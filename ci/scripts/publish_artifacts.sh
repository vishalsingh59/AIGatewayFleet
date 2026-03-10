#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

START_VERSION="${START_VERSION:-1.0.0}"
PUBLISH_INTERVAL="${PUBLISH_INTERVAL:-30}"
SCENARIO_SEQUENCE="${SCENARIO_SEQUENCE:-${MODE_SEQUENCE:-good}}"
MAX_RELEASES="${MAX_RELEASES:-5}"

IFS=',' read -r -a SCENARIOS <<< "${SCENARIO_SEQUENCE}"
if [ "${#SCENARIOS[@]}" -eq 0 ]; then
  SCENARIOS=("good")
fi

increment_patch_version() {
  local version="$1"
  local major minor patch

  IFS='.' read -r major minor patch <<< "${version}"

  if [[ -z "${major}" || -z "${minor}" || -z "${patch}" ]]; then
    echo "Invalid semver version: ${version}" >&2
    return 1
  fi

  if ! [[ "${major}" =~ ^[0-9]+$ && "${minor}" =~ ^[0-9]+$ && "${patch}" =~ ^[0-9]+$ ]]; then
    echo "Version parts must be numeric: ${version}" >&2
    return 1
  fi

  patch=$((patch + 1))
  echo "${major}.${minor}.${patch}"
}

version="${START_VERSION}"
release_count=0
scenario_index=0

echo "Starting publisher"
echo "- start version : ${START_VERSION}"
echo "- interval (s)  : ${PUBLISH_INTERVAL}"
echo "- scenario sequence : ${SCENARIO_SEQUENCE}"
echo "- max releases  : ${MAX_RELEASES} (0 means infinite)"

while true; do
  scenario="${SCENARIOS[$scenario_index]}"
  echo "[publisher] releasing version=${version} scenario=${scenario}"

  ./ci/scripts/publish_release.sh "${version}" "${scenario}"

  release_count=$((release_count + 1))

  if [ "${MAX_RELEASES}" -gt 0 ] && [ "${release_count}" -ge "${MAX_RELEASES}" ]; then
    echo "[publisher] reached MAX_RELEASES=${MAX_RELEASES}. stopping."
    break
  fi

  version="$(increment_patch_version "${version}")"
  scenario_index=$(((scenario_index + 1) % ${#SCENARIOS[@]}))

  sleep "${PUBLISH_INTERVAL}"
done
