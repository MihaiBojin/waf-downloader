FROM --platform=$BUILDPLATFORM python:3.13-slim

LABEL org.opencontainers.image.source="https://github.com/MihaiBojin/waf-downloader"
LABEL org.opencontainers.image.description="Cloudflare Web Application Firewall log downloader for a specified zone and time range"
LABEL org.opencontainers.image.licenses=Apache-2.0

ARG PROJECT_NAME
ARG VERSION

RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
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

ENTRYPOINT ["python", "/usr/local/bin/waf-downloader"]
