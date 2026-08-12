import hashlib
import json
from sqlalchemy.orm import Session
from app.db.models import (
    Base, AppUser, Customer, RegulatoryStandard, Requirement,
    MaterialDataset, SolverMaterialRepresentation, DummyConfiguration,
    PulseDefinition, MeshDefinition, ContactDefinition, BoundaryConditionSet,
    ProcessingDefinition
)
from app.db.database import engine, SessionLocal

def compute_sha256(data: str) -> str:
    return hashlib.sha256(data.encode('utf-8')).hexdigest()

def init_db(db: Session):
    Base.metadata.create_all(bind=engine)

    # 1. Seed Default User & Customer
    admin_user = db.query(AppUser).filter(AppUser.email == "engineer@aeroseat.io").first()
    if not admin_user:
        admin_user = AppUser(
            id="usr-default-admin-001",
            name="Lead Certification Engineer",
            email="engineer@aeroseat.io",
            role="CERTIFICATION_ENGINEER"
        )
        db.add(admin_user)
    
    customer = db.query(Customer).filter(Customer.name == "AeroSpace Dynamics Corp").first()
    if not customer:
        customer = Customer(
            id="cust-default-001",
            name="AeroSpace Dynamics Corp"
        )
        db.add(customer)
    
    db.commit()

    # 2. Seed Regulatory Standards & Requirements
    as8049 = db.query(RegulatoryStandard).filter(RegulatoryStandard.code == "AS8049").first()
    if not as8049:
        as8049 = RegulatoryStandard(
            id="std-as8049e-001",
            code="AS8049",
            revision="E",
            document_uri="s3://aeroseat-docs/standards/SAE_AS8049E.pdf"
        )
        db.add(as8049)
        db.commit()

        # Requirements
        reqs = [
            Requirement(
                id="req-hic15-001",
                standard_id=as8049.id,
                code="HIC15_LIMIT",
                metric="HIC15",
                limit_operator="<=",
                limit_value=1000.0,
                limit_unit="dimensionless"
            ),
            Requirement(
                id="req-nij-001",
                standard_id=as8049.id,
                code="NIJ_MAX_LIMIT",
                metric="NIJ",
                limit_operator="<=",
                limit_value=1.0,
                limit_unit="dimensionless"
            ),
            Requirement(
                id="req-femur-001",
                standard_id=as8049.id,
                code="FEMUR_LOAD_LIMIT",
                metric="FEMUR_LOAD",
                limit_operator="<=",
                limit_value=10.0,
                limit_unit="kN"
            ),
            Requirement(
                id="req-lumbar-001",
                standard_id=as8049.id,
                code="LUMBAR_LOAD_LIMIT",
                metric="LUMBAR_LOAD",
                limit_operator="<=",
                limit_value=6.67,
                limit_unit="kN"
            ),
            Requirement(
                id="req-excursion-head-001",
                standard_id=as8049.id,
                code="HEAD_EXCURSION_LIMIT",
                metric="HEAD_EXCURSION",
                limit_operator="<=",
                limit_value=889.0, # 35 inches in mm
                limit_unit="mm"
            ),
        ]
        for req in reqs:
            db.add(req)
        db.commit()

    # 3. Seed Reference Material (Al-2024-T3)
    mat = db.query(MaterialDataset).filter(MaterialDataset.name == "Al-2024-T3").first()
    if not mat:
        props = {
            "density_g_cm3": 2.78,
            "elastic_modulus_gpa": 73.1,
            "yield_strength_mpa": 345.0,
            "ultimate_tensile_strength_mpa": 483.0,
            "poisson_ratio": 0.33
        }
        mat_str = json.dumps(props, sort_keys=True)
        mat = MaterialDataset(
            id="mat-al2024-t3-001",
            name="Al-2024-T3",
            revision_label="REV-A",
            mechanical_properties=props,
            sha256=compute_sha256(mat_str)
        )
        db.add(mat)
        db.commit()

        mat_card = """*MAT_PIECEWISE_LINEAR_PLASTICITY
$#    mid        ro         e        pr        sigy        etan
 10001001   2.78e-9    73.100    0.3300   0.3450000        0.00"""
        solver_rep = SolverMaterialRepresentation(
            id="matrep-lsdyna-al2024-001",
            material_dataset_id=mat.id,
            solver_name="LSDYNA",
            solver_mat_card=mat_card,
            sha256=compute_sha256(mat_card)
        )
        db.add(solver_rep)
        db.commit()

    # 4. Seed Dummy Configuration (FAA HIII-50M)
    dummy = db.query(DummyConfiguration).filter(DummyConfiguration.dummy_type == "FAA_HIII_50M").first()
    if not dummy:
        pos_spec = {
            "h_point_offset_mm": [0.0, 0.0, 0.0],
            "backrest_angle_deg": 15.0,
            "seat_pan_angle_deg": 5.0,
            "foot_position": "ON_FLOOR"
        }
        dummy = DummyConfiguration(
            id="dummy-faa-hiii-50m-001",
            dummy_type="FAA_HIII_50M",
            fe_model_uri="s3://aeroseat-models/dummies/faa_hiii_50m_v3.k",
            fe_model_sha256=compute_sha256("faa_hiii_50m_v3"),
            positioning_spec=pos_spec
        )
        db.add(dummy)
        db.commit()

    # 5. Seed Pulse Definition (16g Forward)
    pulse = db.query(PulseDefinition).filter(PulseDefinition.name == "16g Forward Sled Pulse").first()
    if not pulse:
        # Standard 16g pulse curve (time in s, acceleration in g)
        curve = [
            {"time_s": 0.00, "accel_g": 0.0},
            {"time_s": 0.03, "accel_g": 16.0},
            {"time_s": 0.09, "accel_g": 16.0},
            {"time_s": 0.18, "accel_g": 0.0},
        ]
        tol_band = {
            "min_peak_g": 16.0,
            "max_rise_time_s": 0.09,
            "min_velocity_change_m_s": 13.4 # 44 ft/s
        }
        pulse_str = json.dumps(curve, sort_keys=True)
        pulse = PulseDefinition(
            id="pulse-16g-fwd-001",
            name="16g Forward Sled Pulse",
            direction="FORWARD_16G",
            curve_data=curve,
            tolerance_band=tol_band,
            sha256=compute_sha256(pulse_str)
        )
        db.add(pulse)
        db.commit()

    # 6. Seed Processing Definition (Contract 1)
    proc_def = db.query(ProcessingDefinition).filter(ProcessingDefinition.revision_label == "PD-Rev1").first()
    if not proc_def:
        steps = [
            {"step": "integrity_check", "params": {"max_gap_ms": 1.0}},
            {"step": "unit_normalization", "params": {"target_units": "SI"}},
            {"step": "channel_validation", "params": {"expected_range": {"min": -500, "max": 500}}},
            {"step": "filter", "params": {"standard": "SAE_J211"}},
            {"step": "time_zero", "params": {"method": "threshold_crossing", "threshold_g": 0.5}},
            {"step": "window", "params": {"start_offset_ms": -10.0, "end_offset_ms": 180.0}},
            {"step": "resample", "params": {"target_rate_hz": 10000, "interpolation": "linear"}}
        ]
        proc_str = json.dumps(steps, sort_keys=True)
        proc_def = ProcessingDefinition(
            id="procdef-rev1-001",
            revision_label="PD-Rev1",
            steps=steps,
            sha256=compute_sha256(proc_str)
        )
        db.add(proc_def)
        db.commit()

    # 7. Seed default Mesh, Contact, BoundaryCondition
    mesh = db.query(MeshDefinition).first()
    if not mesh:
        mesh = MeshDefinition(
            id="mesh-default-001",
            name="Baseline 5mm Shell Mesh",
            element_count=48500,
            sha256=compute_sha256("mesh-5mm")
        )
        db.add(mesh)
    
    contact = db.query(ContactDefinition).first()
    if not contact:
        contact = ContactDefinition(
            id="contact-default-001",
            name="AUTOMATIC_SINGLE_SURFACE_STATIC_0.3",
            contact_type="AUTOMATIC_SINGLE_SURFACE",
            sha256=compute_sha256("contact-0.3")
        )
        db.add(contact)
        
    bc = db.query(BoundaryConditionSet).first()
    if not bc:
        bc_spec = {"floor_rails": "FIXED_6DOF", "seat_pan_mounting": "PINNED"}
        bc = BoundaryConditionSet(
            id="bc-default-001",
            name="Standard Floor Rail Fixity",
            spec=bc_spec,
            sha256=compute_sha256(json.dumps(bc_spec, sort_keys=True))
        )
        db.add(bc)
    
    db.commit()

if __name__ == "__main__":
    db = SessionLocal()
    init_db(db)
    print("Database initialized & seeded successfully!")
