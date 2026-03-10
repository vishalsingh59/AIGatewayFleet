# System Overview

This project shows a simple offline update pattern for a robot fleet.

## Main idea

- Robots are isolated from the internet.
- Gateways act as the update and metrics bridge.
- Dashboard gives a central fleet view.

## Reliability behavior

- Robots can still update while gateway internet is down, if files are already cached.
- Gateway keeps metrics in local buffer if dashboard is unavailable.

## Security behavior

- CI signs release files.
- Gateway and client verify signatures and checksums offline.
- Client blocks downgrade/replay updates.
