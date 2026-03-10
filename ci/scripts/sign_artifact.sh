#!/usr/bin/env bash
set -e
umask 077

VERSION="${1:-1.0.0}"
OUTPUT_DIR="ci/signatures"
KEY_DIR="ci/keys"
PRIVATE_KEY="${KEY_DIR}/update-private.pem"
PUBLIC_KEY="${KEY_DIR}/update-public.pem"

ARTIFACT_PATH="ci/artifacts/robot-app-${VERSION}.bin"
SBOM_PATH="ci/sbom/sbom-${VERSION}.json"
ATTESTATION_PATH="ci/attestations/attestation-${VERSION}.json"
MANIFEST_PATH="ci/manifests/manifest-${VERSION}.json"

mkdir -p "${OUTPUT_DIR}"
mkdir -p "${KEY_DIR}"

if [ ! -f "${PRIVATE_KEY}" ] || [ ! -f "${PUBLIC_KEY}" ]; then
  openssl genpkey -algorithm RSA -out "${PRIVATE_KEY}" -pkeyopt rsa_keygen_bits:2048 >/dev/null 2>&1
  openssl rsa -in "${PRIVATE_KEY}" -pubout -out "${PUBLIC_KEY}" >/dev/null 2>&1
fi

openssl dgst -sha256 -sign "${PRIVATE_KEY}" -out "${OUTPUT_DIR}/robot-app-${VERSION}.sig" "${ARTIFACT_PATH}"
openssl dgst -sha256 -sign "${PRIVATE_KEY}" -out "${OUTPUT_DIR}/sbom-${VERSION}.sig" "${SBOM_PATH}"
openssl dgst -sha256 -sign "${PRIVATE_KEY}" -out "${OUTPUT_DIR}/attestation-${VERSION}.sig" "${ATTESTATION_PATH}"
openssl dgst -sha256 -sign "${PRIVATE_KEY}" -out "${OUTPUT_DIR}/manifest-${VERSION}.sig" "${MANIFEST_PATH}"

echo "Signatures created for version ${VERSION}"
