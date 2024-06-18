"""
Cloudflare WAF logs
===================

Download WAF logs.

Functions:
    - get_waf_logs: Download logs from Cloudflare
"""

import sys
from typing import Dict, List, Optional
import requests
from waf_logs.get_secret import get_secret
from typing import NamedTuple
from waf_logs.helpers import iso_to_datetime, read_file, validate_name
from datetime import datetime

# Define the endpoint URL
URL = "https://api.cloudflare.com/client/v4/graphql"
MAX_LOG_LIMIT = 10_000  # defined by the Cloudflare API


class WAF(NamedTuple):
    rayName: str
    datetime: str
    data: Dict[str, str]


class LogResult(NamedTuple):
    logs: List[WAF]
    overflown: bool
    last_event: datetime
    intended_end_time: datetime


def get_waf_logs(
    zone_tag: str,
    cloudflare_token: Optional[str],
    query: str,  # must map to resources/QUERY.graphql
    start_time: datetime,
    end_time: datetime,
) -> LogResult:
    """Download WAF logs from the Cloudflare analytics API"""

    # Prevent path traversal
    validate_name(query)
    graphql = read_file(f"resources/{query}.graphql", package_name=__package__)

    if start_time > end_time:
        raise ValueError(
            f" Start time ({start_time}) must be a valid time prior to ({end_time})"
        )

    filter = {
        "datetime_geq": start_time.isoformat(),
        "datetime_leq": end_time.isoformat(),
    }
    variables = {
        "zoneTag": zone_tag,
        "filter": filter,
        "limit": MAX_LOG_LIMIT,
    }

    # Load the Cloudflare token
    if not cloudflare_token:
        cloudflare_token = get_secret("CLOUDFLARE_API_TOKEN")

    # Define the headers
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {cloudflare_token}",
    }

    # Make the request
    print(
        f"Downloading logs between {start_time} and {end_time} (query: {query})",
        file=sys.stderr,
    )
    response = requests.post(
        URL, json={"query": graphql, "variables": variables}, headers=headers
    )

    # Check the response status and content
    if response.status_code != 200:
        raise RuntimeError(f"Error: {response.status_code}\n{response.text}")

    # Retrieve data from API call
    data = response.json()
    if data["errors"] is not None:
        raise RuntimeError(f"Errors were found: {data}")

    # Retrieve firewall events
    # ~6700 / 5 minutes
    zones = data["data"]["viewer"]["zones"]
    result = [_event_row(event) for z in zones for event in z["firewallEventsAdaptive"]]

    return LogResult(
        logs=result,
        # TODO(#3): Handle `last_event==intended_end_time && overflown`
        overflown=len(result) == MAX_LOG_LIMIT,
        last_event=iso_to_datetime(result[-1].datetime),
        intended_end_time=end_time,
    )


def _event_row(event: Dict[str, str]) -> WAF:
    """Extracts interesting fields out of events."""

    return WAF(
        rayName=event["rayName"],
        datetime=event["datetime"],
        data=event,
    )
