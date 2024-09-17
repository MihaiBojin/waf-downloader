"""
Cloudflare WAF logs downloader
==============================

"""

import argparse
from datetime import datetime, timezone
import multiprocessing
import os
import sys
import time
from waf_logs.db import Database
from dotenv import load_dotenv

from waf_logs.downloader import DatabaseOutput, DebugOutput, Output, download_loop
from waf_logs.helpers import compute_time


def perform_download(
    zone_id: str, token: str, start_time: datetime, sink: Output
) -> datetime:
    t0 = time.time()
    print("Downloading WAF logs...", file=sys.stderr)
    end_time = download_loop(
        zone_id=zone_id,
        token=token,
        queries=["get_firewall_events", "get_firewall_events_ext"],
        start_time=start_time,
        sink=sink,
    )
    t1 = time.time() - t0
    print(f"Completed download after {t1:.2f} seconds", file=sys.stderr)

    return end_time


def main() -> None:
    # Load environment variables from .env file
    load_dotenv()

    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Load downloader configuration arguments"
    )
    parser.add_argument(
        "--zone_id",
        type=str,
        required=True,
        help="Cloudflare zone_id for which to download the logs",
    )
    parser.add_argument(
        "--start_time",
        type=lambda s: datetime.fromisoformat(s),
        required=False,
        help="The starting point of the datetime in ISO 8601 format (e.g., 2023-12-25T10:30:00Z)."
        "This is mutually exclusive with --start_minutes_ago.",
    )
    parser.add_argument(
        "--start_minutes_ago",
        type=int,
        required=False,
        help="A relative duration, specified in minutes, from which to start downloading logs."
        "For example, if --start_minutes_ago=-5, the script will download events more recent than 5 minutes ago."
        "This is mutually exclusive with --start_time.",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=0,
        help="How many threads should concurrently download and insert chunks"
        "The default of 0 will cause the number of available cores to be used.",
    )
    parser.add_argument(
        "--chunk_size",
        type=int,
        default=1000,
        help="The chunk size used for bulk inserts",
    )
    parser.add_argument(
        "--ensure_schema",
        type=bool,
        default=True,
        help="If True, the execution will re-apply all schema files",
    )
    parser.add_argument(
        "--follow",
        action="store_true",
        help="If this flag is specified, the process will not exit and instead keep downloading new logs forever",
    )
    parser.add_argument(
        "--sleep_interval_minutes",
        type=int,
        required=False,
        default=1,
        help="Sleep for that many minutes between each download loop; defaults to 1 minute",
    )

    args = parser.parse_args()
    zone_id = args.zone_id

    if args.start_time is None and args.start_minutes_ago is None:
        parser.print_help()
        parser.error("One of '--start_time' or '--start_minutes_ago' must be provided.")
    start_time = args.start_time
    if args.start_minutes_ago is not None:
        if args.start_minutes_ago > 0:
            parser.error(
                "--start_minutes_ago must be negative as the starting time cannot be in the future."
            )
        start_time = compute_time(at=None, delta_by_minutes=args.start_minutes_ago)

    # Auto-detect available cores, if concurrency not explicitly set
    concurrency = (
        args.concurrency if args.concurrency > 0 else multiprocessing.cpu_count()
    )
    chunk_size = args.chunk_size
    ensure_schema = args.ensure_schema

    do_follow = args.follow
    sleep_interval = args.sleep_interval_minutes * 60

    # Get Cloudflare settings
    token = os.getenv("CLOUDFLARE_TOKEN")
    if token is None:
        raise ValueError(
            "A valid Cloudflare token must be specified via CLOUDFLARE_TOKEN"
        )

    # Initialize the sink
    sink: Output
    connection_string = os.getenv("DB_CONN_STR")
    if connection_string is None:
        sink = DebugOutput()
    else:
        db = Database(connection_string, max_pool_size=concurrency)
        if ensure_schema:
            db.ensure_schema()

        sink = DatabaseOutput(
            db=Database(connection_string, max_pool_size=concurrency),
            table_name="cf_waf_logs_adaptive",
            chunk_size=chunk_size,
        )

    if do_follow:
        print(
            f"Starting to download logs every {sleep_interval/60:.0f} minutes",
            file=sys.stderr,
        )
        while True:
            t0 = datetime.now(tz=timezone.utc)
            start_time = perform_download(zone_id, token, start_time, sink)
            duration = start_time - t0
            print(f"Downloaded up to timestamp: {start_time}", file=sys.stderr)

            # If the duration approaches the sleep interval, skip the sleep to allow the process to catch-up
            if duration.total_seconds() > sleep_interval * 0.8:
                print(
                    f"[WARN] Download completed in {duration.strftime(' %H:%M:%S')}, skipping sleep",
                    file=sys.stderr,
                )
            else:
                print(
                    f"Sleeping for {sleep_interval/60:.2f} minutes",
                    file=sys.stderr,
                )
                time.sleep(sleep_interval)
    else:
        perform_download(zone_id, token, start_time, sink)


if __name__ == "__main__":
    main()
