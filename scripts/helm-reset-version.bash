#!/bin/bash
set -ueo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
readonly DIR

# shellcheck disable=SC1091
source "$DIR/functions.bash"

sed -Ei '' "s/version: [0-9]+\.[0-9]+\.[0-9]+/version: \"{{ VERSION }}\"/" charts/waf-downloader/Chart.yaml
sed -Ei '' "s/appVersion: [0-9]+\.[0-9]+\.[0-9]+/appVersion: \"{{ VERSION }}\"/" charts/waf-downloader/Chart.yaml
