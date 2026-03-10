import json
import sys
from pathlib import Path

from shared.security import canonical_json_bytes, sha256_file

version = sys.argv[1] if len(sys.argv) > 1 else "1.0.0"

output_dir = Path("ci/manifests")
output_dir.mkdir(parents=True, exist_ok=True)

artifact_path = Path("ci/artifacts") / f"robot-app-{version}.bin"
sbom_path = Path("ci/sbom") / f"sbom-{version}.json"
attestation_path = Path("ci/attestations") / f"attestation-{version}.json"

if not artifact_path.exists():
    raise FileNotFoundError(f"Artifact missing: {artifact_path}")

if not sbom_path.exists():
    raise FileNotFoundError(f"SBOM missing: {sbom_path}")

if not attestation_path.exists():
    raise FileNotFoundError(f"Attestation missing: {attestation_path}")

manifest = {
    "version": version,
    "artifact_name": f"robot-app-{version}.bin",
    "artifact_url": f"/updates/package/{version}",
    "sbom_name": f"sbom-{version}.json",
    "attestation_name": f"attestation-{version}.json",
    "signature_name": f"robot-app-{version}.sig",
    "sbom_signature_name": f"sbom-{version}.sig",
    "attestation_signature_name": f"attestation-{version}.sig",
    "manifest_signature_name": f"manifest-{version}.sig",
    "artifact_sha256": sha256_file(artifact_path),
    "sbom_sha256": sha256_file(sbom_path),
    "attestation_sha256": sha256_file(attestation_path),
}

manifest_path = output_dir / f"manifest-{version}.json"
manifest_path.write_bytes(canonical_json_bytes(manifest))

print(f"Manifest created: {manifest_path}")
