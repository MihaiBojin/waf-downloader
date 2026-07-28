# The runtime stage is a copy of the builder's .venv, which pins both stages to
# the same base image and the same architecture. No '--platform=$BUILDPLATFORM':
# the environment holds compiled wheels (psycopg-binary), so each entry in a
# multi-platform manifest has to be built for its own platform.
FROM python:3.14-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.11.32 /uv /uvx /bin/

# Compile bytecode for faster cold starts; copy (not link) so the cache mount
# may live on another filesystem; never download an interpreter, the base
# image already provides the right one.
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0 \
    # Allow statements and log messages to appear immediately
    PYTHONUNBUFFERED=1

# Build toolchain for any dependency shipping only an sdist. Confined to the
# builder stage, so it never reaches the runtime image.
RUN set -ex \
    && apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/* \
    ;

WORKDIR /app

# Resolve dependencies first, without the project itself, so editing source
# does not invalidate this layer.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=README.md,target=README.md \
    --mount=type=bind,source=VERSION,target=VERSION \
    uv sync --frozen --no-dev --no-editable --extra cli --no-install-project

COPY . /app

# '--no-editable' matters: the runtime stage copies only .venv, so an editable
# install would point at source that is not there.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable --extra cli

FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1

RUN set -ex \
    && addgroup --system --gid 30000 appuser \
    && adduser --system --uid 30000 --no-create-home appuser \
    && mkdir -p /app \
    && chown -R appuser:appuser /app

WORKDIR /app

COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

USER appuser

ENTRYPOINT ["/app/.venv/bin/waf-downloader"]
