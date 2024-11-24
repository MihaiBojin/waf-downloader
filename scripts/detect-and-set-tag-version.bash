#!/bin/bash
set -ueo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
readonly DIR

# shellcheck disable=SC1091
source "$DIR/functions.bash"

VERSION="$(rt git::version_or_sha)"
readonly VERSION
echo "Updating version in '$VERSION_FILE' to: $VERSION" >&2
echo "$VERSION" >"$VERSION_FILE"
