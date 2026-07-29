#!/bin/bash
set -ueo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
readonly DIR

# shellcheck disable=SC1091
source "$DIR/functions.bash"

# Helm chart versions are SemVer without a leading 'v'. The published chart
# tags and index entries all use the bare form (waf-downloader-0.2.5), so strip
# the prefix that a tag carries.
#
# Takes the version as an optional argument, falling back to the newest tag on
# the remote. Republishing the chart for an older release has to stamp that
# release's version, not whatever happens to be newest now.
VERSION="${1:-$(releasetools git::latest_version)}"
VERSION="${VERSION#v}"
readonly VERSION

cat "$DIR"/../charts/waf-downloader/Chart.yaml.tmpl >"$DIR"/../charts/waf-downloader/Chart.yaml
sed -i.bak "s/version: \"{{ VERSION }}\"/version: $VERSION/" "$DIR"/../charts/waf-downloader/Chart.yaml
sed -i.bak "s/appVersion: \"{{ VERSION }}\"/appVersion: $VERSION/" "$DIR"/../charts/waf-downloader/Chart.yaml
rm -f "$DIR"/../charts/waf-downloader/Chart.yaml.bak

echo "Updated Helm chart version to $VERSION" >&2
