"""
Cloudflare WAF logs downloader library
======================================

"""

from abc import ABC
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import json
import sys
import time
from typing import Any, List, NamedTuple, Optional

from more_itertools import chunked
from waf_logs import MAX_DAYS_AGO, MAX_LOG_LIMIT, MAX_LOG_WINDOW_SECONDS, get_waf_logs
from waf_logs import WAF, LogResult
from waf_logs.db import EVENT_DOWNLOAD_TIME, Database
from waf_logs.helpers import (
    compute_time,
    iso_to_datetime,
    validate_name,
)


class TimeWindow(NamedTuple):
    """The time window between which logs should be downloaded"""

    start: datetime
    end: datetime


class Output(ABC):
    """Base class for all output classes."""

    def save(self, zone_id: str, result: LogResult):
        """Saves the result."""
        pass


class DebugOutput(Output):
    """Class that outputs results to stdout."""

    def save(self, zone_id: str, result: LogResult):
        """Saves the result to a Database."""

        for log in result.logs:
            # Print logs to stdout
            # Convert WAF object to dict for JSON serialization
            print(
                json.dumps({"zone_id": log.zone_id, "data": log.data}), file=sys.stdout
            )


class DatabaseOutput(Output):
    """Class that stores results to a database."""

    def __init__(self, db: Database, table_name: str, chunk_size: int):
        validate_name(table_name)

        self.db: Database = db
        self.table_name: str = table_name
        self.chunk_size = chunk_size

    def save(self, zone_id: str, result: LogResult):
        """Stores the results to a DB using a ThreadPoolExecutor."""

        def _exec(chunk: List[WAF]) -> Any:
            """Pools the chunk insert."""

            results = self.db.pooled_exec(
                Database.insert_bulk(
                    data=chunk,
                    zone_id=zone_id,
                    table_name=self.table_name,
                )
            )

            # Print stats and approximate duration
            duration, _, all_rows, total_bytes = results
            row_per_sec = all_rows / duration
            print(
                f"Inserted {all_rows} records into {self.table_name} ({total_bytes:,} bytes) in {duration:.2f} seconds [{row_per_sec:.0f} rows/s]",
                file=sys.stderr,
            )
            return results

        # Split the dataset into chunks
        chunks = chunked(result.logs, n=self.chunk_size)
        total_chunks = len(result.logs) // self.chunk_size + (
            1 if len(result.logs) % self.chunk_size != 0 else 0
        )
        print(
            f"Inserting {len(result.logs)} records in {total_chunks} chunks...",
            file=sys.stderr,
        )

        # Use a ThreadPoolExecutor to insert data concurrently
        t0 = time.time()
        with ThreadPoolExecutor(max_workers=self.db.max_connections()) as executor:
            results = list(executor.map(_exec, chunks))
            total_bytes = sum([r[3] for r in results])

        # Compute stats
        t1 = time.time() - t0
        rows_per_sec = len(result.logs) / t1
        bytes_per_sec = total_bytes / t1
        print(
            f"Completed inserting after {t1:.2f} seconds ({rows_per_sec:,.0f} rows/sec; {bytes_per_sec:,.0f} bytes/sec).",
            file=sys.stderr,
        )


def _store_last_download_time(db: Database, zone_id: str, at: datetime) -> None:
    """Store the last download time in the database"""
    if db is None:
        # Nothing to do if DB is not initialized
        return

    db.pooled_exec(
        db.set_event(
            name=EVENT_DOWNLOAD_TIME,
            zone_id=zone_id,
            event_time=at,
        )
    )


def _box_start_time(start_time: datetime) -> datetime:
    """Ensure that the start time is a valid time for the Cloudflare API"""

    # The Cloudflare API only allows for 15 days of logs to be downloaded
    allowed_start_mins = 1440 * MAX_DAYS_AGO

    # Calculate a valid start time, allowing one minute to avoid errors due to proximity to the limit
    if datetime.now(tz=timezone.utc) - start_time >= timedelta(
        minutes=allowed_start_mins - 1
    ):
        start_time = compute_time(at=None, delta_by_minutes=-allowed_start_mins + 1)
        print(
            f"Start time is too far in the past, setting to {start_time}",
            file=sys.stderr,
        )

    return start_time


def download_loop(
    zone_id: str,
    connection_string: Optional[str],
    concurrency: int,
    chunk_size: int,
    ensure_schema: bool,
    cloudflare_token: str,
    cloudflare_queries: List[str],
    start_time: Optional[datetime],
) -> datetime:
    """Loops and downloads all the logs in the configured interval."""

    # If a connection string is provided, use it to connect to the database
    # and store outputs
    sink: Output = DebugOutput()
    db: Optional[Database] = None
    if connection_string:
        db = Database(connection_string, max_pool_size=concurrency)
        if ensure_schema:
            db.ensure_schema()

        sink = DatabaseOutput(
            db=Database(connection_string, max_pool_size=concurrency),
            table_name="cf_waf_logs_adaptive",
            chunk_size=chunk_size,
        )

    if start_time is None and db:
        # If we don't have a start time, load it from the database
        start_time = db.pooled_exec(
            db.get_event(name=EVENT_DOWNLOAD_TIME, zone_id=zone_id)
        )

    if start_time is not None:
        print(f"Start time loaded from DB: {start_time}", file=sys.stderr)

    else:
        # If a start time was not defined, default to 5 minutes ago
        start_time = compute_time(at=None, delta_by_minutes=-5)
        print(f"Defaulting start time to: {start_time}", file=sys.stderr)

    # Always round down to the previous minute to avoid partial logs
    end_time = compute_time(at=None, delta_by_minutes=-1)

    # Initialize window size to 1 day in seconds
    window_size = MAX_LOG_WINDOW_SECONDS
    current_time: datetime = start_time
    last_observed_time = current_time

    while current_time < end_time:
        # Ensure that the current time is a valid time for the Cloudflare API
        current_time = _box_start_time(current_time)

        # Calculate the window end, not exceeding the overall end_time
        window_end = min(current_time + timedelta(seconds=window_size), end_time)
        print(f"Processing window: {current_time} to {window_end}", file=sys.stderr)

        # Download logs for all queries in this window
        window_logs: List[List[WAF]] = []
        overflown = False
        for query in cloudflare_queries:
            result: LogResult = get_waf_logs(
                zone_tag=zone_id,
                cloudflare_token=cloudflare_token,
                query=query,
                start_time=current_time,
                end_time=window_end,
            )

            if result.overflown:
                overflown = True
                # If the result is overflown, we can't trust it
                window_size //= 2
                print(
                    f"Overflown at {result.last_event} ({len(result.logs)} logs), intended end time {result.intended_end_time}, retrying with window size {window_size}",
                    file=sys.stderr,
                )

                # If overflown, break out of the query loop
                break

            window_logs.append(result.logs)

        if overflown:
            # If overflown, retry with smaller window
            continue

        # Merge logs from different queries
        merged_logs = _merge_logs(window_logs)
        total_rows = len(merged_logs)
        print(f"Retrieved {total_rows} rows", file=sys.stderr)

        # Determine if the window is too small, but do so while de-risking overflown results
        if total_rows < MAX_LOG_LIMIT // 3:
            window_size = min(2 * window_size, MAX_LOG_WINDOW_SECONDS)
            print(
                f"Few rows, increasing next window to {window_size} seconds",
                file=sys.stderr,
            )

        if total_rows > 0:
            # Repackage as a LogResult to pass metadata to the sink
            result = LogResult(
                logs=merged_logs,
                overflown=False,
                last_event=iso_to_datetime(merged_logs[-1].datetime),
                intended_end_time=window_end,
            )
            sink.save(zone_id=zone_id, result=result)
            last_observed_time = result.last_event

        # Move to next window
        current_time = window_end

        # Store the last processed time
        if db is not None:
            _store_last_download_time(db=db, zone_id=zone_id, at=window_end)

    # Return the last processed time
    return last_observed_time


def _merge_logs(logs: List[List[WAF]]) -> List[WAF]:
    """Create a merged set of WAF logs from multiple queries.
    For now, this implementation will do, however, it can be
    replaced with an n-way merged sort, modified to handle object
    join case.
    """

    # for each unique pair of rayname and datetime, merge the data
    merged = dict()
    for log in logs:
        for w in log:
            key = (w.rayname, w.datetime)
            if key not in merged:
                merged[key] = w
            else:
                merged[key].data.update(w.data)

    # extract the merged data
    return list(merged.values())
