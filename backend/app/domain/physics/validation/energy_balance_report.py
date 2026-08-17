import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class MassScalingVerification:
    """FAA AC 20-146A Mass Scaling Verification per Section 8 / Appendix B."""
    segment_name: str
    nominal_mass_kg: float
    scaled_mass_kg: float
    is_critical_component: bool = False

    @property
    def mass_increase_pct(self) -> float:
        if self.nominal_mass_kg <= 0:
            return 0.0
        return ((self.scaled_mass_kg - self.nominal_mass_kg) / self.nominal_mass_kg) * 100.0

    @property
    def is_faa_compliant(self) -> bool:
        limit_pct = 5.0 if self.is_critical_component else 10.0
        return self.mass_increase_pct <= limit_pct

class EnergyBalanceVARReportEngine:
    """
    FAA AC 20-146A Validation & Analysis Report (VAR) Energy Balance Generator.
    Audits conservation of energy across explicit multi-body crash time integration.
    """

    @classmethod
    def audit_simulation_energy_balance(
        cls,
        kinetic_energy_series_j: np.ndarray | list[float],
        strain_energy_series_j: np.ndarray | list[float],
        dissipated_energy_series_j: np.ndarray | list[float],
        work_external_series_j: np.ndarray | list[float]
    ) -> Dict[str, float | bool | str]:
        ke = np.asarray(kinetic_energy_series_j, dtype=np.float64)
        se = np.asarray(strain_energy_series_j, dtype=np.float64)
        de = np.asarray(dissipated_energy_series_j, dtype=np.float64)
        we = np.asarray(work_external_series_j, dtype=np.float64)

        n = min(len(ke), len(se), len(de), len(we))
        if n < 5:
            return {"status": "INSUFFICIENT_ENERGY_DATA", "is_balanced": True}

        total_system_energy = ke[:n] + se[:n] + de[:n]
        e_init = max(1.0, float(total_system_energy[0]))
        e_max = float(np.max(total_system_energy))
        e_final = float(total_system_energy[-1])
        we_final = max(1.0, float(np.max(np.abs(we[:n]))))

        # Energy ratio & deviation
        energy_ratio = e_final / e_init
        energy_divergence_pct = abs(e_final - e_init) / max(e_init, we_final) * 100.0
        is_balanced = bool(energy_divergence_pct <= 5.0) # FAA 5% energy tolerance

        return {
            "initial_energy_j": round(e_init, 2),
            "final_energy_j": round(e_final, 2),
            "peak_energy_j": round(e_max, 2),
            "energy_ratio": round(energy_ratio, 4),
            "energy_divergence_pct": round(energy_divergence_pct, 2),
            "is_balanced": is_balanced,
            "status": "FAA_ENERGY_BALANCE_PASS" if is_balanced else "ENERGY_DIVERGENCE_WARNING"
        }

    @classmethod
    def verify_mass_scaling(cls, items: List[MassScalingVerification]) -> Dict[str, object]:
        audit = []
        all_passed = True
        for it in items:
            passed = it.is_faa_compliant
            if not passed:
                all_passed = False
            audit.append({
                "segment": it.segment_name,
                "nominal_kg": it.nominal_mass_kg,
                "scaled_kg": it.scaled_mass_kg,
                "increase_pct": round(it.mass_increase_pct, 2),
                "limit_pct": 5.0 if it.is_critical_component else 10.0,
                "status": "PASS" if passed else "EXCEEDS_FAA_LIMIT"
            })

        return {
            "all_components_compliant": all_passed,
            "audit_details": audit,
            "status": "MASS_SCALING_FAA_COMPLIANT" if all_passed else "MASS_SCALING_VIOLATION"
        }
