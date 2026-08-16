const API_BASE = "http://localhost:8000/api/v1";

async function request(endpoint, options = {}) {
  try {
    const isFormData = options.body instanceof FormData;
    const headers = isFormData ? { ...options.headers } : { "Content-Type": "application/json", ...options.headers };

    const res = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
    });
    if (!res.ok) {
      let errorDetail = "API request failed";
      try {
        const errorData = await res.json();
        errorDetail = errorData.detail || errorData.message || JSON.stringify(errorData);
      } catch (e) {
        errorDetail = res.statusText;
      }
      throw new Error(`[HTTP ${res.status}] ${errorDetail}`);
    }
    return await res.json();
  } catch (err) {
    console.error(`API Error on ${endpoint}:`, err);
    throw err;
  }
}

export async function fetchProjects() {
  return request("/projects");
}

export async function createProject(name = "AeroSeat Economy Single Standard", customerId = "cust-default-001") {
  return request("/projects", {
    method: "POST",
    body: JSON.stringify({ name, customer_id: customerId }),
  });
}

export async function uploadCADRevision(projectId, revisionLabel = "REV-2026-A1", cadFileUri = "s3://aeroseat/cad/economy_single_frame.step") {
  return request(`/projects/${projectId}/model-revisions`, {
    method: "POST",
    body: JSON.stringify({
      seat_architecture_id: projectId,
      revision_label: revisionLabel,
      cad_file_uri: cadFileUri,
      uploaded_by: "usr-default-admin-001",
    }),
  });
}

export async function uploadRealCADFile(projectId, revisionLabel, file) {
  const formData = new FormData();
  formData.append("revision_label", revisionLabel || `REV-2026-${Date.now().toString().slice(-4)}`);
  formData.append("file", file);

  return request(`/projects/${projectId}/cad-upload`, {
    method: "POST",
    body: formData,
  });
}

export async function uploadCustomPulse(name, direction, file) {
  const formData = new FormData();
  formData.append("name", name || "Custom Dynamic Sled Pulse");
  formData.append("direction", direction || "FORWARD_16G");
  formData.append("file", file);

  return request("/pulse-definitions/upload", {
    method: "POST",
    body: formData,
  });
}

export async function createSimConfig(
  modelRevisionId,
  solverName = "PHYSICS_LUMPED_MASS",
  solverVersion = "1.0.0",
  angles = {},
  dummyType = "FAA_HIII_50M",
  pulseType = "FORWARD_16G",
  customPulseData = null
) {
  return request("/simulation-configurations", {
    method: "POST",
    body: JSON.stringify({
      model_revision_id: modelRevisionId,
      solver_name: solverName,
      solver_version: solverVersion,
      dummy_type: dummyType,
      pulse_type: pulseType,
      custom_pulse_data: customPulseData,
      yaw_deg: angles.yaw_deg || 0.0,
      pitch_deg: angles.pitch_deg || 0.0,
      roll_deg: angles.roll_deg || 0.0,
      dummy_offset_x: angles.dummy_offset_x || 0.0,
      dummy_offset_y: angles.dummy_offset_y || 0.0,
      dummy_offset_z: angles.dummy_offset_z || 0.0,
      dummy_recline_deg: angles.dummy_recline_deg || 0.0,
      dummy_yaw_deg: angles.dummy_yaw_deg || 0.0,
      seat_pitch_warp_deg: angles.seat_pitch_warp_deg || 0.0,
      seat_roll_warp_deg: angles.seat_roll_warp_deg || 0.0,
      seat_yaw_mount_deg: angles.seat_yaw_mount_deg || 0.0,
    }),
  });
}

export async function runQAGate(configId) {
  return request(`/simulation-configurations/${configId}/qa`, {
    method: "POST",
  });
}

export async function runSimulation(configId) {
  return request(`/simulation-configurations/${configId}/run`, {
    method: "POST",
  });
}

export async function fetchRequirementStatus(configId) {
  return request(`/simulation-configurations/${configId}/requirement-status`);
}

export async function fetchRequirements() {
  return request("/requirements");
}

export async function createPhysicalTest(seatArchId, facility = "Accredited Dynamic Sled Facility", dataUri = "s3://aeroseat/physical_tests/dynamic_sled_16g_run04.csv") {
  return request("/physical-tests", {
    method: "POST",
    body: JSON.stringify({
      seat_architecture_id: seatArchId,
      test_facility: facility,
      raw_data_uri: dataUri,
    }),
  });
}

export async function runCorrelation(simResultId, physicalTestId) {
  return request(`/correlation-runs?simulation_result_id=${simResultId}&physical_test_id=${physicalTestId}`, {
    method: "POST",
  });
}

export async function reviewCredibility(correlationRunId, reviewPayload) {
  return request(`/correlation-runs/${correlationRunId}/credibility-review`, {
    method: "POST",
    body: JSON.stringify(reviewPayload),
  });
}

export async function createEngineeringAssessment(assessmentPayload) {
  return request("/engineering-assessments", {
    method: "POST",
    body: JSON.stringify(assessmentPayload),
  });
}

export async function generateEvidencePackage(assessmentId) {
  return request(`/engineering-assessments/${assessmentId}/evidence-package`, {
    method: "POST",
  });
}

export async function checkGoldenRegression() {
  return request("/golden-dataset/regression-check");
}

export { API_BASE };
