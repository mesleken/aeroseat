from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Any
from datetime import datetime, date

# Project
class ProjectCreate(BaseModel):
    name: str
    customer_id: Optional[str] = "cust-default-001"

class ProjectResponse(BaseModel):
    id: str
    name: str
    customer_id: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# Model Revision
class ModelRevisionCreate(BaseModel):
    seat_architecture_id: str
    revision_label: str
    cad_file_uri: str
    uploaded_by: Optional[str] = "usr-default-admin-001"
    part_manifest: Optional[dict[str, Any]] = None

class ModelRevisionResponse(BaseModel):
    id: str
    seat_architecture_id: str
    revision_label: str
    cad_file_uri: str
    cad_file_sha256: str
    part_manifest: dict[str, Any]
    uploaded_by: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# Material
class MaterialCreate(BaseModel):
    name: str
    revision_label: str
    mechanical_properties: dict[str, Any]

class SolverMaterialRepCreate(BaseModel):
    solver_name: str = "LSDYNA"
    solver_mat_card: str

# Dummy & Pulse
class DummyConfigCreate(BaseModel):
    dummy_type: str = "FAA_HIII_50M"
    fe_model_uri: str
    positioning_spec: dict[str, Any]

class PulseDefCreate(BaseModel):
    name: str
    direction: str = "FORWARD_16G"
    curve_data: list[dict[str, Any]]
    tolerance_band: dict[str, Any]

# Simulation Configuration
class SimulationConfigCreate(BaseModel):
    model_revision_id: str
    mesh_definition_id: Optional[str] = None
    material_dataset_id: Optional[str] = None
    solver_material_representation_id: Optional[str] = None
    contact_definition_id: Optional[str] = None
    boundary_condition_set_id: Optional[str] = None
    dummy_configuration_id: Optional[str] = None
    pulse_definition_id: Optional[str] = None
    solver_name: str = "PHYSICS_LUMPED_MASS"
    solver_version: str = "1.0.0"
    dummy_type: str = "FAA_HIII_50M"
    pulse_type: str = "FORWARD_16G"
    custom_pulse_data: Optional[dict[str, Any]] = None
    yaw_deg: float = 0.0
    pitch_deg: float = 0.0
    roll_deg: float = 0.0
    dummy_offset_x: float = 0.0
    dummy_offset_y: float = 0.0
    dummy_offset_z: float = 0.0
    dummy_recline_deg: float = 0.0
    dummy_yaw_deg: float = 0.0
    seat_pitch_warp_deg: float = 0.0
    seat_roll_warp_deg: float = 0.0
    seat_yaw_mount_deg: float = 0.0
    created_by: Optional[str] = "usr-default-admin-001"

# Physical Test
class PhysicalTestCreate(BaseModel):
    seat_architecture_id: str
    test_facility: str = "Accredited Dynamic Sled Facility"
    test_date: Optional[date] = None
    raw_data_uri: str
    tema_video_uri: Optional[str] = None

# Correlation & Credibility Review
class CredibilityReviewCreate(BaseModel):
    correlation_run_id: str
    signal_correlation_status: str = "ACCEPTABLE"
    model_verification_status: str = "VERIFIED"
    test_quality_status: str = "HIGH"
    parameter_confidence_status: str = "HIGH"
    overall_assessment: str
    reviewed_by: Optional[str] = "usr-default-admin-001"

# Engineering Assessment
class EngineeringAssessmentCreate(BaseModel):
    simulation_configuration_id: str
    model_credibility_id: Optional[str] = None
    overall_readiness: str # READY, CONDITIONALLY_READY, NOT_READY
    engineer_comments: str
    approved_by: Optional[str] = "usr-default-admin-001"
    approval_role: str = "CHIEF_CERTIFICATION_ENGINEER"
