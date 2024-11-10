"""
A Python package template
=========================
"""

from .helpers import compute_time, iso_to_datetime
from .cloudflare_waf import get_waf_logs, WAF, LogResult

# The Cloudflare API allows for 10,000 log lines to be downloaded at a time
MAX_LOG_LIMIT = 10_000
# The Cloudflare API only allows for 15 days of logs to be downloaded
MAX_DAYS_AGO = 15
# The Cloudflare API allows for maximum 1 day to be downloaded at a time
MAX_LOG_WINDOW_SECONDS = 86400

__all__ = [
    # keep-sorted start
    "LogResult",
    "MAX_LOG_LIMIT",
    "WAF",
    "compute_time",
    "get_waf_logs",
    "iso_to_datetime",
    # keep-sorted end
]
