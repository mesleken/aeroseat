import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_full_certification_pipeline_definition_of_done():
    # 1. System Health
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["status"] == "OPERATIONAL"

    # 2. Create Project
    proj_res = client.post("/api/v1/projects", json={"name": "AeroSeat Economy Single Standard", "customer_id": "cust-default-001"})
    assert proj_res.status_code == 201
    proj_id = proj_res.json()["id"]

    # 3. Upload CAD Model Revision
    rev_res = client.post(f"/api/v1/projects/{proj_id}/model-revisions", json={
        "seat_architecture_id": proj_id,
        "revision_label": "Rev-001",
        "cad_file_uri": "s3://aeroseat/cad/economy_single_v1.step",
        "uploaded_by": "usr-default-admin-001"
    })
    assert rev_res.status_code == 201
    rev_id = rev_res.json()["id"]

    # 4. Create Simulation Configuration
    sim_cfg_res = client.post("/api/v1/simulation-configurations", json={
        "model_revision_id": rev_id,
        "solver_name": "LSDYNA",
        "solver_version": "R13.1"
    })
    assert sim_cfg_res.status_code == 201
    cfg_id = sim_cfg_res.json()["id"]

    # 5. Run Model QA Gate (Honest status: PASS, WARNING, or PASS_WITH_UNVERIFIED_FE_CHECKS)
    qa_res = client.post(f"/api/v1/simulation-configurations/{cfg_id}/qa")
    assert qa_res.status_code == 200
    assert qa_res.json()["overall_status"] in ["PASS", "WARNING", "PASS_WITH_UNVERIFIED_FE_CHECKS"]

    # 6. Execute Simulation Job
    run_res = client.post(f"/api/v1/simulation-configurations/{cfg_id}/run")
    assert run_res.status_code == 200
    run_data = run_res.json()
    assert "simulation_result" in run_data
    sim_res_id = run_data["simulation_result"]["id"]
    inj_metrics = run_data["injury_metrics"]
    assert inj_metrics["hic15"] > 0
    assert inj_metrics["femur_load_left"] > 0

    # 7. Register Physical Sled Test
    test_res = client.post("/api/v1/physical-tests", json={
        "seat_architecture_id": proj_id,
        "test_facility": "OTEST Sled Facility",
        "raw_data_uri": "s3://aeroseat/tests/otest_16g_test_042.csv"
    })
    assert test_res.status_code == 201
    test_id = test_res.json()["id"]

    # 8. Run Correlation Engine (ARP5765B)
    corr_res = client.post("/api/v1/correlation-runs", params={
        "simulation_result_id": sim_res_id,
        "physical_test_id": test_id
    })
    assert corr_res.status_code == 200
    corr_run_id = corr_res.json()["correlation_run"]["id"]
    assert len(corr_res.json()["correlation_vectors"]) >= 2

    # 9. Credibility Review (Human Engineer Sign-off)
    cred_res = client.post(f"/api/v1/correlation-runs/{corr_run_id}/credibility-review", json={
        "correlation_run_id": corr_run_id,
        "signal_correlation_status": "ACCEPTABLE",
        "model_verification_status": "VERIFIED",
        "overall_assessment": "Simulation acceleration and load curves correlate within allowable ARP5765B corridors.",
        "reviewed_by": "usr-default-admin-001"
    })
    assert cred_res.status_code == 200
    cred_id = cred_res.json()["id"]

    # 10. Engineering Assessment
    assess_res = client.post("/api/v1/engineering-assessments", json={
        "simulation_configuration_id": cfg_id,
        "model_credibility_id": cred_id,
        "overall_readiness": "READY",
        "engineer_comments": "Seat architecture meets 14 CFR § 25.562 16g forward crashworthiness standards.",
        "approved_by": "usr-default-admin-001",
        "approval_role": "CHIEF_CERTIFICATION_ENGINEER"
    })
    assert assess_res.status_code == 201
    assess_id = assess_res.json()["id"]

    # 11. Generate Evidence Artifact & PDF Package
    ev_res = client.post(f"/api/v1/engineering-assessments/{assess_id}/evidence-package")
    assert ev_res.status_code == 200
    artifact = ev_res.json()
    assert artifact["package_pdf_uri"].endswith(".pdf")
    assert len(artifact["input_manifest_sha256"]) == 64
    assert len(artifact["output_manifest_sha256"]) == 64

    # 12. Download Evidence PDF
    art_id = artifact["id"]
    pdf_download = client.get(f"/api/v1/evidence-artifacts/{art_id}/download-pdf")
    assert pdf_download.status_code == 200
    assert pdf_download.headers["content-type"] == "application/pdf"
