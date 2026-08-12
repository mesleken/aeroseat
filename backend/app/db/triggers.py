from sqlalchemy import event
from sqlalchemy.orm import Session
from app.db.models import (
    ModelRevision, MaterialDataset, DummyConfiguration,
    PulseDefinition, RegulatoryStandard, Requirement, EvidenceArtifact
)

class ImmutableRecordError(Exception):
    """Raised when an attempt is made to UPDATE or DELETE an immutable record."""
    pass

IMMUTABLE_MODELS = [
    ModelRevision,
    MaterialDataset,
    DummyConfiguration,
    PulseDefinition,
    RegulatoryStandard,
    Requirement,
    EvidenceArtifact
]

def prevent_update(mapper, connection, target):
    raise ImmutableRecordError(f"Contract 4 Violation: Record of type '{target.__class__.__name__}' is immutable and cannot be UPDATED.")

def prevent_delete(mapper, connection, target):
    raise ImmutableRecordError(f"Contract 4 Violation: Record of type '{target.__class__.__name__}' is immutable and cannot be DELETED.")

def register_immutability_triggers(engine=None):
    """Registers ORM event listeners for immutability enforcement."""
    for model in IMMUTABLE_MODELS:
        event.listen(model, 'before_update', prevent_update)
        event.listen(model, 'before_delete', prevent_delete)

setup_immutability_triggers = register_immutability_triggers

def get_postgres_trigger_ddl() -> list[str]:
    """Generates raw PostgreSQL DDL triggers for database-engine-level immutability enforcement."""
    tables = [
        "model_revision", "material_dataset", "dummy_configuration",
        "pulse_definition", "regulatory_standard", "requirement", "evidence_artifact"
    ]
    
    ddl_statements = [
        """
        CREATE OR REPLACE FUNCTION block_immutable_mutation()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'Contract 4 Immutability Violation: Mutation (UPDATE or DELETE) is prohibited on immutable certification table %', TG_TABLE_NAME;
        END;
        $$ LANGUAGE plpgsql;
        """
    ]
    
    for table in tables:
        ddl_statements.append(f"""
        CREATE TRIGGER trg_block_update_{table}
        BEFORE UPDATE OR DELETE ON {table}
        FOR EACH ROW EXECUTE FUNCTION block_immutable_mutation();
        """)
        
    return ddl_statements
