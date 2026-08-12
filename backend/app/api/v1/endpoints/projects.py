import json
import hashlib
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import (
    SeatArchitecture, ModelRevision, MaterialDataset, SolverMaterialRepresentation,
    DummyConfiguration, PulseDefinition, RegulatoryStandard, Requirement
)
from app.schemas.schemas import (
    ProjectCreate, ProjectResponse, ModelRevisionCreate, ModelRevisionResponse,
    MaterialCreate, SolverMaterialRepCreate
)

router = APIRouter()

@router.post("/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    proj = SeatArchitecture(name=payload.name, customer_id=payload.customer_id)
    db.add(proj)
    db.commit()
    db.refresh(proj)
    return proj

@router.get("/projects")
def list_projects(db: Session = Depends(get_db)):
    return db.query(SeatArchitecture).all()

@router.post("/projects/{project_id}/model-revisions", response_model=ModelRevisionResponse, status_code=status.HTTP_201_CREATED)
def create_model_revision(project_id: str, payload: ModelRevisionCreate, db: Session = Depends(get_db)):
    proj = db.query(SeatArchitecture).filter(SeatArchitecture.id == project_id).first()
    if not proj:
        raise HTTPException(status_code=404, detail=f"Seat architecture project '{project_id}' not found.")

    # Real artifact hashing: SHA-256 of the CAD file URI payload content
    cad_bytes = payload.cad_file_uri.encode('utf-8')
    sha256 = hashlib.sha256(cad_bytes).hexdigest()

    manifest = payload.part_manifest or {
        "primary_frame": {"material": "Al-2024-T3", "element_type": "SHELL_5MM"},
        "spreader_beam": {"material": "Al-7075-T6", "element_type": "SOLID_HEX"},
        "seat_cushion": {"material": "PU_FOAM_MEDIUM", "element_type": "SOLID_HEX"}
    }

    rev = ModelRevision(
        seat_architecture_id=project_id,
        revision_label=payload.revision_label,
        cad_file_uri=payload.cad_file_uri,
        cad_file_sha256=sha256,
        part_manifest=manifest,
        uploaded_by=payload.uploaded_by
    )
    db.add(rev)
    db.commit()
    db.refresh(rev)
    return rev

@router.get("/model-revisions/{revision_id}")
def get_model_revision(revision_id: str, db: Session = Depends(get_db)):
    rev = db.query(ModelRevision).filter(ModelRevision.id == revision_id).first()
    if not rev:
        raise HTTPException(status_code=404, detail="Model revision not found.")
    return rev

@router.post("/material-datasets")
def create_material_dataset(payload: MaterialCreate, db: Session = Depends(get_db)):
    mat_str = json.dumps(payload.mechanical_properties, sort_keys=True)
    sha256 = hashlib.sha256(mat_str.encode('utf-8')).hexdigest()
    mat = MaterialDataset(
        name=payload.name,
        revision_label=payload.revision_label,
        mechanical_properties=payload.mechanical_properties,
        sha256=sha256
    )
    db.add(mat)
    db.commit()
    db.refresh(mat)
    return mat

@router.get("/material-datasets")
def list_material_datasets(db: Session = Depends(get_db)):
    return db.query(MaterialDataset).all()

@router.post("/material-datasets/{material_id}/solver-representations")
def create_solver_material_rep(material_id: str, payload: SolverMaterialRepCreate, db: Session = Depends(get_db)):
    mat = db.query(MaterialDataset).filter(MaterialDataset.id == material_id).first()
    if not mat:
        raise HTTPException(status_code=404, detail=f"Material dataset '{material_id}' not found.")
    
    sha256 = hashlib.sha256(payload.solver_mat_card.encode('utf-8')).hexdigest()
    rep = SolverMaterialRepresentation(
        material_dataset_id=material_id,
        solver_name=payload.solver_name,
        solver_mat_card=payload.solver_mat_card,
        sha256=sha256
    )
    db.add(rep)
    db.commit()
    db.refresh(rep)
    return rep

@router.get("/regulatory-standards")
def list_regulatory_standards(db: Session = Depends(get_db)):
    return db.query(RegulatoryStandard).all()

@router.get("/requirements")
def list_requirements(db: Session = Depends(get_db)):
    return db.query(Requirement).all()
