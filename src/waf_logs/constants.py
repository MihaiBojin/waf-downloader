"""
Constants for the waf_logs package
==================================
"""

# The Cloudflare API allows for 10,000 log lines to be downloaded at a time
MAX_LOG_LIMIT = 10_000
# The Cloudflare API only allows for 15 days of logs to be downloaded
MAX_DAYS_AGO = 15
# The Cloudflare API allows for maximum 1 day to be downloaded at a time
MAX_LOG_WINDOW_SECONDS = 86400
