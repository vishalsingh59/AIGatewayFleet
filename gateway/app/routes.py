from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from gateway.app.services import (
    GATEWAY_ID,
    forward_buffered_metrics,
    get_all_signatures,
    get_attestation_path,
    get_attestation_signature_path,
    get_latest_manifest_path,
    get_manifest_signature_path,
    get_package_path,
    get_sbom_path,
    get_sbom_signature_path,
    get_signature_path,
    is_gateway_online,
    store_metric,
    sync_from_ci,
)

router = APIRouter()


class MetricPayload(BaseModel):
    robot_id: str = Field(..., min_length=1)
    version: str = Field(..., min_length=1)
    status: Literal["healthy", "rolled_back", "unhealthy", "failed"]
    cpu: Optional[int] = Field(default=None, ge=0, le=100)
    memory: Optional[int] = Field(default=None, ge=0, le=100)
    timestamp: Optional[int] = Field(default=None, ge=0)

    def to_payload(self) -> dict:
        model_dump = getattr(self, "model_dump", None)
        if callable(model_dump):
            return model_dump()
        return self.dict()


@router.get("/health")
def health():
    return {
        "status": "gateway running",
        "gateway_id": GATEWAY_ID,
        "online": is_gateway_online(),
    }


@router.post("/metrics", tags=["metrics"])
def receive_metric(metric: MetricPayload):
    payload = metric.to_payload()
    payload["gateway_id"] = GATEWAY_ID
    store_metric(payload)
    return {"status": "metric buffered", "gateway_id": GATEWAY_ID}


@router.get("/updates/manifest", tags=["updates"])
def get_manifest():
    manifest_path = get_latest_manifest_path()
    if not manifest_path:
        raise HTTPException(status_code=404, detail="No manifest available")
    return FileResponse(manifest_path, media_type="application/json")


@router.get("/updates/package/{version}", tags=["updates"])
def get_package(version: str):
    package_path = get_package_path(version)
    if not package_path:
        raise HTTPException(status_code=404, detail=f"Package for version {version} not found")
    return FileResponse(package_path, media_type="application/octet-stream")


@router.get("/updates/sbom/{version}", tags=["updates"])
def get_sbom(version: str):
    sbom_path = get_sbom_path(version)
    if not sbom_path:
        raise HTTPException(status_code=404, detail=f"SBOM for version {version} not found")
    return FileResponse(sbom_path, media_type="application/json")


@router.get("/updates/attestation/{version}", tags=["updates"])
def get_attestation(version: str):
    attestation_path = get_attestation_path(version)
    if not attestation_path:
        raise HTTPException(status_code=404, detail=f"Attestation for version {version} not found")
    return FileResponse(attestation_path, media_type="application/json")


@router.get("/updates/signature/{version}", tags=["updates"])
def get_signature(version: str):
    signature_path = get_signature_path(version)
    if not signature_path:
        raise HTTPException(status_code=404, detail=f"Signature for version {version} not found")
    return FileResponse(signature_path, media_type="application/octet-stream")


@router.get("/updates/sbom-signature/{version}", tags=["updates"])
def get_sbom_signature(version: str):
    signature_path = get_sbom_signature_path(version)
    if not signature_path:
        raise HTTPException(status_code=404, detail=f"SBOM signature for version {version} not found")
    return FileResponse(signature_path, media_type="application/octet-stream")


@router.get("/updates/attestation-signature/{version}", tags=["updates"])
def get_attestation_signature(version: str):
    signature_path = get_attestation_signature_path(version)
    if not signature_path:
        raise HTTPException(status_code=404, detail=f"Attestation signature for version {version} not found")
    return FileResponse(signature_path, media_type="application/octet-stream")


@router.get("/updates/manifest-signature/{version}", tags=["updates"])
def get_manifest_signature(version: str):
    signature_path = get_manifest_signature_path(version)
    if not signature_path:
        raise HTTPException(status_code=404, detail=f"Manifest signature for version {version} not found")
    return FileResponse(signature_path, media_type="application/octet-stream")


@router.get("/updates/signatures/{version}", tags=["updates"])
def get_signatures(version: str):
    signatures = get_all_signatures(version)
    if not any(signatures.values()):
        raise HTTPException(status_code=404, detail=f"No signatures found for version {version}")
    return signatures


@router.post("/sync", tags=["sync"])
def sync():
    if not is_gateway_online():
        raise HTTPException(status_code=503, detail="Gateway is offline. Sync unavailable.")
    return sync_from_ci()


@router.post("/forward", tags=["forward"])
def forward_metrics():
    if not is_gateway_online():
        raise HTTPException(
            status_code=503,
            detail="Gateway is offline. Metrics forwarding unavailable.",
        )

    return forward_buffered_metrics()
