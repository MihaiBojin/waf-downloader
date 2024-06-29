#!/bin/bash
set -euo pipefail

# Ensure the up-to-date requirements are installed
# shellcheck disable=SC1090
eval "$(task venv)"
task setup
