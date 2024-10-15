#!/bin/bash
set -ueo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
readonly DIR

VERSION_FILE="$DIR/../VERSION"
readonly VERSION_FILE

# shellcheck disable=SC1091
source "$DIR/functions.bash"

# Retrieve current git sha
VERSION="$(cat "$VERSION_FILE")"
if [ -z "$(is_dirty)" ]; then
    # Working dir is clean, attempt to use tag
    GITTAG="$(get_tag_at_head)"

    # If git tag found, use it
    if [ -n "$GITTAG" ]; then
        VERSION="$GITTAG"
    fi
fi

# Parse command-line arguments
PLATFORM="linux/arm64,linux/amd64"
DOCKER_TAGS=()
while [[ $# -gt 0 ]]; do
    case $1 in
    --push)
        PUSH_FLAG="--push"
        shift 1
        ;;
    --platform)
        PLATFORM="$2"
        shift 2
        ;;
    --tag)
        DOCKER_TAGS+=("$2")
        shift 2
        ;;
    *)
        echo "Unknown argument: $1" >&2
        exit 1
        ;;
    esac
done

# If DOCKER_TAGS is empty, populate with default
if [ ${#DOCKER_TAGS[@]} -eq 0 ]; then
    echo "ERROR: No image tags provided" >&2
    exit 1
fi

echo "Updating version in '$VERSION_FILE' to: $VERSION"
echo "$VERSION" >"$VERSION_FILE"

# Build the image
echo "Building (${DOCKER_TAGS[*]}) for $PLATFORM..."
mkdir -p build
set +e
docker buildx build --sbom=true --attest type=provenance,mode=max "$PUSH_FLAG" \
    --platform "$PLATFORM" \
    $(for tag in "${DOCKER_TAGS[@]}"; do echo -n "-t $tag "; done) \
    --metadata-file build/build-metadata.json \
    .
res=$?
set -e

# Revert the version after the dist/ was built
echo "Reverting version to repository value..."
git checkout -- "$VERSION_FILE"

if [ $res -ne 0 ]; then
    echo
    echo "ERROR: Failed to build image (${DOCKER_TAGS[*]}) for $PLATFORM" >&2
    exit 1
fi

echo
echo "Built image (${DOCKER_TAGS[*]}) for $PLATFORM, flags: $PUSH_FLAG" >&2
