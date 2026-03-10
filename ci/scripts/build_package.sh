#!/usr/bin/env bash
set -e

VERSION="${1:-1.0.0}"
SCENARIO="${2:-good}"

OUTPUT_DIR="ci/artifacts"
ARTIFACT_NAME="robot-app-${VERSION}.bin"
ARTIFACT_PATH="${OUTPUT_DIR}/${ARTIFACT_NAME}"

mkdir -p "${OUTPUT_DIR}"

case "${SCENARIO}" in
    good|faulty_signature|faulty_checksum|missing_sbom|missing_attestation)
        ARTIFACT_HEALTH="healthy"
        ;;
    faulty|faulty_health)
        ARTIFACT_HEALTH="broken"
        ;;
    *)
        echo "Unknown scenario: ${SCENARIO}" >&2
        echo "Supported scenarios: good,faulty_health,faulty_signature,faulty_checksum,missing_sbom,missing_attestation" >&2
        exit 1
        ;;
esac

echo "robot software version ${VERSION}" > "${ARTIFACT_PATH}"
echo "status=${ARTIFACT_HEALTH}" >> "${ARTIFACT_PATH}"

echo "Artifact scenario: ${SCENARIO}"

echo "Artifact created: ${ARTIFACT_PATH}"
