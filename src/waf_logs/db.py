from datetime import datetime
import json
import sys
import threading
import time
from typing import Any, Callable, List, Optional

from psycopg_pool import ConnectionPool

from waf_logs import WAF
from waf_logs.helpers import list_files, read_file, validate_name

# Define a constant for the maximum number of retries
EVENT_DOWNLOAD_TIME = "last_download_time"


class Database:
    def __init__(self, connection_string: str, max_pool_size: int = 10):
        """Initializes a connection"""

        self.connection_string = connection_string
        self.max_pool_size = max_pool_size

        # Init connection pool
        self.lock = threading.Lock()
        self.connection_pool = None
        self.pool()

    def __del__(self):
        # Close all connections in the pool
        if self.connection_pool and not self.connection_pool.closed:
            self.connection_pool.close()
        print("Connection pool destroyed", file=sys.stderr)

    def pool(self) -> ConnectionPool:
        if not self.connection_pool or self.connection_pool.closed:
            with self.lock:
                self.connection_pool = ConnectionPool(
                    conninfo=self.connection_string,
                    min_size=1,  # Minimum number of connections in the pool
                    max_size=self.max_pool_size,  # Maximum number of connections in the pool
                    max_idle=300,  # Maximum idle time for a connection
                    max_lifetime=300,  # Maximum lifetime for a connection
                )

                # Check if the pool was created successfully
                if self.connection_pool:
                    print("Connection pool created successfully", file=sys.stderr)

        return self.connection_pool

    def max_connections(self) -> int:
        """Returns the maximum number of configured connections"""
        return self.max_pool_size

    def pooled_exec(self, func: Callable[[Any], Any]):
        # Get a connection from the pool
        conn = None
        try:
            p: ConnectionPool = self.pool()
            conn = p.getconn()

            return func(conn)

        except Exception as e:
            if conn:
                conn.rollback()
            raise e

        finally:
            # Return the connection to the pool
            if conn:
                p.putconn(conn)

    @staticmethod
    def test(conn: Any) -> Any:
        # Create a cursor object
        cur = conn.cursor()
        try:
            # Execute SQL commands to retrieve the current time and version from PostgreSQL
            cur.execute("SELECT NOW();")
            time = cur.fetchone()[0]

            cur.execute("SELECT version();")
            version = cur.fetchone()[0]

            # Print the results
            print(f"Current time: {time}", file=sys.stderr)
            print(f"PostgreSQL version: {version}", file=sys.stderr)

        finally:
            # Close the cursor
            cur.close()

    @staticmethod
    def execute(sql: str) -> Any:
        def _execute(conn: Any) -> Any:
            # Create a cursor object
            cur = conn.cursor()
            try:
                cur.execute(sql)
                conn.commit()
                print("Executed.", file=sys.stderr)

            finally:
                # Close the cursor
                cur.close()

        return _execute

    @staticmethod
    def set_event(
        name: str, zone_id: str, event_time: datetime
    ) -> Callable[[Any], None]:
        def exec(conn: Any) -> None:
            # Create a cursor object
            cur = conn.cursor()

            try:
                # Insert JSON data into the table
                update_query = """
                INSERT INTO events (name, zone_id, datetime)
                VALUES (%s, %s, %s)
                ON CONFLICT (zone_id, name)
                DO UPDATE SET datetime = EXCLUDED.datetime
                """

                try:
                    cur.execute(update_query, (name, zone_id, event_time))
                    conn.commit()
                    print(
                        f"Event '{name}/{zone_id}' set to {event_time}", file=sys.stderr
                    )

                except Exception as e:
                    print(
                        f"Failed to set event '{name}/{zone_id}' to {event_time}: {e}",
                        file=sys.stderr,
                    )
                    conn.rollback()  # Roll back the transaction before retrying

            finally:
                # Close the cursor
                cur.close()

        return exec

    @staticmethod
    def get_event(name: str, zone_id: str) -> Callable[[Any], Optional[datetime]]:
        def get_row(conn: Any) -> Optional[datetime]:
            # Create a cursor object
            cur = conn.cursor()
            res: Optional[str] = None
            try:
                # Insert JSON data into the table
                select_query = """
                SELECT datetime FROM events WHERE name = %s AND zone_id = %s LIMIT 1;
                """

                cur.execute(
                    select_query,
                    (
                        name,
                        zone_id,
                    ),
                )
                res = cur.fetchone()
                conn.commit()

            except Exception as e:
                print(f"Failed to get event '{name}/{zone_id}': {e}", file=sys.stderr)

            finally:
                # Close the cursor
                if cur:
                    cur.close()

                # Parse the datetime
                if not res:
                    return None

                return datetime.fromisoformat(str(res[0]))

        return get_row

    @staticmethod
    def insert_bulk(
        data: List[WAF], zone_id: str, table_name: str, max_retries: int = 3
    ) -> Callable[[Any], Any]:
        """Inserts a chunk of records in bulk, into the specified table."""

        validate_name(table_name)

        def _to_row(data: WAF) -> tuple:
            """Returns a row tuple to be inserted into a table."""

            return (
                data.rayname,
                zone_id,
                data.datetime,
                json.dumps(data.data),
            )

        # Convert data to insertion format
        rows = [_to_row(d) for d in data]

        def insert_rows(conn: Any) -> Any:
            """Bulk inserts the specified 'rows' with a retry mechanism"""
            t0 = time.time()

            # Create a cursor object
            cur = conn.cursor()
            try:
                # Insert JSON data into the table
                insert_query = f"""
                INSERT INTO {table_name} (rayname, zone_id, datetime, data)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (zone_id, rayname, datetime) DO NOTHING
                ;
                """

                for attempt in range(max_retries):
                    try:
                        cur.executemany(
                            query=insert_query, params_seq=rows, returning=True
                        )
                        conn.commit()

                        if cur.rowcount != -1:
                            break
                        print(
                            f"Cursor returned -1, retrying (attempt {attempt + 1}/{max_retries})",
                            file=sys.stderr,
                        )
                    except Exception as e:
                        print(
                            f"Exception: {e}, retrying (attempt {attempt + 1}/{max_retries})",
                            file=sys.stderr,
                        )
                        conn.rollback()  # Roll back the transaction before retrying
                        time.sleep(1)
                else:
                    print("Max retries reached, insert chunk failed", file=sys.stderr)

            finally:
                # Close the cursor
                cur.close()

                # Compute duration
                t1 = time.time() - t0
                sz = sum([len(r[2]) for r in rows])
                return (t1, cur.rowcount, len(rows), sz)

        return insert_rows

    def ensure_schema(self) -> None:
        """Ensure that all the required schemas have been applied."""
        schemas = list_files("resources/db", package_name=__package__)

        for schema in schemas:
            print(f"Applying schema file: {schema}", file=sys.stderr)
            sql = read_file(f"resources/db/{schema}", package_name=__package__)
            self.pooled_exec(Database.execute(sql))
