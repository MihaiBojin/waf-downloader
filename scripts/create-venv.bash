#!/bin/bash
readonly VENV="venv"

if [ ! -e "pyproject.toml" ]; then
    echo "Current directory does not appear to be a python package..." >&2
    echo
    exit 1
fi

if [ -d "$VENV" ]; then
    echo "Directory already exists: $VENV" >&2
    echo "Will not recreate it." >&2
    echo
    exit 0
fi

# Pick the newest supported interpreter available. A bare `python` can easily be
# older than the 3.11 floor (a global mise or pyenv pin, say), which builds a
# venv that cannot import tomllib.
PYTHON=python
for candidate in python3.14 python3.13 python3.12 python3.11; do
    if command -v "$candidate" >/dev/null 2>&1; then
        PYTHON="$candidate"
        break
    fi
done

# Create virtualenv
$PYTHON -m venv "$VENV"

# shellcheck disable=SC1091
source "$VENV"/bin/activate

pip install --upgrade pip
pip install -e .[cli,dev]
