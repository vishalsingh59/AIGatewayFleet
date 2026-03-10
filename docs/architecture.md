# Architecture

## Goal

Allow robots to update safely without direct internet access, and still report fleet health centrally.

## Components

- `ci/`
  - builds the release artifact
  - generates SBOM and attestation
  - generates manifest
  - signs files
- `gateway/`
  - syncs release files when online
  - verifies signatures and checksums
  - caches validated files locally
  - serves update endpoints to robots
  - buffers metrics and forwards them to dashboard
- `client/`
  - checks for updates from gateway
  - verifies manifest, SBOM, attestation, and artifact offline
  - installs update
  - runs health check
  - rolls back on failure
  - sends metrics to gateway
- `dashboard/`
  - receives metrics from gateways
  - aggregates by gateway and robot
  - exposes fleet status endpoints

## Diagram

```text                
                   +-------------------+
                   |        CI.        |
                   |  Build + Sign     |
                   |  Packages + SBOM  |
                   +---------+---------+
                             |
                    (sync when online)
                             |
                    +-------v--------+
                    |     Gateway    |
                    |----------------|
                    | Artifact Cache |
                    | Update API     |
                    | Metrics Buffer |
                    +---+-------+----+
                        |       |
                      (local network)     
                        |       |
                        |       |
         +-------+------+       +------+-------+
         | Robot Client |       | Robot Client |
         |--------------|       |--------------|
         | Check update |       | Check update |
         | Verify sig   |       | Verify sig   |
         | Install OTA  |       | Install OTA  |
         | Send metrics |       | Send metrics |
         +--------------+       +--------------+
                            |
                            | 
                  (when gateway online)
                            v
                  +-------------------+
                  | Central Dashboard |
                  |-------------------|
                  | Fleet status      |
                  | Metrics           |
                  | Version tracking  |
                  +-------------------+
```

## Data Flow

1. CI publishes:
   - `robot-app-<version>.bin`
   - `sbom-<version>.json`
   - `attestation-<version>.json`
   - `manifest-<version>.json`
   - signatures for each file
2. Gateway syncs and verifies files, then stores them in local cache.
3. Robot fetches manifest from gateway, verifies files offline, downloads package, installs, and health-checks.
4. Robot sends metrics to gateway.
5. Gateway forwards buffered metrics to dashboard when connectivity is available.

## Why This Is Offline-First

- Robots never call internet services.
- Gateways can serve updates from local cache during outages.
- Verification uses local public keys.
- Metrics are buffered locally until forwarding succeeds.

## Known Limit

- Delta patching is not implemented.
