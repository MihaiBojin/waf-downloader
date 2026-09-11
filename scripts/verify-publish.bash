#!/bin/bash
set -ueo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
readonly DIR

VERSION="$(cat "$DIR"/../VERSION)"
readonly VERSION

# Load project name from project manifest
PROJECT_NAME="$(uv run --no-project python -c "import tomllib; print(tomllib.load(open('$DIR/../pyproject.toml','rb'))['project']['name'])")"
readonly PROJECT_NAME

# Waits for an index to serve the version, then installs it once.
#
# The upload has just happened and the package is not listed yet, so something has to
# wait. This replaced four attempts of linear backoff totalling about 30 seconds, which
# is short enough to fail a release that in fact published correctly.
# 'rt net::await_url' backs off 15s, 30s, 60s, 120s, 240s and returns as soon as the
# version is there.
#
# curl rather than a retried install: uv caches the index response it gets, negative
# answers included, so a bare retry re-reads the cached "no such version" in about 2ms
# and never asks PyPI again. '--refresh-package' on the install below is the other half
# of that.
await_index() {
    releasetools net::await_url "$1/pypi/$PROJECT_NAME/$VERSION/json"
}

if [[ "$#" -eq 0 ]]; then
    echo "You must specify --test or --prod as arguments" >&2
    echo
    exit 1
fi

echo "Creating a virtual env..."
VENV="$(mktemp -d)/venv"
readonly VENV
# '--no-project' keeps the env detached from the working tree, so the check
# really does exercise the published artifact rather than the local source.
uv venv --no-project "$VENV"
# 'uv pip' targets this env instead of the project's .venv
export VIRTUAL_ENV="$VENV"

echo "Copying verification script..."
cp "$DIR"/../src/scripts/verify_install.py "$VENV/verify_install.py"

echo "Attempting to install version ($VERSION) in virtualenv ($VENV)..."
while [[ "$#" -gt 0 ]]; do
    case $1 in
    --test)
        # Dependencies come from the main index because test.pypi does not
        # carry every third-party package.
        DEPS="$(uv run --no-project python -c "
import tomllib
p = tomllib.load(open('$DIR/../pyproject.toml', 'rb'))['project']
print(' '.join(p['dependencies'] + p.get('optional-dependencies', {}).get('cli', [])))
")"
        if [ -n "$DEPS" ]; then
            echo "Installing dependencies from main index, since not all packages are available in test.pypi..."
            # shellcheck disable=SC2086
            uv pip install $DEPS
        fi
        echo "Attempting install: ${PROJECT_NAME}==$VERSION"
        await_index "https://test.pypi.org"
        uv pip install --refresh-package "$PROJECT_NAME" --index-url https://test.pypi.org/simple/ "${PROJECT_NAME}==$VERSION"
        ;;
    --prod)
        echo "Attempting install: ${PROJECT_NAME}==$VERSION"
        await_index "https://pypi.org"
        uv pip install --refresh-package "$PROJECT_NAME" "${PROJECT_NAME}[cli]==$VERSION"
        ;;
    --*= | -*)
        echo "Error: Unsupported flag $1" >&2
        echo
        exit 1
        ;;
    esac
    shift
done

pushd "$VENV" >/dev/null 2>&1
"$VENV/bin/python" verify_install.py
popd >/dev/null 2>&1

echo "Virtualenv location: $VENV"
