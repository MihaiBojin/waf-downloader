#!/bin/bash
set -euo pipefail

# Ensure the up-to-date requirements are installed
# shellcheck disable=SC1091
source "$HOME/.local/bin/env"
task setup
