#!/bin/bash
set -ueo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
readonly DIR

# shellcheck disable=SC1091
source "$DIR/functions.bash"

VERSION_FILE="$DIR/../VERSION"
readonly VERSION_FILE

VERSION="$(cat "$VERSION_FILE")"
if [ -z "$(is_dirty)" ]; then
    # Working dir is clean, attempt to use tag
    GITTAG="$(get_tag_at_head)"

    # If git tag found, use it
    if [ -n "$GITTAG" ]; then
        VERSION="$GITTAG"
    fi
fi
readonly VERSION

sed -i '' "s/version: \"{{ VERSION }}\"/version: $VERSION/" charts/waf-downloader/Chart.yaml
sed -i '' "s/appVersion: \"{{ VERSION }}\"/appVersion: $VERSION/" charts/waf-downloader/Chart.yaml
