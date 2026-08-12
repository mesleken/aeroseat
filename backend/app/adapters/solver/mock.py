import os
import json
import hashlib
import numpy as np
from app.adapters.solver.base import (
    BaseSolverAdapter, PreparedInput, ComputeConfiguration, ExternalJobRef, SolverStatus, RawSimulationOutput
)

class MockSolverAdapter(BaseSolverAdapter):
    """Explicit Mock Solver Adapter for Development, Testing, and Harness Execution.
    
    Uses deterministic pseudo-random seed to guarantee bit-for-bit reproducible mock results.
    """
    
    def __init__(self, seed: int = 42):
        self.seed = seed

    def prepare_input(self, config_data: dict) -> PreparedInput:
        storage_dir = config_data.get("storage_dir", "./storage_data")
        config_id = config_data.get("id", "cfg-test")
        
        job_dir = os.path.join(storage_dir, "jobs", config_id)
        os.makedirs(job_dir, exist_ok=True)
        
        input_deck_path = os.path.join(job_dir, "mock_input.k")
        deck_content = f"*MOCK_DECK_CONFIG_{config_id}\n*END\n"
        
        with open(input_deck_path, "w", encoding="utf-8") as f:
            f.write(deck_content)
            
        deck_hash = hashlib.sha256(deck_content.encode("utf-8")).hexdigest()
        
        return PreparedInput(
            input_deck_uri=input_deck_path,
            input_deck_hash=deck_hash,
            metadata={"solver": "MOCK", "job_dir": job_dir}
        )

    def submit_job(self, prepared: PreparedInput, compute: ComputeConfiguration) -> ExternalJobRef:
        job_dir = prepared.metadata.get("job_dir", "./storage_data")
        job_id = os.path.basename(job_dir)
        
        status_file = os.path.join(job_dir, "status.json")
        with open(status_file, "w", encoding="utf-8") as f:
            json.dump({"status": "RUNNING", "progress": 0.0}, f)
            
        return ExternalJobRef(
            job_id=job_id,
            cluster_name="Mock-Compute-Cluster",
            working_dir=job_dir
        )

    def poll_status(self, ref: ExternalJobRef) -> SolverStatus:
        return SolverStatus(status_code="COMPLETED", progress_pct=100.0)

    def parse_results(self, ref: ExternalJobRef) -> RawSimulationOutput:
        d3plot_path = os.path.join(ref.working_dir, "d3plot")
        binout_path = os.path.join(ref.working_dir, "binout")
        
        # Deterministic random generator using fixed seed
        rng = np.random.default_rng(self.seed)
        
        t = np.linspace(-0.010, 0.180, 1901) # 10kHz sample rate
        
        # Deterministic Head Acceleration (g) - Peak ~ 42g around 75ms
        noise = rng.normal(0, 0.1, len(t))
        head_accel_g = 42.0 * np.exp(-((t - 0.075)**2) / (2 * (0.018**2))) + noise
        neck_moment = 38.0 * np.exp(-((t - 0.078)**2) / (2 * (0.020**2)))
        neck_fz = 1200.0 * np.exp(-((t - 0.075)**2) / (2 * (0.020**2)))
        femur_left_kn = 4.2 * np.exp(-((t - 0.082)**2) / (2 * (0.022**2)))
        femur_right_kn = 4.1 * np.exp(-((t - 0.083)**2) / (2 * (0.022**2)))
        lumbar_kn = 3.5 * np.exp(-((t - 0.080)**2) / (2 * (0.025**2)))
        sled_g = 16.0 * np.exp(-((t - 0.060)**2) / (2 * (0.035**2)))

        timeseries_data = {
            "time_s": t.tolist(),
            "head_acceleration": head_accel_g.tolist(),
            "neck_moment": neck_moment.tolist(),
            "neck_axial_force": neck_fz.tolist(),
            "femur_load_left": femur_left_kn.tolist(),
            "femur_load_right": femur_right_kn.tolist(),
            "lumbar_load": lumbar_kn.tolist(),
            "sled_acceleration": sled_g.tolist(),
            "head_excursion_mm": 540.0,
            "knee_excursion_mm": 410.0,
            "seat_structural_status": "INTACT_NO_FAILURE"
        }
        
        with open(d3plot_path, "w", encoding="utf-8") as f:
            f.write("MOCK D3PLOT BINARY DATA")
            
        with open(binout_path, "w", encoding="utf-8") as f:
            json.dump(timeseries_data, f)
            
        out_hash = hashlib.sha256(json.dumps(timeseries_data, sort_keys=True).encode("utf-8")).hexdigest()
        
        return RawSimulationOutput(
            d3plot_uri=d3plot_path,
            binout_uri=binout_path,
            output_sha256=out_hash,
            timeseries_data=timeseries_data
        )
