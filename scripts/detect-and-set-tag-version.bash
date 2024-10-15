#!/bin/bash
set -ueo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
readonly DIR

# shellcheck disable=SC1091
source "$DIR/functions.bash"

VERSION_FILE="$DIR/../VERSION"
readonly VERSION_FILE

#TAG="$(get_git_sha)"
VERSION="$(cat "$VERSION_FILE")"
if [ -z "$(is_dirty)" ]; then
    # Working dir is clean, attempt to use tag
    GITTAG="$(get_tag_at_head)"

    # If git tag found, use it
    if [ -n "$GITTAG" ]; then
        #TAG="$GITTAG"
        VERSION="$GITTAG"
    fi
fi
#readonly TAG
readonly VERSION

# Output the detected tag
echo "Updating version in '$VERSION_FILE' to: $VERSION"
echo "$VERSION" >"$VERSION_FILE"
