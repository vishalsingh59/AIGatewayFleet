#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

MODE="${1:-local}"
ACTION="${2:-start}"
SERVICE="${3:-gateway-1}"
ONLINE="${4:-true}"

case "${MODE}" in
  local)
    if [[ "${ACTION}" != "start" ]]; then
      echo "Local mode supports only: start"
      exit 1
    fi

    if [[ "${SERVICE}" == "gateway-2" ]]; then
      default_gateway_id="gateway-2"
      default_data_dir="gateway/data-gw2"
      default_port="8081"
    else
      default_gateway_id="gateway-1"
      default_data_dir="gateway/data-gw1"
      default_port="8080"
    fi

    export GATEWAY_ID="${GATEWAY_ID:-${default_gateway_id}}"
    export GATEWAY_DATA_DIR="${GATEWAY_DATA_DIR:-${default_data_dir}}"
    export DASHBOARD_METRICS_URL="${DASHBOARD_METRICS_URL:-http://127.0.0.1:9000/metrics}"
    export GATEWAY_ONLINE="${GATEWAY_ONLINE:-${ONLINE}}"
    GATEWAY_BIND_HOST="${GATEWAY_BIND_HOST:-127.0.0.1}"
    GATEWAY_PORT="${GATEWAY_PORT:-${default_port}}"
    PYTHONPATH=. uvicorn gateway.app.main:app --host "${GATEWAY_BIND_HOST}" --port "${GATEWAY_PORT}"
    ;;
  docker)
    case "${ACTION}" in
      start)
        if [[ "${SERVICE}" == "gateway-2" ]]; then
          GW2_ONLINE="${ONLINE}" docker compose up -d gateway-2
        else
          GW1_ONLINE="${ONLINE}" docker compose up -d gateway-1
        fi
        ;;
      stop)
        docker compose stop "${SERVICE}"
        ;;
      *)
        echo "Docker mode actions: start|stop"
        exit 1
        ;;
    esac
    ;;
  *)
    echo "Usage: ./gateway/run_gateway.sh [local|docker] [start|stop] [gateway-1|gateway-2] [true|false]"
    exit 1
    ;;
esac
