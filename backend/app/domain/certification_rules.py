"""
FAA AC 25.562-1B / 14 CFR § 25.562 Statutory Certification & Data Reduction Engine.

Implements legal compliance rules, data reduction allowances, 95th-percentile flail envelopes,
and front-row exemption criteria for aviation seating certification.
"""

from dataclasses import dataclass
from typing import Tuple, Dict, Any, Optional

@dataclass
class ReductionResult:
    """Detailed output of an FAA Data Reduction adjustment."""
    raw_load: float
    adjusted_load: float
    reduction_ratio: float
    reduction_percent: float
    applied: bool
    actual_peak_g: float
    target_peak_g: float
    rule: str = "FAA AC 25.562-1B Paragraph 12.e & 12.f"

@dataclass
class ExemptionResult:
    """Outcome of a regulatory front-row HIC exemption audit."""
    is_exempt: bool
    reason: str
    setback_inches: float
    seat_class: str
    rule: str = "FAA AC 25.562-1B Paragraph 5.e(5)(d)3"

class FAACertificationEngine:
    """
    AeroSeat - FAA AC 25.562-1B Statutory Compliance and Data Reduction Engine.
    Evaluates dynamic sled tests against legal FAA regulatory limits (14 CFR § 25.562):
    - Lumbar Spinal Axial Load: <= 1500 lb (6.67 kN)
    - Femur Compressive Load: <= 2250 lb (10.0 kN)
    - Head Injury Criterion (HIC15): <= 1000
    - Shoulder Restraint Webbing Tension: <= 1750 lb (single), <= 2000 lb (dual harness)
    """

    def __init__(self):
        self.MAX_LUMBAR_LOAD_LB = 1500.0
        self.MAX_FEMUR_LOAD_LB = 2250.0
        self.MAX_HIC = 1000.0
        self.MAX_SHOULDER_RESTRAINT_LB = 1750.0
        self.MAX_DUAL_SHOULDER_RESTRAINT_LB = 2000.0
        
        # SI Equivalent Constants (kN)
        self.MAX_LUMBAR_LOAD_KN = 6.672
        self.MAX_FEMUR_LOAD_KN = 10.008

    def apply_data_reduction(
        self,
        measured_load: float,
        actual_peak_g: float,
        target_peak_g: float
    ) -> float:
        """
        FAA AC 25.562-1B Paragraph 12.e & 12.f:
        If actual sled acceleration (actual_peak_g) exceeds target (target_peak_g),
        loads may be reduced proportionally (target_g / actual_g), up to a MAXIMUM of 10% (ratio >= 0.90).
        """
        if actual_peak_g <= target_peak_g:
            return float(measured_load)
            
        ratio = target_peak_g / actual_peak_g
        allowable_ratio = max(ratio, 0.90)  # Capped at max 10% reduction
        
        return float(measured_load * allowable_ratio)

    def apply_data_reduction_detailed(
        self,
        measured_load: float,
        actual_peak_g: float,
        target_peak_g: float
    ) -> ReductionResult:
        """Detailed data reduction audit returning full reduction metadata and ratio."""
        if actual_peak_g <= target_peak_g:
            return ReductionResult(
                raw_load=round(float(measured_load), 2),
                adjusted_load=round(float(measured_load), 2),
                reduction_ratio=1.0,
                reduction_percent=0.0,
                applied=False,
                actual_peak_g=actual_peak_g,
                target_peak_g=target_peak_g
            )
            
        ratio = target_peak_g / actual_peak_g
        allowable_ratio = max(ratio, 0.90)
        adj_load = measured_load * allowable_ratio
        reduc_pct = (1.0 - allowable_ratio) * 100.0
        
        return ReductionResult(
            raw_load=round(float(measured_load), 2),
            adjusted_load=round(float(adj_load), 2),
            reduction_ratio=round(float(allowable_ratio), 4),
            reduction_percent=round(float(reduc_pct), 2),
            applied=True,
            actual_peak_g=actual_peak_g,
            target_peak_g=target_peak_g
        )

    def evaluate_95th_percentile_head_path(self, measured_head_path_mm: float) -> float:
        """
        FAA AC 25.562-1B Paragraph 5.e(5)(b):
        When tests are conducted with 50th percentile ATD, the 95th percentile flail envelope
        is evaluated by adding an offset of 3.0 inches (76.2 mm) to the measured head trajectory apex.
        """
        offset_mm = 3.0 * 25.4  # 76.2 mm
        return float(measured_head_path_mm + offset_mm)

    def check_front_row_hic_exemption(
        self,
        setback_inches: float,
        seat_class: str = "economy",
        is_metallic_load_path: bool = True
    ) -> Tuple[bool, str]:
        """
        FAA AC 25.562-1B Paragraph 5.e(5)(d)3:
        For front-row seating with a primary metallic load path:
        - Economy Class setback >= 42.0 inches -> EXEMPT from dynamic HIC test
        - Business/First Class setback >= 45.0 inches -> EXEMPT from dynamic HIC test
        """
        if not is_metallic_load_path:
            return False, "Muafiyet reddedildi: Birincil yuk yolu metalik olmalidir."
            
        cls = seat_class.strip().lower()
        if cls == "economy" and setback_inches >= 42.0:
            return True, f"PASS: Ekonomi sinifi {setback_inches:.1f} inc >= 42.0 inc muafiyetini sagladi. Dinamik HIC testine gerek yoktur."
            
        if cls in ["business", "first", "premium_economy"] and setback_inches >= 45.0:
            return True, f"PASS: {seat_class.capitalize()} sinifi {setback_inches:.1f} inc >= 45.0 inc muafiyetini sagladi. Dinamik HIC testine gerek yoktur."
            
        min_req = 42.0 if cls == "economy" else 45.0
        return False, f"Muafiyet reddedildi: Setback mesafesi ({setback_inches:.1f} in) yetersiz (Gereken: >= {min_req:.1f} in). Dinamik simulasyon/test sarttir."

    def evaluate_compliance_summary(
        self,
        raw_lumbar_lb: float,
        raw_femur_lb: float,
        raw_hic: float,
        actual_peak_g: float,
        target_peak_g: float,
        head_path_mm: float,
        setback_inches: float
    ) -> Dict[str, Any]:
        """Full end-to-end statutory certification verdict combining reduction and injury rules."""
        adj_lumbar = self.apply_data_reduction(raw_lumbar_lb, actual_peak_g, target_peak_g)
        adj_femur = self.apply_data_reduction(raw_femur_lb, actual_peak_g, target_peak_g)
        flail_95th_mm = self.evaluate_95th_percentile_head_path(head_path_mm)
        
        lumbar_pass = adj_lumbar <= self.MAX_LUMBAR_LOAD_LB
        femur_pass = adj_femur <= self.MAX_FEMUR_LOAD_LB
        hic_pass = raw_hic <= self.MAX_HIC
        
        overall = lumbar_pass and femur_pass and hic_pass
        
        return {
            "overall_faa_certification_verdict": "PASS" if overall else "FAIL",
            "lumbar": {
                "raw_lb": round(raw_lumbar_lb, 1),
                "adjusted_lb": round(adj_lumbar, 1),
                "limit_lb": self.MAX_LUMBAR_LOAD_LB,
                "is_compliant": lumbar_pass
            },
            "femur": {
                "raw_lb": round(raw_femur_lb, 1),
                "adjusted_lb": round(adj_femur, 1),
                "limit_lb": self.MAX_FEMUR_LOAD_LB,
                "is_compliant": femur_pass
            },
            "hic": {
                "value": round(raw_hic, 1),
                "limit": self.MAX_HIC,
                "is_compliant": hic_pass
            },
            "head_flail_envelope": {
                "head_path_50th_mm": round(head_path_mm, 1),
                "head_path_95th_mm": round(flail_95th_mm, 1),
                "offset_applied_mm": 76.2
            }
        }
