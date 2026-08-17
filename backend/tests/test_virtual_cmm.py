import pytest
import numpy as np

from app.domain.certification.virtual_cmm import VirtualCMMEngine, CMMInspectionReport

def test_virtual_cmm_compliant_egress_inspection():
    """
    Verifies a compliant post-crash seat deformation:
    - Delta X = 70.0 mm <= 76.2 mm (3.0 in)
    - Seat Pan Pitch = -15.0 deg (within -20 deg to +35 deg)
    - Verdict: PASS
    """
    cmm = VirtualCMMEngine()
    
    ref_top = cmm.probe_point([150.0, 0.0, 1100.0])
    ref_pan_rear = cmm.probe_point([100.0, 0.0, 400.0])
    ref_pan_front = cmm.probe_point([500.0, 0.0, 420.0])
    
    def_top = cmm.probe_point([220.0, 0.0, 1080.0]) # 70 mm forward deflection
    def_pan_rear = cmm.probe_point([105.0, 0.0, 395.0])
    def_pan_front = cmm.probe_point([502.0, 0.0, 310.0]) # Minor downward pitch
    
    fore_aft_mm = cmm.measure_fore_aft_deformation(ref_top, def_top)
    pitch_deg = cmm.measure_seat_pan_rotation(ref_pan_rear, ref_pan_front, def_pan_rear, def_pan_front)
    
    report = cmm.generate_egress_report(fore_aft_mm, pitch_deg)
    
    assert report.is_translation_compliant is True
    assert report.is_rotation_compliant is True
    assert report.egress_status == "PASS"
    assert abs(report.fore_aft_deformation_mm - 70.0) < 0.1

def test_virtual_cmm_exceeded_deformation_fail():
    """
    Verifies that excessive plastic deformation (e.g. Delta X = 85.0 mm > 76.2 mm)
    triggers an egress FAIL verdict.
    """
    cmm = VirtualCMMEngine()
    
    ref_top = cmm.probe_point([150.0, 0.0, 1100.0])
    def_top = cmm.probe_point([235.0, 0.0, 1080.0]) # 85 mm forward deflection (Exceeds 76.2 mm)
    
    fore_aft_mm = cmm.measure_fore_aft_deformation(ref_top, def_top)
    report = cmm.generate_egress_report(fore_aft_def_mm=fore_aft_mm, seat_pan_pitch_deg=0.0)
    
    assert report.is_translation_compliant is False
    assert report.egress_status == "FAIL"

def test_virtual_cmm_excessive_pitch_down_fail():
    """
    Verifies that seat pan pitch collapse below -20 degrees (e.g. -25 degrees)
    triggers an egress entrapment FAIL verdict.
    """
    cmm = VirtualCMMEngine()
    report = cmm.generate_egress_report(fore_aft_def_mm=50.0, seat_pan_pitch_deg=-25.0)
    
    assert report.is_rotation_compliant is False
    assert report.egress_status == "FAIL"
