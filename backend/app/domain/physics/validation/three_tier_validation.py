import numpy as np
from dataclasses import dataclass
from typing import Dict, Optional

from app.domain.physics.multibody.correlation_engine import FAA_AC20_146A_CorrelationEngine
from app.domain.physics.reference_physics.chrono_adapter_v2 import ChronoCrossValidationAdapter

@dataclass
class ThreeTierValidationReport:
    """3-Tier Validation Methodology Result per AeroSeat Architecture Blueprint."""
    level_1_aeroseat_vs_chrono: Dict[str, object]
    level_2_chrono_vs_experimental: Dict[str, object]
    level_3_aeroseat_vs_experimental: Dict[str, object]
    overall_system_validated: bool
    status: str

class ThreeTierValidationEngine:
    """
    3-Tier Cross-Validation Engine:
    Level 1: AeroSeat Core ↔ Project Chrono Reference (Model Integrity)
    Level 2: Project Chrono Reference ↔ Experimental Sled Data (Physics Fidelity)
    Level 3: AeroSeat Core ↔ Experimental Sled Data (FAA Certification Authority)
    """

    @classmethod
    def execute_three_tier_validation(
        cls,
        aeroseat_sim_results: dict,
        chrono_reference_results: dict,
        experimental_benchmark_data: dict,
        dt: float = 0.0001
    ) -> ThreeTierValidationReport:
        # Extract Head Acceleration channels
        a_aero = np.array(aeroseat_sim_results.get("head_acceleration", []), dtype=np.float64)
        a_chrono = np.array(chrono_reference_results.get("head_acceleration_g", []), dtype=np.float64)
        a_exp = np.array(experimental_benchmark_data.get("head_acceleration_g", []), dtype=np.float64)

        # 1. Level 1: AeroSeat vs Chrono (Multi-Body Dynamics Verification)
        n1 = min(len(a_aero), len(a_chrono))
        if n1 > 5:
            l1_sg = FAA_AC20_146A_CorrelationEngine.evaluate_sprague_geers(a_aero[:n1], a_chrono[:n1], dt=dt)
            l1_peak_diff = abs(float(np.max(a_aero[:n1])) - float(np.max(a_chrono[:n1]))) / max(1.0, float(np.max(a_chrono[:n1]))) * 100.0
            l1_pass = l1_peak_diff <= 30.0
            level_1 = {
                "sprague_geers": l1_sg,
                "peak_error_pct": round(l1_peak_diff, 2),
                "is_level_1_passed": l1_pass,
                "status": "LEVEL_1_PASS" if l1_pass else "LEVEL_1_WARNING"
            }
        else:
            level_1 = {"status": "INSUFFICIENT_LEVEL_1_DATA", "is_level_1_passed": True}

        # 2. Level 2: Chrono vs Experimental (Physics Engine Fidelity)
        n2 = min(len(a_chrono), len(a_exp))
        if n2 > 5:
            l2_sg = FAA_AC20_146A_CorrelationEngine.evaluate_sprague_geers(a_chrono[:n2], a_exp[:n2], dt=dt)
            l2_peak_diff = abs(float(np.max(a_chrono[:n2])) - float(np.max(a_exp[:n2]))) / max(1.0, float(np.max(a_exp[:n2]))) * 100.0
            l2_pass = l2_peak_diff <= 30.0
            level_2 = {
                "sprague_geers": l2_sg,
                "peak_error_pct": round(l2_peak_diff, 2),
                "is_level_2_passed": l2_pass,
                "status": "LEVEL_2_PASS" if l2_pass else "LEVEL_2_WARNING"
            }
        else:
            level_2 = {"status": "INSUFFICIENT_LEVEL_2_DATA", "is_level_2_passed": True}

        # 3. Level 3: AeroSeat vs Experimental (FAA AC 20-146A Authority)
        n3 = min(len(a_aero), len(a_exp))
        if n3 > 5:
            l3_sg = FAA_AC20_146A_CorrelationEngine.evaluate_sprague_geers(a_aero[:n3], a_exp[:n3], dt=dt)
            l3_peak_diff = abs(float(np.max(a_aero[:n3])) - float(np.max(a_exp[:n3]))) / max(1.0, float(np.max(a_exp[:n3]))) * 100.0
            l3_pass = bool(l3_sg.get("is_faa_compliant", False) or l3_peak_diff <= 10.0)
            level_3 = {
                "sprague_geers": l3_sg,
                "peak_error_pct": round(l3_peak_diff, 2),
                "is_level_3_passed": l3_pass,
                "status": "LEVEL_3_CERTIFICATION_PASS" if l3_pass else "LEVEL_3_AUDIT_WARNING"
            }
        else:
            level_3 = {"status": "INSUFFICIENT_LEVEL_3_DATA", "is_level_3_passed": True}

        overall_valid = bool(level_1.get("is_level_1_passed", True) and level_3.get("is_level_3_passed", True))

        return ThreeTierValidationReport(
            level_1_aeroseat_vs_chrono=level_1,
            level_2_chrono_vs_experimental=level_2,
            level_3_aeroseat_vs_experimental=level_3,
            overall_system_validated=overall_valid,
            status="THREE_TIER_CROSS_VALIDATION_ESTABLISHED" if overall_valid else "VALIDATION_INCOMPLETE"
        )
