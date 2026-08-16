import os
import json
import hashlib
from app.adapters.solver.base import (
    BaseSolverAdapter, PreparedInput, ComputeConfiguration, ExternalJobRef, SolverStatus, RawSimulationOutput
)
from app.domain.physics.lumped_mass_model import LumpedMassCrashModel

class PhysicsSolverAdapter(BaseSolverAdapter):
    """Physics-based Dynamic Lumped-Mass Solver Adapter.
    
    Explicit multi-DOF crash dynamics engine that dynamically responds
    to yaw, pitch, roll angles, dummy types (HIII-50M, 5F, 95M), pulse definitions, and seat parameters.
    """

    def __init__(self, seed: int = 42):
        self.seed = seed

    def prepare_input(self, config_data: dict) -> PreparedInput:
        storage_dir = config_data.get("storage_dir", "./storage_data")
        config_id = config_data.get("id", "cfg-physics")
        
        job_dir = os.path.join(storage_dir, "jobs", config_id)
        os.makedirs(job_dir, exist_ok=True)

        yaw_deg = float(config_data.get("yaw_deg", 0.0))
        pitch_deg = float(config_data.get("pitch_deg", 0.0))
        roll_deg = float(config_data.get("roll_deg", 0.0))
        dummy_offset_x = float(config_data.get("dummy_offset_x", 0.0))
        dummy_offset_y = float(config_data.get("dummy_offset_y", 0.0))
        dummy_offset_z = float(config_data.get("dummy_offset_z", 0.0))
        dummy_recline_deg = float(config_data.get("dummy_recline_deg", 0.0))
        dummy_yaw_deg = float(config_data.get("dummy_yaw_deg", 0.0))
        seat_pitch_warp_deg = float(config_data.get("seat_pitch_warp_deg", 0.0))
        seat_roll_warp_deg = float(config_data.get("seat_roll_warp_deg", 0.0))
        seat_yaw_mount_deg = float(config_data.get("seat_yaw_mount_deg", 0.0))
        pulse_type = config_data.get("pulse_type", "FORWARD_16G")
        dummy_type = config_data.get("dummy_type", "FAA_HIII_50M")
        custom_pulse_data = config_data.get("custom_pulse_data")

        deck_content = (
            f"*AEROSEAT_PHYSICS_ENGINE_INPUT_DECK\n"
            f"*CONFIG_ID: {config_id}\n"
            f"*PULSE_TYPE: {pulse_type}\n"
            f"*DUMMY_TYPE: {dummy_type}\n"
            f"*YAW_ANGLE_DEG: {yaw_deg}\n"
            f"*PITCH_ANGLE_DEG: {pitch_deg}\n"
            f"*ROLL_ANGLE_DEG: {roll_deg}\n"
            f"*DUMMY_OFFSET_XYZ_CM: {dummy_offset_x},{dummy_offset_y},{dummy_offset_z}\n"
            f"*DUMMY_RECLINE_DEG: {dummy_recline_deg}\n"
            f"*DUMMY_YAW_DEG: {dummy_yaw_deg}\n"
            f"*SEAT_WARP_DEG: {seat_pitch_warp_deg},{seat_roll_warp_deg},{seat_yaw_mount_deg}\n"
            f"*CUSTOM_PULSE_ATTACHED: {bool(custom_pulse_data)}\n"
            f"*INTEGRATION: EXPLICIT_CENTRAL_DIFFERENCE\n"
            f"*END\n"
        )

        input_deck_path = os.path.join(job_dir, "physics_input.k")
        with open(input_deck_path, "w", encoding="utf-8") as f:
            f.write(deck_content)

        deck_hash = hashlib.sha256(deck_content.encode("utf-8")).hexdigest()

        return PreparedInput(
            input_deck_uri=input_deck_path,
            input_deck_hash=deck_hash,
            metadata={
                "solver": "PHYSICS_LUMPED_MASS",
                "integrator_type": "EXPLICIT_RK4_FIXED_SUBSTEP",
                "integrator_order": 4,
                "time_step_s": 0.0001,
                "femur_model_type": "SURROGATE_EMPIRICAL_LOAD_ALLOCATION",
                "lumbar_model_type": "SURROGATE_EMPIRICAL_EQUILIBRIUM",
                "calibration_status": "NOT_YET_VALIDATED",
                "reference_basis": "PART_572_GEOMETRIC_AND_MASS_TARGETS",
                "job_dir": job_dir,
                "yaw_deg": yaw_deg,
                "pitch_deg": pitch_deg,
                "roll_deg": roll_deg,
                "dummy_offset_x": dummy_offset_x,
                "dummy_offset_y": dummy_offset_y,
                "dummy_offset_z": dummy_offset_z,
                "dummy_recline_deg": dummy_recline_deg,
                "dummy_yaw_deg": dummy_yaw_deg,
                "seat_pitch_warp_deg": seat_pitch_warp_deg,
                "seat_roll_warp_deg": seat_roll_warp_deg,
                "seat_yaw_mount_deg": seat_yaw_mount_deg,
                "pulse_type": pulse_type,
                "dummy_type": dummy_type,
                "custom_pulse_data": custom_pulse_data
            }
        )

    def submit_job(self, prepared: PreparedInput, compute: ComputeConfiguration) -> ExternalJobRef:
        job_dir = prepared.metadata.get("job_dir", "./storage_data")
        job_id = os.path.basename(job_dir)

        # Execute physics simulation with full dynamic parametrization
        model = LumpedMassCrashModel(
            pulse_type=prepared.metadata.get("pulse_type", "FORWARD_16G"),
            dummy_type=prepared.metadata.get("dummy_type", "FAA_HIII_50M"),
            yaw_deg=prepared.metadata.get("yaw_deg", 0.0),
            pitch_deg=prepared.metadata.get("pitch_deg", 0.0),
            roll_deg=prepared.metadata.get("roll_deg", 0.0),
            dummy_offset_x=prepared.metadata.get("dummy_offset_x", 0.0),
            dummy_offset_y=prepared.metadata.get("dummy_offset_y", 0.0),
            dummy_offset_z=prepared.metadata.get("dummy_offset_z", 0.0),
            dummy_recline_deg=prepared.metadata.get("dummy_recline_deg", 0.0),
            dummy_yaw_deg=prepared.metadata.get("dummy_yaw_deg", 0.0),
            seat_pitch_warp_deg=prepared.metadata.get("seat_pitch_warp_deg", 0.0),
            seat_roll_warp_deg=prepared.metadata.get("seat_roll_warp_deg", 0.0),
            seat_yaw_mount_deg=prepared.metadata.get("seat_yaw_mount_deg", 0.0),
            custom_pulse_data=prepared.metadata.get("custom_pulse_data"),
            seed=self.seed
        )
        sim_data = model.run()

        # Write output files
        d3plot_path = os.path.join(job_dir, "d3plot")
        binout_path = os.path.join(job_dir, "binout")

        with open(d3plot_path, "w", encoding="utf-8") as f:
            f.write(f"AEROSEAT_PHYSICS_D3PLOT_STATE_DATA_JOB_{job_id}")

        with open(binout_path, "w", encoding="utf-8") as f:
            json.dump(sim_data, f)

        status_file = os.path.join(job_dir, "status.json")
        with open(status_file, "w", encoding="utf-8") as f:
            json.dump({"status": "COMPLETED", "progress": 100.0}, f)

        return ExternalJobRef(
            job_id=job_id,
            cluster_name="AeroSeat-Physics-Engine",
            working_dir=job_dir
        )

    def poll_status(self, ref: ExternalJobRef) -> SolverStatus:
        return SolverStatus(status_code="COMPLETED", progress_pct=100.0)

    def parse_results(self, ref: ExternalJobRef) -> RawSimulationOutput:
        d3plot_path = os.path.join(ref.working_dir, "d3plot")
        binout_path = os.path.join(ref.working_dir, "binout")

        with open(binout_path, "r", encoding="utf-8") as f:
            timeseries_data = json.load(f)

        out_hash = hashlib.sha256(json.dumps(timeseries_data, sort_keys=True).encode("utf-8")).hexdigest()

        return RawSimulationOutput(
            d3plot_uri=d3plot_path,
            binout_uri=binout_path,
            output_sha256=out_hash,
            timeseries_data=timeseries_data
        )
