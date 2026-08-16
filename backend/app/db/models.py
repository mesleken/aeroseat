import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Float, Integer, DateTime, Date, ForeignKey, JSON, CheckConstraint, Index, Boolean
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

def generate_uuid():
    return str(uuid.uuid4())

class AppUser(Base):
    __tablename__ = "app_user"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    role = Column(String(100), nullable=False, default="ENGINEER")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class Customer(Base):
    __tablename__ = "customer"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class SeatArchitecture(Base):
    __tablename__ = "seat_architecture"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    customer_id = Column(String(36), ForeignKey("customer.id"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class ModelRevision(Base):
    __tablename__ = "model_revision"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    seat_architecture_id = Column(String(36), ForeignKey("seat_architecture.id"), nullable=False)
    revision_label = Column(String(100), nullable=False)
    cad_file_uri = Column(String(500), nullable=False)
    cad_file_sha256 = Column(String(64), nullable=False)
    part_manifest = Column(JSON, nullable=False)
    uploaded_by = Column(String(36), ForeignKey("app_user.id"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class MaterialDataset(Base):
    __tablename__ = "material_dataset"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    revision_label = Column(String(100), nullable=False)
    mechanical_properties = Column(JSON, nullable=False)
    sha256 = Column(String(64), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class SolverMaterialRepresentation(Base):
    __tablename__ = "solver_material_representation"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    material_dataset_id = Column(String(36), ForeignKey("material_dataset.id"), nullable=False)
    solver_name = Column(String(100), nullable=False)
    solver_mat_card = Column(Text, nullable=False)
    sha256 = Column(String(64), nullable=False)

class DummyConfiguration(Base):
    __tablename__ = "dummy_configuration"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    dummy_type = Column(String(100), nullable=False) # e.g. FAA_HIII_50M
    fe_model_uri = Column(String(500), nullable=False)
    fe_model_sha256 = Column(String(64), nullable=False)
    positioning_spec = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class PulseDefinition(Base):
    __tablename__ = "pulse_definition"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    direction = Column(String(50), nullable=False) # FORWARD_16G
    curve_data = Column(JSON, nullable=False)
    tolerance_band = Column(JSON, nullable=False)
    sha256 = Column(String(64), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class MeshDefinition(Base):
    __tablename__ = "mesh_definition"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    element_count = Column(Integer, nullable=False, default=0)
    sha256 = Column(String(64), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class ContactDefinition(Base):
    __tablename__ = "contact_definition"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    contact_type = Column(String(100), nullable=False)
    sha256 = Column(String(64), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class BoundaryConditionSet(Base):
    __tablename__ = "boundary_condition_set"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    spec = Column(JSON, nullable=False)
    sha256 = Column(String(64), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class ProcessingDefinition(Base):
    __tablename__ = "processing_definition"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    revision_label = Column(String(100), nullable=False)
    steps = Column(JSON, nullable=False)
    sha256 = Column(String(64), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class RegulatoryStandard(Base):
    __tablename__ = "regulatory_standard"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    code = Column(String(100), nullable=False) # e.g. CS-25.562, AS8049, ARP5765B
    revision = Column(String(50), nullable=False) # e.g. E
    effective_date = Column(Date, nullable=True)
    document_uri = Column(String(500), nullable=True)

class Requirement(Base):
    __tablename__ = "requirement"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    standard_id = Column(String(36), ForeignKey("regulatory_standard.id"), nullable=False)
    code = Column(String(100), nullable=False)
    metric = Column(String(100), nullable=False) # HIC15, NIJ, FEMUR_LOAD, LUMBAR_LOAD, EXCURSION
    limit_operator = Column(String(10), nullable=False) # <=
    limit_value = Column(Float, nullable=False)
    limit_unit = Column(String(50), nullable=False)

class SimulationConfiguration(Base):
    __tablename__ = "simulation_configuration"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    model_revision_id = Column(String(36), ForeignKey("model_revision.id"), nullable=False)
    mesh_definition_id = Column(String(36), ForeignKey("mesh_definition.id"), nullable=False)
    material_dataset_id = Column(String(36), ForeignKey("material_dataset.id"), nullable=False)
    solver_material_representation_id = Column(String(36), ForeignKey("solver_material_representation.id"), nullable=False)
    contact_definition_id = Column(String(36), ForeignKey("contact_definition.id"), nullable=False)
    boundary_condition_set_id = Column(String(36), ForeignKey("boundary_condition_set.id"), nullable=False)
    dummy_configuration_id = Column(String(36), ForeignKey("dummy_configuration.id"), nullable=False)
    pulse_definition_id = Column(String(36), ForeignKey("pulse_definition.id"), nullable=False)
    solver_name = Column(String(100), nullable=False, default="LSDYNA")
    solver_version = Column(String(50), nullable=False, default="R13.1")
    dummy_type = Column(String(100), nullable=False, default="FAA_HIII_50M")
    pulse_type = Column(String(50), nullable=False, default="FORWARD_16G")
    custom_pulse_data = Column(JSON, nullable=True)
    yaw_deg = Column(Float, nullable=False, default=0.0)
    pitch_deg = Column(Float, nullable=False, default=0.0)
    roll_deg = Column(Float, nullable=False, default=0.0)
    dummy_offset_x = Column(Float, nullable=False, default=0.0)
    dummy_offset_y = Column(Float, nullable=False, default=0.0)
    dummy_offset_z = Column(Float, nullable=False, default=0.0)
    dummy_recline_deg = Column(Float, nullable=False, default=0.0)
    dummy_yaw_deg = Column(Float, nullable=False, default=0.0)
    seat_pitch_warp_deg = Column(Float, nullable=False, default=0.0)
    seat_roll_warp_deg = Column(Float, nullable=False, default=0.0)
    seat_yaw_mount_deg = Column(Float, nullable=False, default=0.0)
    configuration_hash = Column(String(64), nullable=False)
    created_by = Column(String(36), ForeignKey("app_user.id"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class ModelQAResult(Base):
    __tablename__ = "model_qa_result"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    simulation_configuration_id = Column(String(36), ForeignKey("simulation_configuration.id"), nullable=False)
    checks = Column(JSON, nullable=False)
    overall_status = Column(String(20), nullable=False) # PASS, WARNING, BLOCKED
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class SolverJob(Base):
    __tablename__ = "solver_job"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    simulation_configuration_id = Column(String(36), ForeignKey("simulation_configuration.id"), nullable=False)
    execution_fingerprint = Column(String(64), nullable=False, index=True)
    status = Column(String(50), nullable=False) # QUEUED, PREPARING, SUBMITTED, RUNNING, POST_PROCESSING, VALIDATING, COMPLETED, etc.
    hpc_job_id = Column(String(100), nullable=True)
    last_polled_at = Column(DateTime, nullable=True)
    last_heartbeat_at = Column(DateTime, nullable=True)
    attempt_count = Column(Integer, nullable=False, default=0)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

class SimulationResult(Base):
    __tablename__ = "simulation_result"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    solver_job_id = Column(String(36), ForeignKey("solver_job.id"), nullable=False)
    d3plot_uri = Column(String(500), nullable=False)
    binout_uri = Column(String(500), nullable=False)
    output_sha256 = Column(String(64), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class InjuryMetrics(Base):
    __tablename__ = "injury_metrics"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    simulation_result_id = Column(String(36), ForeignKey("simulation_result.id"), nullable=False)
    hic15 = Column(Float, nullable=True)
    nij_max = Column(Float, nullable=True)
    nij_type = Column(String(50), nullable=True)
    femur_load_left = Column(Float, nullable=True)
    femur_load_right = Column(Float, nullable=True)
    lumbar_load = Column(Float, nullable=True)
    belt_shoulder_load_kn = Column(Float, nullable=True)
    belt_lap_load_kn = Column(Float, nullable=True)
    head_excursion_mm = Column(Float, nullable=True)
    knee_excursion_mm = Column(Float, nullable=True)
    seat_structural_status = Column(String(50), nullable=True)
    raw_timeseries = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class TestConfiguration(Base):
    __tablename__ = "test_configuration"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    seat_architecture_id = Column(String(36), ForeignKey("seat_architecture.id"), nullable=False)
    dummy_type = Column(String(100), nullable=False)
    pulse_target = Column(String(100), nullable=False)
    restraint_configuration = Column(JSON, nullable=False)
    instrumentation_configuration = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class PhysicalTest(Base):
    __tablename__ = "physical_test"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    test_configuration_id = Column(String(36), ForeignKey("test_configuration.id"), nullable=False)
    test_facility = Column(String(255), nullable=True) # e.g. Dynamic Sled Facility
    test_date = Column(Date, nullable=True)
    raw_data_uri = Column(String(500), nullable=False)
    raw_data_sha256 = Column(String(64), nullable=False)
    tema_video_uri = Column(String(500), nullable=True)
    metadata_json = Column(JSON, nullable=True)

class CorrelationRun(Base):
    __tablename__ = "correlation_run"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    simulation_result_id = Column(String(36), ForeignKey("simulation_result.id"), nullable=False)
    physical_test_id = Column(String(36), ForeignKey("physical_test.id"), nullable=False)
    processing_definition_id = Column(String(36), ForeignKey("processing_definition.id"), nullable=False)
    method = Column(String(100), nullable=False, default="ARP5765B")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class CorrelationVector(Base):
    __tablename__ = "correlation_vector"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    correlation_run_id = Column(String(36), ForeignKey("correlation_run.id"), nullable=False)
    channel = Column(String(100), nullable=False)
    magnitude_error = Column(Float, nullable=True)
    phase_error_ms = Column(Float, nullable=True)
    shape_metric_sprague_geers = Column(Float, nullable=True)
    peak_error = Column(Float, nullable=True)
    rms_error = Column(Float, nullable=True)
    engineering_note = Column(Text, nullable=True)

class CredibilityAssessment(Base):
    __tablename__ = "credibility_assessment"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    correlation_run_id = Column(String(36), ForeignKey("correlation_run.id"), nullable=False)
    signal_correlation_status = Column(String(50), nullable=True)
    model_verification_status = Column(String(50), nullable=True)
    test_quality_status = Column(String(50), nullable=True)
    parameter_confidence_status = Column(String(50), nullable=True)
    overall_assessment = Column(Text, nullable=False)
    reviewed_by = Column(String(36), ForeignKey("app_user.id"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class RequirementStatus(Base):
    __tablename__ = "requirement_status"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    requirement_id = Column(String(36), ForeignKey("requirement.id"), nullable=False)
    injury_metrics_id = Column(String(36), ForeignKey("injury_metrics.id"), nullable=False)
    measured_value = Column(Float, nullable=False)
    status = Column(String(10), nullable=False) # PASS, FAIL
    margin_percent = Column(Float, nullable=True)

class EngineeringAssessment(Base):
    __tablename__ = "engineering_assessment"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    simulation_configuration_id = Column(String(36), ForeignKey("simulation_configuration.id"), nullable=False)
    requirement_compliance_summary = Column(JSON, nullable=False)
    model_credibility_id = Column(String(36), ForeignKey("credibility_assessment.id"), nullable=True)
    overall_readiness = Column(String(50), nullable=False) # READY, CONDITIONALLY_READY, NOT_READY
    engineer_comments = Column(Text, nullable=True)
    approved_by = Column(String(36), ForeignKey("app_user.id"), nullable=False)
    approval_role = Column(String(100), nullable=False)
    approved_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class EvidenceArtifact(Base):
    __tablename__ = "evidence_artifact"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    engineering_assessment_id = Column(String(36), ForeignKey("engineering_assessment.id"), nullable=False)
    parent_evidence_id = Column(String(36), ForeignKey("evidence_artifact.id"), nullable=True)
    input_manifest_uri = Column(String(500), nullable=False)
    input_manifest_sha256 = Column(String(64), nullable=False)
    output_manifest_uri = Column(String(500), nullable=False)
    output_manifest_sha256 = Column(String(64), nullable=False)
    package_pdf_uri = Column(String(500), nullable=False)
    software_version = Column(String(50), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class AuditEvent(Base):
    __tablename__ = "audit_event"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    entity_type = Column(String(100), nullable=False)
    entity_id = Column(String(36), nullable=False)
    action = Column(String(50), nullable=False)
    actor_id = Column(String(36), ForeignKey("app_user.id"), nullable=True)
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
