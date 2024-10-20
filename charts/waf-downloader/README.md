# Helm chart for the Cloudflare Web Application Firewall log downloader

## Add the Helm repository

```shell
helm repo add waf https://MihaiBojin.github.io/waf-downloader

# or pull new versions if already installed
helm repo update
```

## Install the Helm chart in your cluster

```shell
helm install -f config.yaml waf-downloader waf/waf-downloader

# or upgrade
helm upgrade waf-downloader waf/waf-downloader
```

You must also provide a few configuration values, e.g.:

```yaml
# config.yaml
cloudflare:
  apiToken: <CLOUDFLARE_API_TOKEN> # Specifies the Cloudflare API token
  zoneId: <CLOUDFLARE_ZONE_ID> # Specifies the zone to download logs from
outputs:
  dbConnStr: <POSTGRES_CONNECTION_STRING> # Specifies a Postgres endpoint to send the logs to
```

## Delete the Helm chart from your cluster

```shell
helm delete waf-downloader
```

## Or uninstall a specific release

```shell
helm list
helm uninstall waf-downloader-<RELEASE_NAME>
```

More details are provided in [Helm's documentation](https://helm.sh/docs/intro/quickstart/#learn-about-releases).
