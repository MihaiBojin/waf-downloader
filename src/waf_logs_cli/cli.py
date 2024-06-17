"""
A demo CLI
==========

"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import os
import time
from typing import Any, Iterable, List, NamedTuple, Optional
from waf_logs import Database, get_waf_logs
from dotenv import load_dotenv
from itertools import islice

from waf_logs.cloudflare_waf import WAF, LogResult
from waf_logs.helpers import compute_time, validate_name
from queue import Queue


class TimeWindow(NamedTuple):
    start: Optional[datetime]
    end: Optional[datetime]


def download_loop(
    zone_id: str,
    token: str,
    time_window_in_minutes: int,
    db: Database,
    chunk_size: int,
    query: str = "get_firewall_events",
    table_name: str = "cf_waf_logs_adaptive",
):
    """Loops and downloads all the logs in the configured interval."""

    # Add the initial interval
    q: Queue[TimeWindow] = Queue()
    q.put(TimeWindow(None, None))

    while not q.empty():
        window = q.get()
        result = get_waf_logs(
            zone_tag=zone_id,
            cloudflare_token=token,
            start_time=window.start or None,
            end_time=window.end,
            query=query,
            limit=10000,
            default_time_window_in_minutes=time_window_in_minutes,
        )
        print(
            f"Downloaded {len(result.logs)} logs up until {result.last_event}, overflown={result.overflow}"
        )

        # Store results
        store(db=db, result=result, table_name=table_name, chunk_size=chunk_size)

        # Compute next time window
        if result.overflow:
            # Since we overflowed, process the rest of the interval
            start_time = result.last_event
            end_time = result.intended_end_time

            # edge case: if too many logs, the loop might get stuck
            if window.start == start_time:
                print(
                    f"Download seems stuck at ({start_time}; offsetting by +1 minute and skipping some logs"
                )
                start_time = compute_time(start_time, 1)

        else:
            # Compute the most recent window
            start_time = result.intended_end_time
            end_time = compute_time(at=None)

            # If we have caught up, exit the loop
            if start_time == end_time:
                continue

        # process the remainder of the interval
        q.put(TimeWindow(start_time, end_time))


def _chunked_list(iterable: Iterable[WAF], chunk_size: int):
    """Splits an iterable into chunks of specified size."""

    iterable = iter(iterable)
    return iter(lambda: list(islice(iterable, chunk_size)), [])


def store(
    db: Database,
    result: LogResult,
    table_name: str = "cf_waf_logs_adaptive",  # must be a valid name
    chunk_size: int = 100,
):
    """Stores the results using a ThreadPoolExecutor."""

    validate_name(table_name)

    def _exec(chunk: List[WAF]) -> Any:
        """Pools the chunk insert."""

        results = db.pooled_exec(
            Database.insert_bulk(data=chunk, table_name=table_name)
        )

        # Print stats and approximate duration
        duration, rows_inserted, all_rows, total_bytes = results
        row_per_sec = rows_inserted / duration
        print(
            f"Inserted {rows_inserted}/{all_rows} new records into {table_name} ({total_bytes:,} bytes) in {duration:.2f} seconds [{row_per_sec:.0f} rows/s]"
        )
        return results

    # Split the dataset into chunks
    chunks = _chunked_list(result.logs, chunk_size=chunk_size)
    total_chunks = len(result.logs) // chunk_size + (
        1 if len(result.logs) % chunk_size != 0 else 0
    )
    print(f"Inserting {len(result.logs)} records in {total_chunks} chunks...")

    # Use a ThreadPoolExecutor to insert data concurrently
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=db.max_connections()) as executor:
        results = list(executor.map(_exec, chunks))
        total_bytes = sum([r[3] for r in results])

    # Compute stats
    t1 = time.time() - t0
    rows_per_sec = len(result.logs) / t1
    bytes_per_sec = total_bytes / t1
    print(
        f"Completed after {t1:.2f} seconds ({rows_per_sec:,.0f} rows/sec; {bytes_per_sec:,.0f} bytes/sec)."
    )


def main() -> None:
    # Load environment variables from .env file
    load_dotenv()

    # Get Cloudflare settings
    token = os.getenv("CLOUDFLARE_TOKEN", "none")
    zone_id = os.getenv("CLOUDFLARE_ZONE_ID", "none")

    chunk_size = int(os.getenv("CHUNK_SIZE", 1000))

    # Get connection string
    connection_string = os.getenv("DB_CONN_STR")
    if connection_string is None:
        raise ValueError("Connection string must be specified via DB_CONN_STR")

    t0 = time.time()
    db = Database(connection_string)
    db.ensure_schema()

    print("Downloading WAF logs...")
    download_loop(
        zone_id=zone_id,
        token=token,
        db=db,
        time_window_in_minutes=10,
        chunk_size=chunk_size,
        query="get_firewall_events",
        table_name="cf_waf_logs_adaptive",
    )

    print("Downloading WAF extended logs...")
    download_loop(
        zone_id=zone_id,
        token=token,
        db=db,
        time_window_in_minutes=10,
        chunk_size=chunk_size,
        query="get_firewall_events_ext",
        table_name="cf_waf_logs_adaptive_ext",
    )
    t1 = time.time() - t0
    print(f"Exiting after {t1:.2f} seconds")


if __name__ == "__main__":
    main()
