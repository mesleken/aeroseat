"""
AeroSeat Phase 17: Virtual CMM Inspection & Egress Compliance Engine.

Simulates physical FaroArm / Coordinate Measuring Machine (CMM) probe inspections
per FAA AC 25.562-1B Appendix 2 'Seat Deformation & Egress Clearance Requirements':
1. Fore/Aft (X-axis) Permanent Translation Limit: Delta X <= 3.0 inches (76.2 mm)
2. Seat Pan Pitch Rotation Limit: -20.0 deg (Pitch Down) <= Theta <= +35.0 deg (Pitch Up)
3. Generates certified CMMInspectionReport for FAA Egress Compliance Audits.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class CMMInspectionReport:
    """Sanal CMM (FaroArm) Ölçüm ve FAA Tahliye (Egress) Uygunluk Raporu."""
    fore_aft_deformation_mm: float
    seat_pan_pitch_deg: float
    is_translation_compliant: bool
    is_rotation_compliant: bool
    egress_status: str  # "PASS" or "FAIL"
    max_translation_limit_mm: float = 76.2
    min_pitch_limit_deg: float = -20.0
    max_pitch_limit_deg: float = 35.0
    faa_reference: str = "FAA AC 25.562-1B Appendix 2 - Seat Deformation & Egress"

class VirtualCMMEngine:
    """
    AeroSeat - Virtual CMM Inspection & Egress Compliance Engine.
    Simulates FaroArm / CMM probe measurements comparing T=0 pre-test datum against
    T=250ms post-test permanent plastic deformation.
    """

    def __init__(
        self,
        max_fore_aft_deformation_mm: float = 76.2,  # 3.0 inches per AC 25.562-1B App. 2
        max_pitch_down_deg: float = -20.0,          # -20 degrees downward tilt limit
        max_pitch_up_deg: float = 35.0              # +35 degrees upward pitch limit
    ):
        self.MAX_FORE_AFT_DEFORMATION_MM = float(max_fore_aft_deformation_mm)
        self.MAX_PITCH_DOWN_DEG = float(max_pitch_down_deg)
        self.MAX_PITCH_UP_DEG = float(max_pitch_up_deg)

    def probe_point(self, coordinates: List[float] | np.ndarray) -> np.ndarray:
        """Sanal CMM probu ile 3D uzaydan nokta okuma simülasyonu [X, Y, Z] (mm)."""
        return np.asarray(coordinates, dtype=np.float64)

    def measure_fore_aft_deformation(self, pre_test_pt: np.ndarray, post_test_pt: np.ndarray) -> float:
        """
        X eksenindeki (İleri/Geri) kalıcı deformasyonu ölçer:
        Delta_X = |X_post - X_pre|
        """
        delta_x = float(post_test_pt[0] - pre_test_pt[0])
        return abs(delta_x)

    def measure_seat_pan_rotation(
        self,
        pre_front_pt: np.ndarray,
        pre_rear_pt: np.ndarray,
        post_front_pt: np.ndarray,
        post_rear_pt: np.ndarray
    ) -> float:
        """
        Oturma minderinin (Seat Pan) kalıcı yunuslama (Pitch) açısını hesaplar.
        """
        # Pre-test Vektörü (Arkadan öne)
        vec_pre = pre_front_pt - pre_rear_pt
        vec_pre[1] = 0.0  # X-Z sagittal düzlemindeki rotasyon
        
        # Post-test Vektörü (Arkadan öne)
        vec_post = post_front_pt - post_rear_pt
        vec_post[1] = 0.0
        
        # Zemin düzlemine (X ekseni) göre açıları hesapla
        angle_pre = np.degrees(np.arctan2(vec_pre[2], vec_pre[0]))
        angle_post = np.degrees(np.arctan2(vec_post[2], vec_post[0]))
        
        rotation_deg = float(angle_post - angle_pre)
        # Normalize to [-180, +180]
        rotation_deg = (rotation_deg + 180.0) % 360.0 - 180.0
        return rotation_deg

    def generate_egress_report(
        self,
        fore_aft_def_mm: float,
        seat_pan_pitch_deg: float
    ) -> CMMInspectionReport:
        """
        CMM ölçümlerini FAA Appendix 2 limitleriyle karşılaştırıp resmi uygunluk raporu üretir.
        """
        trans_compliant = bool(fore_aft_def_mm <= self.MAX_FORE_AFT_DEFORMATION_MM)
        rot_compliant = bool(self.MAX_PITCH_DOWN_DEG <= seat_pan_pitch_deg <= self.MAX_PITCH_UP_DEG)
        status = "PASS" if (trans_compliant and rot_compliant) else "FAIL"
        
        return CMMInspectionReport(
            fore_aft_deformation_mm=round(float(fore_aft_def_mm), 2),
            seat_pan_pitch_deg=round(float(seat_pan_pitch_deg), 2),
            is_translation_compliant=trans_compliant,
            is_rotation_compliant=rot_compliant,
            egress_status=status,
            max_translation_limit_mm=self.MAX_FORE_AFT_DEFORMATION_MM,
            min_pitch_limit_deg=self.MAX_PITCH_DOWN_DEG,
            max_pitch_limit_deg=self.MAX_PITCH_UP_DEG,
            faa_reference="FAA AC 25.562-1B Appendix 2 - Seat Deformation & Egress"
        )
