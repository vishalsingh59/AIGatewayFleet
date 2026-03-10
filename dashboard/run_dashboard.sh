#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

MODE="${1:-local}"
ACTION="${2:-start}"
BIND_HOST="${DASHBOARD_BIND_HOST:-127.0.0.1}"
PORT="${DASHBOARD_PORT:-9000}"

case "${MODE}" in
  local)
    if [[ "${ACTION}" != "start" ]]; then
      echo "Local mode supports only: start"
      exit 1
    fi
    PYTHONPATH=. uvicorn dashboard.app.main:app --host "${BIND_HOST}" --port "${PORT}"
    ;;
  docker)
    case "${ACTION}" in
      start)
        docker compose up -d --build dashboard
        ;;
      stop)
        docker compose stop dashboard
        ;;
      *)
        echo "Docker mode actions: start|stop"
        exit 1
        ;;
    esac
    ;;
  *)
    echo "Usage: ./dashboard/run_dashboard.sh [local|docker] [start|stop]"
    exit 1
    ;;
esac
