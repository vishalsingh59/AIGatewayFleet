#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

VERSION="${1:-1.1.0}"
MODE="${2:-good}"
LOG_ROOT="${ROOT_DIR}/logs/demo"

next_run_id() {
  local max_index=0
  local entry name suffix numeric

  mkdir -p "${LOG_ROOT}"

  for entry in "${LOG_ROOT}"/*; do
    if [ ! -d "${entry}" ]; then
      continue
    fi

    name="$(basename "${entry}")"
    suffix="${name##*_}"
    if [[ "${name}" == timestamp_* && "${suffix}" =~ ^[0-9]+$ ]]; then
      numeric=$((10#${suffix}))
      if [ "${numeric}" -gt "${max_index}" ]; then
        max_index="${numeric}"
      fi
    fi
  done

  printf "timestamp_%02d" "$((max_index + 1))"
}

RUN_ID="$(next_run_id)"
RUN_LOG_DIR="${LOG_ROOT}/${RUN_ID}"
RUN_LOG_FILE="${RUN_LOG_DIR}/demo.log"

DASHBOARD_URL="http://127.0.0.1:9000"
GW1_URL="http://127.0.0.1:8080"
GW2_URL="http://127.0.0.1:8081"

prepare_logs() {
  mkdir -p "${RUN_LOG_DIR}"
  exec > >(tee -a "${RUN_LOG_FILE}") 2>&1
}

capture_compose_logs() {
  if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    docker compose logs --no-color >"${RUN_LOG_DIR}/docker-compose.log" 2>&1 || true
  fi
}

wait_for_http() {
  local url="$1"
  local timeout_s="${2:-60}"
  local elapsed=0
  until curl -fsS "${url}" >/dev/null 2>&1; do
    sleep 1
    elapsed=$((elapsed + 1))
    if [ "${elapsed}" -ge "${timeout_s}" ]; then
      echo "Timed out waiting for ${url}"
      return 1
    fi
  done
}

run_robot_once() {
  local service="$1"
  echo "Running ${service} update cycle"
  ./client/run_client.sh docker "${service}"
}

ensure_docker_daemon() {
  if docker info >/dev/null 2>&1; then
    return 0
  fi

  echo "Docker daemon is not running."
  if [[ "$(uname -s)" == "Darwin" ]] && command -v open >/dev/null 2>&1; then
    echo "Attempting to start Docker Desktop..."
    open -a Docker >/dev/null 2>&1 || true
  fi

  echo "Waiting for Docker daemon..."
  local waited=0
  local timeout_s=90
  until docker info >/dev/null 2>&1; do
    sleep 2
    waited=$((waited + 2))
    if [ "${waited}" -ge "${timeout_s}" ]; then
      echo "Docker daemon is still unavailable after ${timeout_s}s."
      echo "Please start Docker and rerun ./scripts/demo.sh"
      return 1
    fi
  done

  echo "Docker daemon is running."
}

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required to run this demo"
  exit 1
fi

prepare_logs
trap capture_compose_logs EXIT
echo "Logs directory: ${RUN_LOG_DIR}"

if ! docker compose version >/dev/null 2>&1; then
  echo "docker compose plugin is required to run this demo"
  exit 1
fi

ensure_docker_daemon

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required to run this demo"
  exit 1
fi

echo ""
echo "=== Reset demo state ==="
./scripts/reset_demo_state.sh

echo ""
echo "=== Stop previous compose stack ==="
docker compose down --remove-orphans >/dev/null 2>&1 || true

echo ""
echo "=== Step 1: Start dashboard + gateways offline ==="
./dashboard/run_dashboard.sh docker start
./gateway/run_gateway.sh docker start gateway-1 false
./gateway/run_gateway.sh docker start gateway-2 false
wait_for_http "${DASHBOARD_URL}/health"
wait_for_http "${GW1_URL}/health"
wait_for_http "${GW2_URL}/health"
curl -fsS "${GW1_URL}/health" | python3 -m json.tool
curl -fsS "${GW2_URL}/health" | python3 -m json.tool

echo ""
echo "=== Step 2: Publish release ${VERSION} (${MODE}) ==="
./ci/run_ci.sh docker "${VERSION}" "${MODE}"

echo ""
echo "=== Step 3: Bring gateways online and sync ==="
./gateway/run_gateway.sh docker start gateway-1 true
./gateway/run_gateway.sh docker start gateway-2 true
wait_for_http "${GW1_URL}/health"
wait_for_http "${GW2_URL}/health"
curl -fsS -X POST "${GW1_URL}/sync" | python3 -m json.tool
curl -fsS -X POST "${GW2_URL}/sync" | python3 -m json.tool

echo ""
echo "=== Step 4: Gateways offline again (serve from cache) ==="
./gateway/run_gateway.sh docker start gateway-1 false
./gateway/run_gateway.sh docker start gateway-2 false
wait_for_http "${GW1_URL}/health"
wait_for_http "${GW2_URL}/health"
curl -fsS "${GW1_URL}/health" | python3 -m json.tool
curl -fsS "${GW2_URL}/health" | python3 -m json.tool

echo ""
echo "=== Step 5: Fleet update cycle (2 gateways, 6 robots) ==="
run_robot_once robot-1
run_robot_once robot-2
run_robot_once robot-3
run_robot_once robot-4
run_robot_once robot-5
run_robot_once robot-6

echo ""
echo "=== Step 6: Verify metrics buffered on both gateways ==="
if [ -f gateway/data-gw1/metrics/buffer.jsonl ]; then
  echo "gateway-1 buffered lines:"
  wc -l gateway/data-gw1/metrics/buffer.jsonl
fi
if [ -f gateway/data-gw2/metrics/buffer.jsonl ]; then
  echo "gateway-2 buffered lines:"
  wc -l gateway/data-gw2/metrics/buffer.jsonl
fi

echo ""
echo "=== Step 7: Gateways reconnect and forward metrics ==="
./gateway/run_gateway.sh docker start gateway-1 true
./gateway/run_gateway.sh docker start gateway-2 true
wait_for_http "${GW1_URL}/health"
wait_for_http "${GW2_URL}/health"
curl -fsS -X POST "${GW1_URL}/forward" | python3 -m json.tool
curl -fsS -X POST "${GW2_URL}/forward" | python3 -m json.tool

echo ""
echo "=== Dashboard fleet summary ==="
curl -fsS "${DASHBOARD_URL}/fleet/summary" | python3 -m json.tool

echo ""
echo "=== Dashboard fleet view ==="
curl -fsS "${DASHBOARD_URL}/fleet" | python3 -m json.tool

echo ""
echo "Fleet demo completed successfully."
echo "To stop services: docker compose down"
echo "Run logs: ${RUN_LOG_FILE}"
echo "Compose logs: ${RUN_LOG_DIR}/docker-compose.log"
