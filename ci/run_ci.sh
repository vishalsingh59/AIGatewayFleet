#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

MODE="${1:-local}"
VERSION="${2:-1.1.0}"
SCENARIO="${3:-good}"

case "${MODE}" in
  local)
    ./ci/scripts/publish_release.sh "${VERSION}" "${SCENARIO}"
    ;;
  docker)
    docker compose run --rm ci bash -lc "./ci/scripts/publish_release.sh ${VERSION} ${SCENARIO}"
    ;;
  *)
    echo "Usage: ./ci/run_ci.sh [local|docker] [version] [scenario]"
    exit 1
    ;;
esac
