"""
Cloudflare WAF logs
===================

Download WAF logs.

Functions:
    - get_waf_logs: Download logs from Cloudflare
"""

from typing import Dict, List, Optional
import requests
from waf_logs.get_secret import get_secret
from typing import NamedTuple
from waf_logs.helpers import compute_time, iso_to_datetime, read_file, validate_name
from datetime import datetime

# Define the endpoint URL
URL = "https://api.cloudflare.com/client/v4/graphql"


class WAF(NamedTuple):
    rayName: str
    datetime: str
    data: Dict[str, str]


class LogResult(NamedTuple):
    logs: List[WAF]
    overflow: bool
    last_event: datetime
    intended_end_time: datetime


def get_waf_logs(
    zone_tag: str,
    cloudflare_token: Optional[str],
    start_time: Optional[datetime],
    end_time: Optional[datetime],
    query: str = "get_firewall_events",  # must map to resources/QUERY.graphql
    limit: int = 10000,
    default_time_window_in_minutes: int = 5,
) -> LogResult:
    """Download WAF logs from the Cloudflare analytics API"""

    # Prevent path traversal
    validate_name(query)
    query = read_file(f"resources/{query}.graphql", package_name=__package__)

    if end_time is None:
        # Always default to a past NN % 5 minute to avoid missing events
        end_time = compute_time(at=None)

    if start_time is None:
        start_time = compute_time(
            at=end_time, delta_by_minutes=-default_time_window_in_minutes
        )

    if start_time > end_time:
        raise ValueError(
            f" Start time ({start_time}) must be before end time ({end_time})"
        )

    filter = {
        "datetime_geq": start_time.isoformat(),
        "datetime_leq": end_time.isoformat(),
    }
    variables = {
        "zoneTag": zone_tag,
        "filter": filter,
        "limit": limit,
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
    print(f"Attempting to download logs between {start_time} and {end_time}...")
    response = requests.post(
        URL, json={"query": query, "variables": variables}, headers=headers
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
        overflow=len(result) == limit,
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
