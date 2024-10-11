FROM --platform=$BUILDPLATFORM python:3.13-slim

LABEL org.opencontainers.image.source="https://github.com/MihaiBojin/waf-downloader"
LABEL org.opencontainers.image.description="Cloudflare Web Application Firewall log downloader for a specified zone and time range"
LABEL org.opencontainers.image.licenses=Apache-2.0

ARG PROJECT_NAME
ARG VERSION

ENV PIP_DEFAULT_TIMEOUT=100 \
    # Allow statements and log messages to appear immediately
    PYTHONUNBUFFERED=1 \
    # disable a pip version check to reduce run-time & log-spam
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # cache is useless in docker image, so disable to reduce image size
    PIP_NO_CACHE_DIR=1

RUN set -ex \
    && addgroup --system --gid 999 appuser \
    && adduser --system --uid 999 --gid 999 --no-create-home appuser \
    && mkdir -p /app \
    && chown -R appuser:appuser /app

RUN set -ex \
    && apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends \
    build-essential \
    && apt-get autoremove -y \
    && apt-get clean -y \
    && apt-get autoclean -y \
    && rm -rf /var/cache/apt/archives /var/lib/apt/lists/* \
    ;

WORKDIR /app

COPY dist /app/dist

RUN pip install --no-cache-dir "/app/dist/${PROJECT_NAME}-${VERSION}-py3-none-any.whl[cli]"

USER appuser

ENTRYPOINT ["python", "/usr/local/bin/waf-downloader"]
