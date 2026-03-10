#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

MODE="${1:-local}"
SERVICE="${2:-robot-1}"
ACTION="${3:-once}"

case "${MODE}" in
  local)
    ROBOT_ID="${ROBOT_ID:-${SERVICE}}"
    CLIENT_STATE_DIR="${CLIENT_STATE_DIR:-client/state/${ROBOT_ID}}"
    export ROBOT_ID
    export CLIENT_STATE_DIR

    if [[ "${ACTION}" == "runner" ]]; then
      PYTHONPATH=. python3 -m client.app.main --runner
    else
      PYTHONPATH=. python3 -m client.app.main
    fi
    ;;
  docker)
    if [[ "${ACTION}" == "runner" ]]; then
      docker compose run --rm --no-deps "${SERVICE}" python3 -m client.app.main --runner
    else
      docker compose run --rm --no-deps "${SERVICE}" python3 -m client.app.main
    fi
    ;;
  *)
    echo "Usage: ./client/run_client.sh [local|docker] [robot-service] [once|runner]"
    exit 1
    ;;
esac
