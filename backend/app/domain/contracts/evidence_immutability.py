import hashlib
import json
from sqlalchemy.orm import Session
from app.db.models import SolverJob

AEROSEAT_ENGINE_VERSION = "1.0.0"

def compute_sha256(data: str | bytes) -> str:
    if isinstance(data, str):
        data = data.encode('utf-8')
    return hashlib.sha256(data).hexdigest()

def compute_artifact_hash(content: str | bytes) -> str:
    """Artifact Hash = SHA256(file content)."""
    return compute_sha256(content)

def compute_configuration_hash(
    model_revision_sha256: str,
    mesh_sha256: str,
    material_sha256: str,
    solver_mat_rep_sha256: str,
    contact_sha256: str,
    boundary_condition_sha256: str,
    dummy_sha256: str,
    pulse_sha256: str
) -> str:
    """Configuration Hash = SHA256(ModelRevision + Mesh + Material + SolverMaterialRepresentation + Contact + BC + Dummy + Pulse)."""
    combined = (
        f"{model_revision_sha256}:"
        f"{mesh_sha256}:"
        f"{material_sha256}:"
        f"{solver_mat_rep_sha256}:"
        f"{contact_sha256}:"
        f"{boundary_condition_sha256}:"
        f"{dummy_sha256}:"
        f"{pulse_sha256}"
    )
    return compute_sha256(combined)

def compute_execution_fingerprint(
    configuration_hash: str,
    solver_name: str,
    solver_version: str,
    solver_build: str,
    processing_definition_sha256: str
) -> str:
    """Execution Fingerprint = SHA256(ConfigurationHash + SolverName + SolverVersion + SolverBuild + EngineVersion + ProcessingDef.sha256)."""
    combined = (
        f"{configuration_hash}:"
        f"{solver_name.upper()}:"
        f"{solver_version}:"
        f"{solver_build}:"
        f"{AEROSEAT_ENGINE_VERSION}:"
        f"{processing_definition_sha256}"
    )
    return compute_sha256(combined)

def get_completed_job_by_fingerprint(db: Session, execution_fingerprint: str) -> SolverJob | None:
    """Idempotency check: returns completed job matching fingerprint if available."""
    return db.query(SolverJob).filter(
        SolverJob.execution_fingerprint == execution_fingerprint,
        SolverJob.status == "COMPLETED"
    ).first()
