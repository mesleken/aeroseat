import os
import json
import hashlib
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.core.config import settings
from app.db.models import (
    SimulationConfiguration, ModelQAResult, SolverJob, SimulationResult,
    InjuryMetrics, Requirement, RequirementStatus, ModelRevision, MaterialDataset,
    SolverMaterialRepresentation, DummyConfiguration, PulseDefinition, MeshDefinition,
    ContactDefinition, BoundaryConditionSet, ProcessingDefinition, RegulatoryStandard
)
from app.schemas.schemas import SimulationConfigCreate
from app.domain.model_qa import run_model_qa_gate
from app.domain.contracts.evidence_immutability import (
    compute_configuration_hash, compute_execution_fingerprint, get_completed_job_by_fingerprint
)
from app.adapters.solver.factory import get_solver_adapter
from app.adapters.solver.base import ComputeConfiguration
from app.domain.injury_metrics import compute_all_injury_metrics

router = APIRouter()

from pydantic import BaseModel
class CalibrationRequest(BaseModel):
    pulse_type: str = "FORWARD_16G"

class CustomSimRequest(BaseModel):
    pulse_type: str = "FORWARD_16G"
    dummy_type: str = "FAA_HIII_50M"
    belt_k_lap: float = 48000.0
    belt_k_shoulder: float = 42000.0
    neck_k_z: float = 22000.0
    rail_mount_k: float = 850000.0
    cushion_k: float = 36000.0

@router.post("/auto-calibrate")
def run_auto_calibration(payload: CalibrationRequest):
    """Runs the SciPy Nelder-Mead optimization on the Phase 7 Simulation Engine."""
    from app.domain.physics.calibration_engine import ModelCalibrationEngine
    from app.domain.physics.lumped_mass_model import LumpedMassCrashModel
    import numpy as np

    # Synthetic golden dataset representing NHTSA targets
    model = LumpedMassCrashModel(pulse_type=payload.pulse_type)
    baseline = model.run()
    
    golden = {}
    if "head_acceleration" in baseline:
        sim_head = np.array(baseline["head_acceleration"])
        peak_idx = np.argmax(np.abs(sim_head))
        golden["head_acceleration"] = (sim_head * (65.0 / max(1.0, np.abs(sim_head[peak_idx])))).tolist()
        
    if "belt_shoulder_load_kn" in baseline:
        sim_belt = np.array(baseline["belt_shoulder_load_kn"])
        peak_idx = np.argmax(np.abs(sim_belt))
        golden["belt_shoulder_load_kn"] = (sim_belt * (7.5 / max(0.1, np.abs(sim_belt[peak_idx])))).tolist()
        
    if "neck_axial_force" in baseline:
        sim_neck = np.array(baseline["neck_axial_force"])
        peak_idx = np.argmax(np.abs(sim_neck))
        golden["neck_axial_force"] = (sim_neck * (4100.0 / max(1.0, np.abs(sim_neck[peak_idx])))).tolist()

    engine = ModelCalibrationEngine(calibration_dataset=golden)
    engine.pulse_type = payload.pulse_type
    result = engine.run_automated_calibration()
    
    return {
        "status": "success",
        "calibration_result": result
    }

@router.post("/simulate-custom")
def run_custom_simulation(payload: CustomSimRequest):
    """Runs a 16G/14G simulation using manual custom stiffness parameters."""
    from app.domain.physics.lumped_mass_model import LumpedMassCrashModel
    
    model = LumpedMassCrashModel(dummy_type=payload.dummy_type, pulse_type=payload.pulse_type)
    model.stiff.belt_k_lap = payload.belt_k_lap
    model.stiff.belt_k_shoulder = payload.belt_k_shoulder
    model.stiff.neck_k_z = payload.neck_k_z
    model.stiff.rail_mount_k = payload.rail_mount_k
    model.stiff.cushion_k = payload.cushion_k
    
    results = model.run()
    
    # Prune full timeseries arrays to limit payload size if necessary, but frontend uses it for 3D
    return {
        "status": "success",
        "metrics": {
            "hic15": results.get("hic15"),
            "nij_max": results.get("nij_max"),
            "lumbar_load": results.get("lumbar_load"),
            "belt_shoulder_load_kn": results.get("belt_shoulder_load_kn")
        },
        "timeseries": results
    }
@router.post("/simulation-configurations", status_code=status.HTTP_201_CREATED)
def create_simulation_config(payload: SimulationConfigCreate, db: Session = Depends(get_db)):
    model_rev = db.query(ModelRevision).filter(ModelRevision.id == payload.model_revision_id).first()
    if not model_rev:
        raise HTTPException(status_code=422, detail=f"Invalid payload: ModelRevision '{payload.model_revision_id}' not found.")

    mesh = db.query(MeshDefinition).filter(MeshDefinition.id == payload.mesh_definition_id).first() if payload.mesh_definition_id else db.query(MeshDefinition).first()
    if not mesh:
        raise HTTPException(status_code=422, detail="Invalid payload: MeshDefinition not found or not specified.")

    mat = db.query(MaterialDataset).filter(MaterialDataset.id == payload.material_dataset_id).first() if payload.material_dataset_id else db.query(MaterialDataset).first()
    if not mat:
        raise HTTPException(status_code=422, detail="Invalid payload: MaterialDataset not found or not specified.")

    solver_rep = db.query(SolverMaterialRepresentation).filter(SolverMaterialRepresentation.id == payload.solver_material_representation_id).first() if payload.solver_material_representation_id else db.query(SolverMaterialRepresentation).first()
    if not solver_rep:
        raise HTTPException(status_code=422, detail="Invalid payload: SolverMaterialRepresentation not found or not specified.")

    contact = db.query(ContactDefinition).filter(ContactDefinition.id == payload.contact_definition_id).first() if payload.contact_definition_id else db.query(ContactDefinition).first()
    if not contact:
        raise HTTPException(status_code=422, detail="Invalid payload: ContactDefinition not found or not specified.")

    bc = db.query(BoundaryConditionSet).filter(BoundaryConditionSet.id == payload.boundary_condition_set_id).first() if payload.boundary_condition_set_id else db.query(BoundaryConditionSet).first()
    if not bc:
        raise HTTPException(status_code=422, detail="Invalid payload: BoundaryConditionSet not found or not specified.")

    dummy = db.query(DummyConfiguration).filter(DummyConfiguration.id == payload.dummy_configuration_id).first() if payload.dummy_configuration_id else db.query(DummyConfiguration).first()
    if not dummy:
        raise HTTPException(status_code=422, detail="Invalid payload: DummyConfiguration not found or not specified.")

    pulse = db.query(PulseDefinition).filter(PulseDefinition.id == payload.pulse_definition_id).first() if payload.pulse_definition_id else db.query(PulseDefinition).first()
    if not pulse:
        raise HTTPException(status_code=422, detail="Invalid payload: PulseDefinition not found or not specified.")

    config_hash = compute_configuration_hash(
        model_revision_sha256=model_rev.cad_file_sha256,
        mesh_sha256=mesh.sha256,
        material_sha256=mat.sha256,
        solver_mat_rep_sha256=solver_rep.sha256,
        contact_sha256=contact.sha256,
        boundary_condition_sha256=bc.sha256,
        dummy_sha256=dummy.fe_model_sha256,
        pulse_sha256=pulse.sha256,
        extra_spec=f"{payload.dummy_type}:{payload.pulse_type}:{payload.yaw_deg}:{payload.pitch_deg}:{payload.roll_deg}:{payload.dummy_offset_x}:{payload.dummy_offset_y}:{payload.dummy_offset_z}:{payload.dummy_recline_deg}:{payload.dummy_yaw_deg}:{payload.seat_pitch_warp_deg}:{payload.seat_roll_warp_deg}:{payload.seat_yaw_mount_deg}"
    )

    sim_config = SimulationConfiguration(
        model_revision_id=model_rev.id,
        mesh_definition_id=mesh.id,
        material_dataset_id=mat.id,
        solver_material_representation_id=solver_rep.id,
        contact_definition_id=contact.id,
        boundary_condition_set_id=bc.id,
        dummy_configuration_id=dummy.id,
        pulse_definition_id=pulse.id,
        solver_name=payload.solver_name,
        solver_version=payload.solver_version,
        dummy_type=payload.dummy_type,
        pulse_type=payload.pulse_type,
        custom_pulse_data=payload.custom_pulse_data,
        yaw_deg=payload.yaw_deg,
        pitch_deg=payload.pitch_deg,
        roll_deg=payload.roll_deg,
        dummy_offset_x=payload.dummy_offset_x,
        dummy_offset_y=payload.dummy_offset_y,
        dummy_offset_z=payload.dummy_offset_z,
        dummy_recline_deg=payload.dummy_recline_deg,
        dummy_yaw_deg=payload.dummy_yaw_deg,
        seat_pitch_warp_deg=payload.seat_pitch_warp_deg,
        seat_roll_warp_deg=payload.seat_roll_warp_deg,
        seat_yaw_mount_deg=payload.seat_yaw_mount_deg,
        configuration_hash=config_hash,
        created_by=payload.created_by
    )
    db.add(sim_config)
    db.commit()
    db.refresh(sim_config)
    return sim_config

@router.post("/simulation-configurations/{config_id}/qa")
def run_qa_gate(config_id: str, db: Session = Depends(get_db)):
    config = db.query(SimulationConfiguration).filter(SimulationConfiguration.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Simulation configuration not found")

    qa_res_data = run_model_qa_gate({
        "material_dataset_id": config.material_dataset_id,
        "dummy_type": config.dummy_type or "FAA_HIII_50M",
        "pulse_direction": config.pulse_type or "FORWARD_16G",
        "total_mass_kg": 54.5
    })

    qa_record = ModelQAResult(
        simulation_configuration_id=config.id,
        checks=qa_res_data["checks"],
        overall_status=qa_res_data["overall_status"]
    )
    db.add(qa_record)
    db.commit()
    db.refresh(qa_record)
    return qa_record

@router.post("/simulation-configurations/{config_id}/run")
def run_simulation(config_id: str, db: Session = Depends(get_db)):
    config = db.query(SimulationConfiguration).filter(SimulationConfiguration.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Simulation configuration not found")

    qa = db.query(ModelQAResult).filter(ModelQAResult.simulation_configuration_id == config_id).first()
    if not qa:
        qa_data = run_model_qa_gate({
            "material_dataset_id": config.material_dataset_id, 
            "dummy_type": config.dummy_type or "FAA_HIII_50M",
            "pulse_direction": config.pulse_type or "FORWARD_16G"
        })
        qa = ModelQAResult(simulation_configuration_id=config.id, checks=qa_data["checks"], overall_status=qa_data["overall_status"])
        db.add(qa)
        db.commit()

    if qa.overall_status == "BLOCKED":
        raise HTTPException(status_code=400, detail="Simulation execution is BLOCKED by Model QA Gate.")

    proc_def = db.query(ProcessingDefinition).first()
    proc_sha256 = proc_def.sha256 if proc_def else "proc00"

    fingerprint = compute_execution_fingerprint(
        configuration_hash=config.configuration_hash,
        solver_name=config.solver_name,
        solver_version=config.solver_version,
        solver_build="BUILD-2026",
        processing_definition_sha256=proc_sha256
    )

    adapter = get_solver_adapter(config.solver_name)
    prepared = adapter.prepare_input({
        "id": config.id,
        "storage_dir": settings.STORAGE_DIR,
        "yaw_deg": getattr(config, "yaw_deg", 0.0),
        "pitch_deg": getattr(config, "pitch_deg", 0.0),
        "roll_deg": getattr(config, "roll_deg", 0.0),
        "dummy_offset_x": getattr(config, "dummy_offset_x", 0.0),
        "dummy_offset_y": getattr(config, "dummy_offset_y", 0.0),
        "dummy_offset_z": getattr(config, "dummy_offset_z", 0.0),
        "dummy_recline_deg": getattr(config, "dummy_recline_deg", 0.0),
        "dummy_yaw_deg": getattr(config, "dummy_yaw_deg", 0.0),
        "seat_pitch_warp_deg": getattr(config, "seat_pitch_warp_deg", 0.0),
        "seat_roll_warp_deg": getattr(config, "seat_roll_warp_deg", 0.0),
        "seat_yaw_mount_deg": getattr(config, "seat_yaw_mount_deg", 0.0),
        "pulse_type": getattr(config, "pulse_type", "FORWARD_16G"),
        "dummy_type": getattr(config, "dummy_type", "FAA_HIII_50M"),
        "custom_pulse_data": getattr(config, "custom_pulse_data", None)
    })
    
    ext_ref = adapter.submit_job(prepared, ComputeConfiguration())

    job = SolverJob(
        simulation_configuration_id=config.id,
        execution_fingerprint=fingerprint,
        status="RUNNING",
        hpc_job_id=ext_ref.job_id,
        attempt_count=1,
        started_at=datetime.now(timezone.utc)
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    raw_output = adapter.parse_results(ext_ref)

    job.status = "COMPLETED"
    job.finished_at = datetime.now(timezone.utc)
    db.commit()

    sim_res = SimulationResult(
        solver_job_id=job.id,
        d3plot_uri=raw_output.d3plot_uri,
        binout_uri=raw_output.binout_uri,
        output_sha256=raw_output.output_sha256
    )
    db.add(sim_res)
    db.commit()
    db.refresh(sim_res)

    metrics_data = compute_all_injury_metrics(raw_output.timeseries_data)
    inj_record = InjuryMetrics(
        simulation_result_id=sim_res.id,
        hic15=metrics_data["hic15"],
        nij_max=metrics_data["nij_max"],
        nij_type=metrics_data["nij_type"],
        femur_load_left=metrics_data["femur_load_left"],
        femur_load_right=metrics_data["femur_load_right"],
        lumbar_load=metrics_data["lumbar_load"],
        belt_shoulder_load_kn=metrics_data.get("belt_shoulder_load_kn"),
        belt_lap_load_kn=metrics_data.get("belt_lap_load_kn"),
        head_excursion_mm=metrics_data["head_excursion_mm"],
        knee_excursion_mm=metrics_data["knee_excursion_mm"],
        seat_structural_status=metrics_data["seat_structural_status"],
        raw_timeseries=metrics_data["raw_timeseries"]
    )
    db.add(inj_record)
    db.commit()
    db.refresh(inj_record)

    standard = db.query(RegulatoryStandard).filter(RegulatoryStandard.code == "AS8049").first()
    requirements = db.query(Requirement).filter(Requirement.standard_id == standard.id).all() if standard else db.query(Requirement).all()
    
    for req in requirements:
        val = None
        if req.metric == "HIC15": val = inj_record.hic15
        elif req.metric == "NIJ": val = inj_record.nij_max
        elif req.metric == "FEMUR_LOAD":
            if inj_record.femur_load_left is not None and inj_record.femur_load_right is not None:
                val = max(inj_record.femur_load_left, inj_record.femur_load_right)
        elif req.metric == "LUMBAR_LOAD": val = inj_record.lumbar_load
        elif req.metric == "HEAD_EXCURSION": val = inj_record.head_excursion_mm
        elif "BELT" in req.metric.upper() or "STRAP" in req.metric.upper(): val = inj_record.belt_shoulder_load_kn
        
        if val is None:
            req_status = RequirementStatus(
                requirement_id=req.id,
                injury_metrics_id=inj_record.id,
                measured_value=0.0,
                status="NOT_ASSESSABLE",
                margin_percent=None
            )
        else:
            pass_flag = (val <= req.limit_value) if req.limit_operator == "<=" else (val >= req.limit_value)
            margin = ((req.limit_value - val) / req.limit_value * 100.0) if req.limit_value != 0 else 0.0
            
            req_status = RequirementStatus(
                requirement_id=req.id,
                injury_metrics_id=inj_record.id,
                measured_value=val,
                status="PASS" if pass_flag else "FAIL",
                margin_percent=round(margin, 2)
            )
        db.add(req_status)

    db.commit()

    time_arr = raw_output.timeseries_data.get("time_s", [])
    head_accel_arr = raw_output.timeseries_data.get("head_acceleration", [])
    femur_l_arr = raw_output.timeseries_data.get("femur_load_left", [])
    femur_r_arr = raw_output.timeseries_data.get("femur_load_right", [])
    lumbar_arr = raw_output.timeseries_data.get("lumbar_load", [])
    sled_accel_arr = raw_output.timeseries_data.get("sled_acceleration", [])

    return {
        "cache_hit": False,
        "solver_job": {
            "id": job.id, 
            "status": job.status, 
            "execution_fingerprint": job.execution_fingerprint
        },
        "simulation_result": {
            "id": sim_res.id, 
            "solver_job_id": sim_res.solver_job_id, 
            "output_sha256": sim_res.output_sha256,
            "duration_ms": 180.0,
            "sample_count": len(time_arr)
        },
        "injury_metrics": {
            "id": inj_record.id,
            "hic15": inj_record.hic15,
            "hic15_t1_ms": metrics_data.get("hic15_t1_ms"),
            "hic15_t2_ms": metrics_data.get("hic15_t2_ms"),
            "nij_max": inj_record.nij_max,
            "nij_type": inj_record.nij_type,
            "femur_load_left": inj_record.femur_load_left,
            "femur_load_right": inj_record.femur_load_right,
            "lumbar_load": inj_record.lumbar_load,
            "belt_shoulder_load_kn": inj_record.belt_shoulder_load_kn,
            "belt_lap_load_kn": inj_record.belt_lap_load_kn,
            "head_excursion_mm": inj_record.head_excursion_mm,
            "knee_excursion_mm": inj_record.knee_excursion_mm,
            "seat_structural_status": inj_record.seat_structural_status,
            "delta_v_ms": metrics_data.get("delta_v_ms")
        },
        "kinematics": raw_output.timeseries_data.get("kinematics", {}),
        "frames": raw_output.timeseries_data.get("frames", {}),
        "loads": raw_output.timeseries_data.get("loads", {}),
        "constraints": raw_output.timeseries_data.get("constraints", {}),
        "force_vectors": raw_output.timeseries_data.get("force_vectors", {}),
        "animation": {
            "available": True,
            "sample_count": len(time_arr),
            "duration_ms": 180.0,
            "frames": raw_output.timeseries_data.get("frames", {}),
            "kinematics": raw_output.timeseries_data.get("kinematics", {}),
            "constraints": raw_output.timeseries_data.get("constraints", {}),
            "force_vectors": raw_output.timeseries_data.get("force_vectors", {}),
            "timeseries": {
                "time": time_arr,
                "head_accel": head_accel_arr,
                "femur_load_l": femur_l_arr,
                "femur_load_r": femur_r_arr,
                "lumbar_load": lumbar_arr,
                "sled_accel": sled_accel_arr
            }
        }
    }

@router.get("/solver-jobs/{job_id}")
def get_solver_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(SolverJob).filter(SolverJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Solver job not found")
    return job

@router.get("/simulation-configurations/{config_id}/requirement-status")
def get_requirement_status(config_id: str, db: Session = Depends(get_db)):
    jobs = db.query(SolverJob).filter(SolverJob.simulation_configuration_id == config_id, SolverJob.status == "COMPLETED").all()
    if not jobs:
        raise HTTPException(status_code=404, detail="No completed simulation jobs found for this configuration.")
        
    job_ids = [j.id for j in jobs]
    sim_res = db.query(SimulationResult).filter(SimulationResult.solver_job_id.in_(job_ids)).order_by(SimulationResult.created_at.desc()).first()
    if not sim_res:
        raise HTTPException(status_code=404, detail="No simulation results found for this configuration.")

    inj = db.query(InjuryMetrics).filter(InjuryMetrics.simulation_result_id == sim_res.id).first()
    if not inj:
        raise HTTPException(status_code=404, detail="No injury metrics found for this simulation result.")

    statuses = db.query(RequirementStatus).filter(RequirementStatus.injury_metrics_id == inj.id).all()
    res = []
    for s in statuses:
        req = db.query(Requirement).filter(Requirement.id == s.requirement_id).first()
        res.append({
            "requirement_code": req.code if req else "N/A",
            "metric": req.metric if req else "N/A",
            "measured_value": s.measured_value,
            "operator": req.limit_operator if req else "<=",
            "limit_value": req.limit_value if req else 0.0,
            "unit": req.limit_unit if req else "",
            "status": s.status,
            "margin_percent": s.margin_percent
        })
    return res
