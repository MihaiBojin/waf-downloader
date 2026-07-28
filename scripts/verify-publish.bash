#!/bin/bash
set -ueo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
readonly DIR

VERSION="$(cat "$DIR"/../VERSION)"
readonly VERSION

# Load project name from project manifest
PROJECT_NAME="$(uv run --no-project python -c "import tomllib; print(tomllib.load(open('$DIR/../pyproject.toml','rb'))['project']['name'])")"
readonly PROJECT_NAME

# Retries a command up to 3 times.
#
# The point of retrying here is to outwait index propagation: the upload has
# just happened and the package is not listed yet. uv caches the index response
# it gets, negative answers included, so a bare retry re-reads the cached "no
# such version" in about 2ms and the whole ladder expires without ever asking
# PyPI again. Callers must pass --refresh-package so each attempt is a real
# request; pip re-fetched on its own, which is why this only began to matter
# once the toolchain moved to uv.
retry() {
    MAX_ATTEMPTS=4
    count=0
    base=5
    local command="$*"
    while [ "$count" -lt "$MAX_ATTEMPTS" ]; do
        count=$((count + 1))
        # shellcheck disable=SC2086
        eval $command && break

        if [ "$count" -eq "$MAX_ATTEMPTS" ]; then
            echo
            echo "Failed after $MAX_ATTEMPTS attempts" >&2
            exit 1
        fi

        echo
        echo "Retrying ($count/$((MAX_ATTEMPTS - 1)))..."
        delay=$((base * count))
        echo "Sleeping for $delay seconds before retrying..."
        sleep "$delay"
    done
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
        retry uv pip install --refresh-package "$PROJECT_NAME" --index-url https://test.pypi.org/simple/ "${PROJECT_NAME}==$VERSION"
        ;;
    --prod)
        echo "Attempting install: ${PROJECT_NAME}==$VERSION"
        retry uv pip install --refresh-package "$PROJECT_NAME" "${PROJECT_NAME}[cli]==$VERSION"
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
