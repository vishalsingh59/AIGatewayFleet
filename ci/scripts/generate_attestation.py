import json
import sys
from pathlib import Path

from shared.security import sha256_file

version = sys.argv[1] if len(sys.argv) > 1 else "1.0.0"

attestation_dir = Path("ci/attestations")
attestation_dir.mkdir(parents=True, exist_ok=True)

artifact_path = Path("ci/artifacts") / f"robot-app-{version}.bin"
sbom_path = Path("ci/sbom") / f"sbom-{version}.json"

if not artifact_path.exists():
    raise FileNotFoundError(f"Artifact missing: {artifact_path}")

if not sbom_path.exists():
    raise FileNotFoundError(f"SBOM missing: {sbom_path}")

attestation = {
    "type": "provenance",
    "predicate_type": "https://slsa.dev/provenance/v1",
    "subject": {
        "name": artifact_path.name,
        "version": version,
        "sha256": sha256_file(artifact_path),
    },
    "materials": [
        {
            "name": sbom_path.name,
            "sha256": sha256_file(sbom_path),
        }
    ],
    "builder": {
        "id": "local-ci-publisher",
    },
}

attestation_path = attestation_dir / f"attestation-{version}.json"
with open(attestation_path, "w", encoding="utf-8") as f:
    json.dump(attestation, f, indent=2)

print(f"Attestation created: {attestation_path}")
