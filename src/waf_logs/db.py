from datetime import datetime
import json
import sys
import threading
import time
from typing import Any, Callable, List, Optional

import psycopg
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

    @staticmethod
    def _rollback(conn: Any) -> None:
        """Rolls back, ignoring a connection the server has already closed."""
        if conn.closed:
            return
        try:
            conn.rollback()
        except psycopg.OperationalError:
            pass

    def pooled_exec(self, func: Callable[[Any], Any], max_attempts: int = 3):
        """Runs func on a pooled connection.

        Connection failures are retried on a fresh connection, so func
        must be safe to run more than once. Other errors are raised as-is.
        """
        p: ConnectionPool = self.pool()
        for attempt in range(1, max_attempts + 1):
            conn = p.getconn()
            try:
                return func(conn)

            except psycopg.OperationalError as e:
                self._rollback(conn)
                if attempt == max_attempts:
                    raise
                print(
                    f"Database connection error: {e}; retrying (attempt {attempt}/{max_attempts})",
                    file=sys.stderr,
                )
                time.sleep(attempt)

            except Exception:
                self._rollback(conn)
                raise

            finally:
                # The pool discards connections that are no longer usable
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

                cur.execute(update_query, (name, zone_id, event_time))
                conn.commit()
                print(f"Event '{name}/{zone_id}' set to {event_time}", file=sys.stderr)

            finally:
                # Close the cursor
                cur.close()

        return exec

    @staticmethod
    def get_event(name: str, zone_id: str) -> Callable[[Any], Optional[datetime]]:
        def get_row(conn: Any) -> Optional[datetime]:
            # Create a cursor object
            cur = conn.cursor()
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

            finally:
                cur.close()

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

            rowcount = -1
            cur = conn.cursor()
            try:
                insert_query = f"""
                INSERT INTO {table_name} (rayname, zone_id, datetime, data)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (zone_id, rayname, datetime) DO NOTHING
                ;
                """

                for attempt in range(max_retries):
                    cur.executemany(query=insert_query, params_seq=rows, returning=True)
                    conn.commit()
                    rowcount = cur.rowcount

                    if rowcount != -1:
                        break
                    print(
                        f"Cursor returned -1, retrying (attempt {attempt + 1}/{max_retries})",
                        file=sys.stderr,
                    )
                else:
                    print("Max retries reached, rowcount unknown", file=sys.stderr)

            finally:
                # Close the cursor
                cur.close()

            sz = sum([len(r[2]) for r in rows])
            return (time.time() - t0, rowcount, len(rows), sz)

        return insert_rows

    def ensure_schema(self) -> None:
        """Ensure that all the required schemas have been applied."""
        schemas = list_files("resources/db", package_name=__package__)

        for schema in schemas:
            print(f"Applying schema file: {schema}", file=sys.stderr)
            sql = read_file(f"resources/db/{schema}", package_name=__package__)
            self.pooled_exec(Database.execute(sql))
