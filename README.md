# Cloudflare Web Application Firewall downloader

![Build Status](https://github.com/MihaiBojin/waf-downloader/actions/workflows/python-tests.yml/badge.svg)
[![PyPI version](https://badge.fury.io/py/waf-downloader.svg)](https://badge.fury.io/py/waf-downloader)
[![Python Versions](https://img.shields.io/pypi/pyversions/waf-downloader.svg)](https://pypi.org/project/waf-downloader/)
[![License](https://img.shields.io/github/license/waf-downloader/waf-downloader.svg)](LICENSE)

Use this repo as a template for starting multi-package Python projects.

## AWS credentials

```shell
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
```

## Documentation

- <https://developers.cloudflare.com/analytics/graphql-api/tutorials/querying-firewall-events>
- <https://developers.cloudflare.com/analytics/graphql-api/tutorials/export-graphql-to-csv/>

## Schema

See [src/waf_logs/resources/db/](./src/waf_logs/resources/db) for a list of schemas that are auto-applied at start.

## Quickstart

The project is published to <https://pypi.org/project/waf-downloader/>.
Install it via:

```shell
pip install waf-downloader

# or alternatively, directly from git
pip install "git+https://github.com/MihaiBojin/waf-downloader@main"
```

### Build and run with Docker

Define secrets in an `.env` file (do not quote values):

```properties
CLOUDFLARE_TOKEN=...
CLOUDFLARE_ZONE_ID=...
DB_CONN_STR=...
CHUNK_SIZE=500 # Optional
```

Build and run:

```shell
make docker docker-run
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

These steps can also be performed locally. For these commands to work, you will need to export two environment variables:

```shell
export TESTPYPI_PASSWORD=... # token for https://test.pypi.org/legacy/
export PYPI_PASSWORD=... # token for https://upload.pypi.org/legacy/
```

First, publish to the test repo and inspect the package:

```shell
make publish-test
```

If correct, distribute the wheel to the PyPI index:

```shell
make publish
```

Verify the distributed code

```shell
make publish-verify
```
