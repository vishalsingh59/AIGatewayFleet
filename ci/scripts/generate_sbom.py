import json
import sys
from pathlib import Path

version = sys.argv[1] if len(sys.argv) > 1 else "1.0.0"

output_dir = Path("ci/sbom")
output_dir.mkdir(parents=True, exist_ok=True)

sbom = {
    "artifact": f"robot-app-{version}.bin",
    "version": version,
    "components": [
        {"name": "robot-app", "version": version},
        {"name": "python-runtime", "version": "3.x"}
    ]
}

sbom_path = output_dir / f"sbom-{version}.json"

with open(sbom_path, "w", encoding="utf-8") as f:
    json.dump(sbom, f, indent=2)

print(f"SBOM created: {sbom_path}")