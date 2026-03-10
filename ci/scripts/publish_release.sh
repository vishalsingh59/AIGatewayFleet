#!/usr/bin/env bash
set -e

VERSION="${1:-1.0.0}"
SCENARIO="${2:-good}"

echo "Publishing release ${VERSION} with scenario: ${SCENARIO}"

./ci/scripts/build_package.sh "${VERSION}" "${SCENARIO}"
PYTHONPATH=. python3 ci/scripts/generate_sbom.py "${VERSION}"
PYTHONPATH=. python3 ci/scripts/generate_attestation.py "${VERSION}"
PYTHONPATH=. python3 ci/scripts/generate_manifest.py "${VERSION}"
./ci/scripts/sign_artifact.sh "${VERSION}"

case "${SCENARIO}" in
  good|faulty|faulty_health)
    ;;
  faulty_signature)
    echo "tampered-signature-${VERSION}" > "ci/signatures/robot-app-${VERSION}.sig"
    echo "Applied scenario mutation: artifact signature tampered"
    ;;
  faulty_checksum)
    echo "tampered-payload-${VERSION}" >> "ci/artifacts/robot-app-${VERSION}.bin"
    echo "Applied scenario mutation: artifact bytes changed after signing"
    ;;
  missing_sbom)
    rm -f "ci/sbom/sbom-${VERSION}.json"
    echo "Applied scenario mutation: SBOM removed"
    ;;
  missing_attestation)
    rm -f "ci/attestations/attestation-${VERSION}.json"
    echo "Applied scenario mutation: attestation removed"
    ;;
  *)
    echo "Unknown scenario: ${SCENARIO}" >&2
    echo "Supported scenarios: good,faulty_health,faulty_signature,faulty_checksum,missing_sbom,missing_attestation" >&2
    exit 1
    ;;
esac

mkdir -p gateway/keys client/keys
cp ci/keys/update-public.pem gateway/keys/update-public.pem
cp ci/keys/update-public.pem client/keys/update-public.pem

echo "Release ${VERSION} published successfully"
