# OSSC — OpenStack CLI Wrapper

[![CI](https://github.com/teamfighter/ossc/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/teamfighter/ossc/actions/workflows/ci.yml)
[![Release](https://github.com/teamfighter/ossc/actions/workflows/release.yml/badge.svg)](https://github.com/teamfighter/ossc/actions/workflows/release.yml)

OSSC reads OpenStack RC files (`rc-*.sh`) or their imported equivalents in a user config, applies the `OS_*` environment, and proxies commands to the `openstack` CLI.

## Prebuilt Images (Recommended)

Images are published to the GitHub Container Registry. The `main` tag is rebuilt on every commit to the default branch, while version tags are produced for releases. Pull an image and source the helper script:

```bash
export OSSC_VERSION=v0.0.0
docker pull ghcr.io/teamfighter/ossc:$OSSC_VERSION
curl -O https://raw.githubusercontent.com/teamfighter/ossc/main/ossc-docker.sh
chmod +x ossc-docker.sh
source ossc-docker.sh
ossc --help
```

Notes
- Inside the container `HOME=/tmp`, `XDG_CONFIG_HOME=/tmp/.config`.
- Your config is stored on the host: `~/.config/ossc/profiles.json` (the wrapper mounts it into the container).
- You can override the image with `OSSC_IMAGE` before `source ./ossc-docker.sh`.
- Prefer release tags for production; `main` is available for latest development builds: `docker pull ghcr.io/teamfighter/ossc:main`.

## Quick Start

1) Import issued RC files into config (ensure they exist in your working directory):
```bash
ossc config import-rc --profile dev  --catalog app --rc-file dev/rc-app.sh
ossc config import-rc --profile prod --catalog net --rc-file prod/rc-net.sh
# or batch import by directory
ossc config import-rc --profile dev --rc-dir ./dev
```

2) Run an OpenStack command
```bash
ossc --profile dev --catalog app server list
```

Helpful commands
```bash
# Wrapper and subcommands help
ossc -h
ossc config -h
ossc report -h

# Pass args directly to OpenStack
ossc --profile <p> --catalog <c> -- --help

# Dry-run (show env and command)
ossc --profile <p> --catalog <c> --dry-run server list
```

## Config & Credentials

- Config path: `~/.config/ossc/profiles.json` (or `$XDG_CONFIG_HOME/ossc/profiles.json`).
- Precedence:
  1) flags `--username` / `--password`
  2) env vars `OSS_USERNAME` / `OSS_PASSWORD`
  3) user config `profiles.json`
  4) `OS_USERNAME` from RC (username only)
- Secrets are not stored in the repository.

## Subcommands

- `config import-rc`: import RC files into user config (single file or batch via `--rc-dir`).
- `config list`: list profiles and their catalogs.
- `config set-cred`: set a password for a profile (username comes from RC/config of a catalog).
- `report [-f table|json|yaml|csv|value] [--out DIR]`: generate `openstack server list` reports for selected profiles/catalogs.

Examples
```bash
# Profiles/catalogs list
ossc config list

# Set password for a profile
ossc config set-cred --profile dev                      # prompts masked input
ossc config set-cred --profile dev --password 'secret'  # non-interactive

# Reports
ossc report                               # all profiles/catalogs
ossc --profile dev report                  # only profile dev
ossc --profile dev --catalog app report    # only dev/app
ossc --catalog app report                  # all profiles with catalog app
```

## Local Development (Optional)

Requires Python 3.8+
```bash
make setup
./ossc --profile <p> --catalog <c> <openstack args>
```

## Tests

```bash
make test
# or
python3 -m unittest -v
```

## Internals

- `core/cli.py` — CLI parsing, routing, proxy execution
- `core/config.py` — read/write `profiles.json`, structure, credentials resolution
- `core/rc.py` — `rc-*.sh` parsing, path building
- `core/env.py` — `openstack` discovery/bootstrapping (local .venv, user venv)
- `core/commands/config_cmd.py` — `config` commands
- `core/commands/report_cmd.py` — `report` command
- Entrypoints: `ossc` (bash wrapper), `ossc.py`

## GHCR Images

Images are published to the GitHub Container Registry. The main tag is rebuilt on every commit to the default branch, while version tags are produced for releases. Pull an image and source the helper script:

```bash
export OSSC_VERSION=v0.0.0
docker pull ghcr.io/teamfighter/ossc:$OSSC_VERSION
curl -O https://raw.githubusercontent.com/teamfighter/ossc/main/ossc-docker.sh
chmod +x ossc-docker.sh
source ossc-docker.sh
ossc --help
```

