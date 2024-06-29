# Cloudflare Web Application Firewall downloader

![Build Status](https://github.com/MihaiBojin/waf-downloader/actions/workflows/python-tests.yml/badge.svg)
[![PyPI version](https://badge.fury.io/py/waf-downloader.svg)](https://badge.fury.io/py/waf-downloader)
[![Python Versions](https://img.shields.io/pypi/pyversions/waf-downloader.svg)](https://pypi.org/project/waf-downloader/)
[![License](https://img.shields.io/github/license/MihaiBojin/waf-downloader.svg)](LICENSE)

A library, CLI, and docker image that downloads Cloudflare WAF logs for a specified zone_id and time frame.

## Schema

See [src/waf_logs/resources/db/](./src/waf_logs/resources/db) for a list of schemas that are auto-applied at start. This can be disabled by passing `--ensure_schema False`.

## Quickstart

The project is published at <https://pypi.org/project/waf-downloader/>.

Install it via:

```shell
pip install waf-downloader

# or alternatively, directly from git
pip install "git+https://github.com/MihaiBojin/waf-downloader@main"
```

Or with Docker:

```shell
docker pull ghcr.io/mihaibojin/waf-downloader:latest
```

The list of published images can be found at:
<https://github.com/MihaiBojin/waf-downloader/pkgs/container/waf-downloader>

### Build and run with Docker

Define secrets in an `.env` file (do not quote values):

```properties
CLOUDFLARE_TOKEN=...
DB_CONN_STR=...
```

The Cloudflare token is required, but the connection string is optional.
If skipped, it will result in logs being printed to stdout.

IMPORTANT: This project uses [taskfile.dev](https://taskfile.dev/installation/),
which you will need to install for running the following commands:

```shell
# Build
task docker-build

# Load all logs in zone, starting 5 minutes prior
task docker-run ARGS="--zone_id [CLOUDFLARE_ZONE_ID] --start_minutes_ago -5"

# And alternatively, only output the logs
task docker-run ARGS="--zone_id [CLOUDFLARE_ZONE_ID] --start_minutes_ago -5" 2>/dev/null
```

## Publishing to PyPI

### GitHub-based version publishing

The simplest way to publish a new version (if you have committer rights) is to tag a commit and push it to the repo:

```shell
# At a certain commit, ideally after merging a PR to main
git tag v0.1.x
git push origin v0.1.x
```

A [GitHub Action](https://github.com/MihaiBojin/waf-downloader/actions) will run, build the library and publish it to the PyPI repositories.

### Manual publish

These steps can also be performed locally. For these commands to work, you will need to export two environment variables (or define them in `.env`):

```shell
export TESTPYPI_PASSWORD=... # token for https://test.pypi.org/legacy/
export PYPI_PASSWORD=... # token for https://upload.pypi.org/legacy/
```

First, publish to the test repo and inspect the package:

```shell
task publish-test
```

If correct, distribute the wheel to the PyPI index:

```shell
task publish
```

Verify the distributed code

```shell
task publish-verify
```

## Cloudflare WAF documentation

- <https://developers.cloudflare.com/analytics/graphql-api/tutorials/querying-firewall-events>
- <https://developers.cloudflare.com/analytics/graphql-api/tutorials/export-graphql-to-csv/>
