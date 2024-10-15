FROM --platform=$BUILDPLATFORM python:3.13-slim AS builder
RUN set -ex \
    && apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends \
    build-essential \
    curl \
    git \
    && apt-get autoremove -y \
    && apt-get clean -y \
    && apt-get autoclean -y \
    && rm -rf /var/cache/apt/archives /var/lib/apt/lists/* \
    ;

WORKDIR /app
RUN sh -c "$(curl --location https://taskfile.dev/install.sh)" -- -d -b /usr/local/bin
COPY . /app
RUN /usr/local/bin/task setup
RUN /app/scripts/detect-and-set-tag-version.bash
RUN /usr/local/bin/task build
