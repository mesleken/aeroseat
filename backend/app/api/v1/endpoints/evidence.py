import os
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.core.config import settings
from app.db.models import (
    EngineeringAssessment, EvidenceArtifact, SimulationConfiguration, ModelRevision,
    RequirementStatus, Requirement, CredibilityAssessment, CorrelationRun, SolverJob,
    SimulationResult, InjuryMetrics, SeatArchitecture
)
from app.schemas.schemas import EngineeringAssessmentCreate
from app.domain.evidence_generator import generate_evidence_package
from app.domain.contracts.golden_dataset import run_golden_dataset_regression

router = APIRouter()

@router.post("/engineering-assessments", status_code=status.HTTP_201_CREATED)
def create_engineering_assessment(payload: EngineeringAssessmentCreate, db: Session = Depends(get_db)):
    config = db.query(SimulationConfiguration).filter(SimulationConfiguration.id == payload.simulation_configuration_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Simulation configuration not found")

    # Fetch requirement status for THIS SPECIFIC SIMULATION CONFIGURATION LINEAGE ONLY (P0 Item 17)
    job = db.query(SolverJob).filter(
        SolverJob.simulation_configuration_id == config.id,
        SolverJob.status == "COMPLETED"
    ).order_by(SolverJob.finished_at.desc()).first()

    req_summary = []
    if job:
        sim_res = db.query(SimulationResult).filter(SimulationResult.solver_job_id == job.id).first()
        if sim_res:
            inj = db.query(InjuryMetrics).filter(InjuryMetrics.simulation_result_id == sim_res.id).first()
            if inj:
                statuses = db.query(RequirementStatus).filter(RequirementStatus.injury_metrics_id == inj.id).all()
                for s in statuses:
                    req = db.query(Requirement).filter(Requirement.id == s.requirement_id).first()
                    if req:
                        req_summary.append({
                            "code": req.code,
                            "metric": req.metric,
                            "measured_value": s.measured_value,
                            "operator": req.limit_operator,
                            "limit_value": req.limit_value,
                            "unit": req.limit_unit,
                            "status": s.status,
                            "margin_percent": s.margin_percent
                        })

    assessment = EngineeringAssessment(
        simulation_configuration_id=payload.simulation_configuration_id,
        requirement_compliance_summary=req_summary,
        model_credibility_id=payload.model_credibility_id,
        overall_readiness=payload.overall_readiness,
        engineer_comments=payload.engineer_comments,
        approved_by=payload.approved_by if payload.approved_by else "usr-default-admin-001",
        approval_role=payload.approval_role
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return assessment

@router.post("/engineering-assessments/{assessment_id}/evidence-package")
def generate_evidence_artifact_endpoint(assessment_id: str, db: Session = Depends(get_db)):
    assessment = db.query(EngineeringAssessment).filter(EngineeringAssessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Engineering assessment not found")

    config = db.query(SimulationConfiguration).filter(SimulationConfiguration.id == assessment.simulation_configuration_id).first()
    model_rev = db.query(ModelRevision).filter(ModelRevision.id == config.model_revision_id).first() if config else None

    # STRICT PARENT EVIDENCE LINEAGE FILTERING (P0 Item 18)
    # Find previous evidence artifact belonging to the SAME SeatArchitecture lineage!
    prev_artifact = None
    if model_rev:
        prev_artifact = db.query(EvidenceArtifact).join(
            EngineeringAssessment, EvidenceArtifact.engineering_assessment_id == EngineeringAssessment.id
        ).join(
            SimulationConfiguration, EngineeringAssessment.simulation_configuration_id == SimulationConfiguration.id
        ).join(
            ModelRevision, SimulationConfiguration.model_revision_id == ModelRevision.id
        ).filter(
            ModelRevision.seat_architecture_id == model_rev.seat_architecture_id,
            EvidenceArtifact.id != assessment_id
        ).order_by(EvidenceArtifact.created_at.desc()).first()

    output_dir = os.path.join(settings.STORAGE_DIR, "artifacts", assessment.id)

    input_manifest = {
        "simulation_configuration_id": config.id if config else "N/A",
        "configuration_hash": config.configuration_hash if config else "N/A",
        "cad_revision_label": model_rev.revision_label if model_rev else "RevA",
        "cad_file_sha256": model_rev.cad_file_sha256 if model_rev else "N/A",
        "solver_name": config.solver_name if config else "LSDYNA",
        "solver_version": config.solver_version if config else "R13.1",
        "dummy_type": "FAA_HIII_50M",
        "pulse_direction": "FORWARD_16G"
    }

    output_manifest = {
        "engineering_assessment_id": assessment.id,
        "overall_readiness": assessment.overall_readiness,
        "requirement_compliance_summary": assessment.requirement_compliance_summary,
        "engineer_comments": assessment.engineer_comments,
        "approved_by": assessment.approved_by,
        "approval_role": assessment.approval_role,
        "approved_at": assessment.approved_at.isoformat()
    }

    assessment_dict = {
        "overall_readiness": assessment.overall_readiness,
        "configuration_hash": config.configuration_hash if config else "N/A",
        "execution_fingerprint": config.configuration_hash if config else "N/A",
        "requirement_compliance_summary": assessment.requirement_compliance_summary,
        "approved_by_name": "Lead Certification Engineer",
        "approval_role": assessment.approval_role,
        "engineer_comments": assessment.engineer_comments
    }

    in_uri, in_hash, out_uri, out_hash, pdf_uri = generate_evidence_package(
        assessment_dict, input_manifest, output_manifest, output_dir
    )

    artifact = EvidenceArtifact(
        engineering_assessment_id=assessment.id,
        parent_evidence_id=prev_artifact.id if prev_artifact else None,
        input_manifest_uri=in_uri,
        input_manifest_sha256=in_hash,
        output_manifest_uri=out_uri,
        output_manifest_sha256=out_hash,
        package_pdf_uri=pdf_uri,
        software_version="1.0.0"
    )
    db.add(artifact)
    db.commit()
    db.refresh(artifact)

    return artifact

@router.get("/evidence-artifacts/{artifact_id}")
def get_evidence_artifact(artifact_id: str, db: Session = Depends(get_db)):
    artifact = db.query(EvidenceArtifact).filter(EvidenceArtifact.id == artifact_id).first()
    if not artifact:
        raise HTTPException(status_code=404, detail="Evidence artifact not found")
    return artifact

@router.get("/evidence-artifacts/{artifact_id}/download-pdf")
def download_pdf(artifact_id: str, db: Session = Depends(get_db)):
    artifact = db.query(EvidenceArtifact).filter(EvidenceArtifact.id == artifact_id).first()
    if not artifact or not os.path.exists(artifact.package_pdf_uri):
        raise HTTPException(status_code=404, detail="PDF document not found")
    return FileResponse(artifact.package_pdf_uri, media_type="application/pdf", filename=f"evidence_package_{artifact_id[:8]}.pdf")

@router.get("/golden-dataset/regression-check")
def check_golden_dataset_regression():
    """Runs scientific regression check on Contract 5 golden dataset."""
    result = run_golden_dataset_regression()
    return result
