# AI Gateway Fleet

This project is a local demo for offline robot updates and fleet metrics.

Robots do not use the internet. A gateway at each site downloads updates when online, then robots pull those updates from the local gateway. Gateways also buffer robot metrics and forward them to a central dashboard.

## Project Layout

- `ci/` - build and publish scripts (artifact, SBOM, attestation, manifest, signatures)
- `gateway/` - sync, verify, cache, update APIs, metrics buffering/forwarding
- `client/` - robot update agent (check, verify, install, health check, rollback, metrics)
- `dashboard/` - aggregated fleet metrics API
- `scripts/` - setup/reset/demo orchestration scripts
- `docs/` - architecture, security, and demo flow
- `tests/` - assignment-focused tests

## Prerequisites

- Python 3.8+
- pip
- venv
- openssl
- curl

- Docker
- Docker Compose plugin (`docker compose`)

## Setup

```bash
./scripts/setup_env.sh
source venv/bin/activate
```

## Main Demo

This is the recommended command for the full assignment flow (2 gateways, 6 robots):

```bash
./scripts/demo.sh
./scripts/demo.sh 1.2.0 good
```

`demo.sh` writes logs to `logs/demo/<utc-timestamp>/` and clears old demo logs at the start of each run.

## Run Services Manually

Use these scripts if you want to run each service independently.

```bash
# CI publisher
./ci/run_ci.sh local 1.2.0 good
./ci/run_ci.sh docker 1.2.0 good

# Dashboard
./dashboard/run_dashboard.sh local start
./dashboard/run_dashboard.sh docker start

# Gateway
./gateway/run_gateway.sh local start gateway-1 true
./gateway/run_gateway.sh docker start gateway-1 true
./gateway/run_gateway.sh docker start gateway-2 false

# Robot client (single cycle)
./client/run_client.sh local robot-1
./client/run_client.sh docker robot-1
```

## Run Tests

```bash
source venv/bin/activate
python3 -m pytest -q
```

## Periodic CI Publisher

```bash
START_VERSION=1.2.0 \
PUBLISH_INTERVAL=30 \
SCENARIO_SEQUENCE=good,good,faulty_signature,faulty_checksum,faulty_health \
MAX_RELEASES=5 \
./ci/scripts/publish_artifacts.sh
```

Run in Docker:

```bash
docker compose run --rm ci
```

## Run Docker Stack

```bash
./scripts/reset_demo_state.sh
docker compose up --build
```

## Known Limits

- Delta patching is not implemented (resumable download is implemented).
- Gateway sync and forwarding are API-triggered (`/sync`, `/forward`) by default.
