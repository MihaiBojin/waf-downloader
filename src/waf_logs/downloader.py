"""
Cloudflare WAF logs downloader library
======================================

"""

from abc import ABC
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import json
import sys
import time
from typing import Any, List, NamedTuple, Optional

from more_itertools import chunked
from waf_logs import get_waf_logs
from waf_logs import WAF, LogResult
from waf_logs.db import Database
from waf_logs.helpers import (
    compute_time,
    iso_to_datetime,
    validate_name,
)
from queue import Queue


class TimeWindow(NamedTuple):
    """The time window between which logs should be downloaded"""

    start: datetime
    end: datetime


class Output(ABC):
    """Base class for all output classes."""

    def save(self, result: LogResult):
        """Saves the result."""
        pass


class DebugOutput(Output):
    """Class that outputs results to stdout."""

    def save(self, result: LogResult):
        """Saves the result to a Database."""

        for log in result.logs:
            # Print logs to stdout
            print(json.dumps(log.data), file=sys.stdout)


class DatabaseOutput(Output):
    """Class that stores results to a database."""

    def __init__(self, db: Database, table_name: str, chunk_size: int):
        validate_name(table_name)

        self.db: Database = db
        self.table_name: str = table_name
        self.chunk_size = chunk_size

    def save(self, result: LogResult):
        """Stores the results to a DB using a ThreadPoolExecutor."""

        def _exec(chunk: List[WAF]) -> Any:
            """Pools the chunk insert."""

            results = self.db.pooled_exec(
                Database.insert_bulk(data=chunk, table_name=self.table_name)
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


def fetch_logs(
    zone_id: str,
    token: str,
    query: str,
    start_time: datetime,
    end_time: datetime,
) -> List[WAF]:
    """Fetch WAF logs from the Cloudflare API, up to the most recent timestamp."""

    # Add the initial interval
    q: Queue[TimeWindow] = Queue()
    q.put(TimeWindow(start_time, end_time))

    logs: List[WAF] = list()
    while not q.empty():
        window = q.get()
        result = get_waf_logs(
            zone_tag=zone_id,
            cloudflare_token=token,
            query=query,
            start_time=window.start,
            end_time=window.end,
        )

        print(
            f"Downloaded {len(result.logs)} logs up until {result.last_event}, overflown={result.overflown}",
            file=sys.stderr,
        )
        logs += result.logs

        # Determine the next window
        next_window = compute_next_window(result, window.start)
        if next_window is None:
            continue

        # process the remainder of the interval
        q.put(next_window)

    return logs


def download_loop(
    zone_id: str,
    token: str,
    queries: List[str],
    start_time: datetime,
    sink: Output,
) -> datetime:
    """Loops and downloads all the logs in the configured interval."""

    # Default to a past NN%5 minute to increase the chance of missing events due to lag
    end_time = compute_time(at=None)

    logs: List[List[WAF]] = list()
    for query in queries:
        logs.append(fetch_logs(zone_id, token, query, start_time, end_time))

    rows = merge_logs(logs)

    # Repackage as a LogResult to pass metadata to the sink
    result = LogResult(
        logs=rows,
        overflown=False,
        last_event=iso_to_datetime(rows[-1].datetime),  # last event's time
        intended_end_time=end_time,  # originally intended end time
    )

    # Store results
    sink.save(result)

    return end_time


def compute_next_window(
    result: LogResult, current_start_time: Optional[datetime]
) -> Optional[TimeWindow]:
    """Compute the next time window."""

    if result.overflown:
        # Since we overflowed, process the rest of the interval
        start_time = result.last_event
        end_time = result.intended_end_time

        # prevent the loop getting stuck by too many events generated
        # exactly on the start of the datetime window
        if current_start_time == start_time:
            print(
                f"Download seems stuck at ({start_time}; offsetting by +1 minute and skipping some logs",
                file=sys.stderr,
            )
            # in which case advance by a minute
            start_time = compute_time(start_time, +1)

    else:
        # Compute the most recent window
        start_time = result.intended_end_time
        end_time = compute_time(at=None)

        # If we have caught up, exit the loop
        if start_time == end_time:
            return None

    return TimeWindow(start_time, end_time)


def merge_logs(logs: List[List[WAF]]) -> List[WAF]:
    """Create a merged set of WAF logs from multiple queries.
    For now, this implementation will do, however, it can be
    replaced with an n-way merged sort, modified to handle object
    join case.
    """

    # for each unique pair of rayName and datetime, merge the data
    merged = dict()
    for log in logs:
        for w in log:
            key = (w.rayName, w.datetime)
            if key not in merged:
                merged[key] = w
            else:
                merged[key].data.update(w.data)

    # extract the merged data
    return list(merged.values())
