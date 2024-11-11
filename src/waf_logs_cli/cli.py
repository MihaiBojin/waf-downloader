"""
Cloudflare WAF logs downloader
==============================

"""

import argparse
from datetime import datetime, timedelta, timezone
import multiprocessing
import os
import time
from typing import List, Optional
from dotenv import load_dotenv

from waf_logs.downloader import download_loop
from waf_logs.helpers import compute_time


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
        nargs="+",
        help="One or more Cloudflare zone_ids for which to download the logs",
    )
    parser.add_argument(
        "--start_time",
        type=lambda s: datetime.fromisoformat(s),
        required=False,
        help="The starting point of the datetime in ISO 8601 format (e.g., 2023-12-25T10:30:00Z)."
        "This will be overwritten by --start_minutes_ago.",
    )
    parser.add_argument(
        "--start_minutes_ago",
        type=int,
        required=False,
        help="A relative duration, specified in minutes, from which to start downloading logs."
        "For example, if --start_minutes_ago=5, the script will download events more recent than 5 minutes ago."
        "This will override --start_time.",
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

    args = parser.parse_args()
    zones: List[str] = args.zone_id

    # Determine the earliest time to download logs for
    start_time = args.start_time
    # If start_minutes_ago was specified, use it
    if args.start_minutes_ago is not None:
        if args.start_minutes_ago < 0:
            parser.error("--start_minutes_ago must be a positive number.")
        start_time = compute_time(at=None, delta_by_minutes=-args.start_minutes_ago)

    # Auto-detect available cores, if concurrency not explicitly set
    concurrency = (
        args.concurrency if args.concurrency > 0 else multiprocessing.cpu_count()
    )
    chunk_size = args.chunk_size
    ensure_schema = args.ensure_schema
    do_follow = args.follow

    # Get Cloudflare settings
    token = os.getenv("CLOUDFLARE_API_TOKEN")
    if token is None:
        raise ValueError(
            "A valid Cloudflare token must be specified via CLOUDFLARE_API_TOKEN"
        )

    # Initialize the sink
    connection_string: Optional[str] = os.getenv("DB_CONN_STR")

    can_run = True
    while can_run:
        # If the --follow flag was not specified, this loop only run once
        can_run = do_follow

        last_time: Optional[datetime] = None
        for zone_id in zones:
            et = download_loop(
                zone_id=zone_id,
                connection_string=connection_string,
                concurrency=concurrency,
                chunk_size=chunk_size,
                ensure_schema=ensure_schema,
                cloudflare_token=token,
                cloudflare_queries=["get_firewall_events", "get_firewall_events_ext"],
                start_time=start_time,
            )
            # Store the earliest observed time
            last_time = et if last_time is None else min(last_time, et)

        # If the end time is close to the current time, sleep for a minute to avoid
        # downloading the same logs repeatedly
        if can_run and (
            last_time is None
            or datetime.now(tz=timezone.utc) - last_time < timedelta(minutes=1)
        ):
            time.sleep(60)


if __name__ == "__main__":
    main()
