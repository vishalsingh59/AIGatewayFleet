# AI Gateway Fleet

Proof-of-concept for offline robot updates and fleet metrics aggregation.

## What It Does

- CI builds and signs a release artifact, SBOM, attestation, and manifest.
- Gateways sync and cache verified releases when online.
- Robots pull updates from their local gateway only.
- Robots verify signatures offline, install, health-check, and roll back on failure.
- Gateways buffer robot metrics and forward them to a central dashboard.
- The dashboard shows fleet health and version state across multiple gateways.

## Run The Demo

```bash
./scripts/demo.sh
./scripts/demo.sh 1.2.0 good
```

Demo logs are written to `logs/demo/timestamp_01/`, `timestamp_02/`, and so on.

You can also try failure paths:

```bash
./scripts/demo.sh 1.2.0 faulty_health
./ci/run_ci.sh docker 1.2.0 faulty_signature
./ci/run_ci.sh docker 1.2.0 faulty_checksum
```

- `faulty_health` shows rollback after a failed health check.
- `faulty_signature` and `faulty_checksum` show release rejection during verification.

## Run Tests

```bash
./scripts/setup_env.sh
source venv/bin/activate
python3 -m pytest -q
```

## Repo Layout

- `ci/` release build and signing scripts
- `gateway/` gateway API, artifact sync, and metrics buffering
- `client/` robot update client
- `dashboard/` fleet metrics API
- `scripts/` demo and helper scripts
- `docs/` architecture, security, and demo notes
- `tests/` automated tests

## Notes

- Resumable downloads are implemented.
- Delta patching is not implemented.
- mTLS is not implemented.
