import uuid
import pytest
from app.domain.contracts.evidence_immutability import (
    compute_artifact_hash, compute_configuration_hash, compute_execution_fingerprint
)
from app.db.models import ModelRevision, SeatArchitecture
from app.db.database import SessionLocal
from app.db.triggers import ImmutableRecordError

def test_hash_computations():
    art_hash = compute_artifact_hash("cad-file-binary-data")
    assert len(art_hash) == 64

    cfg_hash = compute_configuration_hash("rev0", "m0", "mat0", "rep0", "con0", "bc0", "dum0", "pul0")
    assert len(cfg_hash) == 64

    exec_fp = compute_execution_fingerprint(cfg_hash, "LSDYNA", "R13.1", "B1", "proc0")
    assert len(exec_fp) == 64

def test_immutability_trigger_error():
    db = SessionLocal()
    try:
        proj = db.query(SeatArchitecture).first()
        if not proj:
            proj = SeatArchitecture(name="Test Architecture", customer_id="cust-default-001")
            db.add(proj)
            db.commit()

        rev_id = f"test-rev-immut-{uuid.uuid4()}"
        rev = ModelRevision(
            id=rev_id,
            seat_architecture_id=proj.id,
            revision_label="RevA",
            cad_file_uri="/cad.step",
            cad_file_sha256="abc123sha256",
            part_manifest={},
            uploaded_by="usr-default-admin-001"
        )
        db.add(rev)
        db.commit()

        # Contract 4 Immutability Guarantee: UPDATE is prohibited
        rev.revision_label = "RevB-MUTATED"
        with pytest.raises(ImmutableRecordError):
            db.commit()

        db.rollback()

        # Contract 4 Immutability Guarantee: DELETE is prohibited
        rev_to_del = db.query(ModelRevision).filter(ModelRevision.id == rev_id).first()
        db.delete(rev_to_del)
        with pytest.raises(ImmutableRecordError):
            db.commit()

        db.rollback()
    finally:
        db.close()
