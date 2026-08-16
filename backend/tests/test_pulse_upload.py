import io
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_custom_pulse_csv_upload_valid():
    """Valid CSV pulse upload creates PulseDefinition with Delta-V check."""
    csv_content = (
        "time_s,acceleration_g\n"
        "0.000,0.0\n"
        "0.020,3.5\n"
        "0.050,10.0\n"
        "0.090,16.5\n"
        "0.130,9.0\n"
        "0.180,0.0\n"
    )
    
    file_bytes = io.BytesIO(csv_content.encode("utf-8"))
    res = client.post(
        "/api/v1/pulse-definitions/upload",
        data={"name": "Custom Dynamic Sled Test 01", "direction": "FORWARD_16G"},
        files={"file": ("custom_sled_pulse.csv", file_bytes, "text/csv")}
    )
    
    assert res.status_code == 201
    data = res.json()
    assert "id" in data
    assert data["peak_g"] == 16.5
    assert data["delta_v_ms"] > 0
    assert len(data["curve_preview"]) > 0

def test_cad_file_upload():
    """CAD file upload stores geometry and creates ModelRevision."""
    # First create a project
    proj_res = client.post("/api/v1/projects", json={
        "name": "AeroSeat CAD Upload Test Project",
        "customer_id": "cust-default-001"
    })
    assert proj_res.status_code == 201
    proj_id = proj_res.json()["id"]

    cad_bytes = io.BytesIO(b"ISO-10303-21; HEADER; STEP CAD DUMMY; ENDSEC; END-ISO-10303-21;")
    cad_res = client.post(
        f"/api/v1/projects/{proj_id}/cad-upload",
        data={"revision_label": "REV-2026-B1"},
        files={"file": ("seat_structure_assembly.step", cad_bytes, "application/octet-stream")}
    )

    assert cad_res.status_code == 201
    cad_data = cad_res.json()
    assert cad_data["seat_architecture_id"] == proj_id
    assert cad_data["revision_label"] == "REV-2026-B1"
    assert "cad_file_sha256" in cad_data
    assert len(cad_data["cad_file_sha256"]) == 64
