# Demo Flow

Use `./scripts/demo.sh` for the full end-to-end demo.

The script demonstrates:

- 2 gateways
- 6 robots (3 per gateway)
- central dashboard

## Steps

1. Reset local state.
2. Start dashboard and gateways in offline mode.
3. Publish a new signed release.
4. Bring gateways online and run sync.
5. Put gateways offline again.
6. Run robot update cycles from gateway cache.
7. Bring gateways online and forward buffered metrics.
8. Read fleet summary from dashboard.

## Expected result

Dashboard shows robots across both gateways with updated versions and health status.
