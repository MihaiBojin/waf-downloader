#!/bin/bash

# Function to check if the working directory is dirty
is_dirty() {
    if [ -n "$(git status --porcelain)" ]; then
        echo "-dirty"
    else
        echo ""
    fi
}

# Function to get the current Git short SHA
get_git_sha() {
    # Get the current Git short SHA
    GIT_SHA=$(git rev-parse --short HEAD)

    echo "${GIT_SHA}$(is_dirty)"
}

# Function to get any tags matching the current HEAD
get_tag_at_head() {
    # Get the tag and remove the 'v' prefix
    TAG="$(git tag --contains HEAD)"
    echo "${TAG#v}"
}

# Function to get either a git tag at HEAD (i.e., v.0.1.0) or the SHA (i.e., abc123)
get_tag_or_sha() {
    # Get the tag and remove the 'v' prefix
    TAG="$(git tag --contains HEAD)"
    TAG="${TAG#v}"
    if [ -z "$TAG" ]; then
        TAG="$(get_git_sha)"
    fi

    echo "$TAG"
}

# Extracts the project name as configured in 'pyproject.toml'
get_project_name() {
    dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
    python -c "import toml; print(toml.load('$dir/../pyproject.toml')['project']['name'])"
}
