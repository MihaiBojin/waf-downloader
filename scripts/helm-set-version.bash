#!/bin/bash
set -ueo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
readonly DIR

# shellcheck disable=SC1091
source "$DIR/functions.bash"

VERSION="$(latest_version)"
readonly VERSION

cat charts/waf-downloader/Chart.yaml.tmpl >charts/waf-downloader/Chart.yaml
sed -i '' "s/version: \"{{ VERSION }}\"/version: $VERSION/" charts/waf-downloader/Chart.yaml
sed -i '' "s/appVersion: \"{{ VERSION }}\"/appVersion: $VERSION/" charts/waf-downloader/Chart.yaml
