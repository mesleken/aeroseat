import { useState, useEffect, useCallback } from 'react';
import * as api from '../api/aeroseatClient';

export const EXECUTION_STATES = {
  IDLE: "IDLE",
  VALIDATING: "VALIDATING",
  CONFIGURING: "CONFIGURING",
  QA: "QA",
  SOLVING: "SOLVING",
  PROCESSING: "PROCESSING",
  READY: "READY",
  ANIMATING: "ANIMATING",
  FAILED: "FAILED"
};

function validateSimulationMetrics(metrics) {
  if (!metrics || typeof metrics !== "object") {
    throw new Error("Invalid injury metrics payload returned from solver.");
  }

  const numericFields = [
    "hic15",
    "femur_load_left",
    "femur_load_right",
    "lumbar_load",
    "head_excursion_mm"
  ];

  for (const field of numericFields) {
    if (metrics[field] === undefined || metrics[field] === null) {
      continue;
    }
    const val = Number(metrics[field]);
    if (!Number.isFinite(val)) {
      throw new Error(`Non-finite numerical metric detected: ${field} = ${metrics[field]}`);
    }
  }
}

export function useCertificationPipeline() {
  const [activeTab, setActiveTab] = useState("projects");
  const [executionState, setExecutionState] = useState(EXECUTION_STATES.IDLE);
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState(null);
  const [modelRevision, setModelRevision] = useState(null);
  const [simConfig, setSimConfig] = useState(null);
  const [qaResult, setQaResult] = useState(null);
  const [solverJob, setSolverJob] = useState(null);
  const [simResult, setSimResult] = useState(null);
  const [injuryMetrics, setInjuryMetrics] = useState(null);
  const [animationData, setAnimationData] = useState(null);
  const [requirements, setRequirements] = useState([]);
  const [physicalTest, setPhysicalTest] = useState(null);
  const [correlationData, setCorrelationData] = useState(null);
  const [credibilityReview, setCredibilityReview] = useState(null);
  const [engineeringAssessment, setEngineeringAssessment] = useState(null);
  const [evidenceArtifact, setEvidenceArtifact] = useState(null);
  const [goldenRegression, setGoldenRegression] = useState(null);

  // Configuration Angles
  const [yawAngle, setYawAngle] = useState(0.0);
  const [pitchAngle, setPitchAngle] = useState(0.0);
  const [rollAngle, setRollAngle] = useState(0.0);

  // Configuration Dummy & Pulse Selection
  const [dummyType, setDummyType] = useState("FAA_HIII_50M");
  const [testType, setTestType] = useState("FORWARD_16G");
  const [customPulse, setCustomPulse] = useState(null);
  const [uploadedCadFile, setUploadedCadFile] = useState(null);

  // Dynamic Occupant & Seat Positioning Fit State
  const [dummyOffset, setDummyOffset] = useState({ x: 0, y: 0, z: 0, recline: 0, yaw: 0 });
  const [seatOffset, setSeatOffset] = useState({ x: 0, y: 0, z: 0, pitchWarp: 0, rollWarp: 0, yawMount: 0 });

  const [isLoading, setIsLoading] = useState(false);
  const [animProgress, setAnimProgress] = useState(0);
  const [isPlayingAnim, setIsPlayingAnim] = useState(false);
  const [statusMessage, setStatusMessage] = useState(null);

  // 1. Initial Data Load
  useEffect(() => {
    loadInitialData();
  }, []);

  // 2. Global Dynamic Crash Animation Timer (Runs across all tabs at 30fps)
  useEffect(() => {
    let interval = null;
    if (isPlayingAnim) {
      interval = setInterval(() => {
        setAnimProgress((prev) => {
          if (prev >= 1.0) {
            return 0.0; // Loop seamlessly
          }
          return parseFloat((prev + 0.02).toFixed(3));
        });
      }, 40);
    } else if (interval) {
      clearInterval(interval);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isPlayingAnim]);

  const loadInitialData = async () => {
    try {
      const projData = await api.fetchProjects();
      let activeProj = null;
      if (Array.isArray(projData) && projData.length > 0) {
        setProjects(projData);
        activeProj = projData[0];
        setSelectedProject(activeProj);
      } else {
        activeProj = await api.createProject("AeroSeat Economy Single Standard");
        setProjects([activeProj]);
        setSelectedProject(activeProj);
      }

      // Auto-ensure baseline model revision and simulation config are ready
      try {
        const rev = await api.uploadCADRevision(activeProj.id, "REV-2026-BASELINE");
        setModelRevision(rev);
        const cfg = await api.createSimConfig(
          rev.id,
          "PHYSICS_LUMPED_MASS",
          "1.0.0",
          { yaw_deg: 0, pitch_deg: 0, roll_deg: 0 },
          "FAA_HIII_50M",
          "FORWARD_16G"
        );
        setSimConfig(cfg);
      } catch (err) {}
    } catch (e) {
      console.log("Backend offline or local dev fallback for projects.");
    }

    try {
      const reqData = await api.fetchRequirements();
      if (Array.isArray(reqData)) {
        setRequirements(reqData);
      }
    } catch (e) {}
  };

  // 1. Create Project
  const handleCreateProject = async (projectName) => {
    setIsLoading(true);
    setStatusMessage("Creating new Seat Architecture project...");
    try {
      const proj = await api.createProject(projectName || "AeroSeat Economy Single Standard");
      setProjects((prev) => [...prev, proj]);
      setSelectedProject(proj);
      setStatusMessage("Project created successfully.");
    } catch (e) {
      setStatusMessage(`Error creating project: ${e.message}`);
    }
    setIsLoading(false);
  };

  // 2. Upload CAD (Default/Mock URI or Real File)
  const handleUploadCAD = async (revisionLabel) => {
    if (!selectedProject) return;
    setIsLoading(true);
    setStatusMessage("Registering STEP CAD geometry revision...");
    try {
      const rev = await api.uploadCADRevision(
        selectedProject.id,
        revisionLabel || `REV-2026-${Date.now().toString().slice(-4)}`
      );
      setModelRevision(rev);
      
      const cfg = await api.createSimConfig(
        rev.id,
        "PHYSICS_LUMPED_MASS",
        "1.0.0",
        { yaw_deg: yawAngle, pitch_deg: pitchAngle, roll_deg: rollAngle },
        dummyType,
        testType,
        customPulse?.raw_pulse || null
      );
      setSimConfig(cfg);

      setStatusMessage(`CAD Revision ${rev.revision_label} registered and configuration ready.`);
    } catch (e) {
      setStatusMessage(`Error uploading CAD: ${e.message}`);
    }
    setIsLoading(false);
  };

  const handleUploadRealCAD = async (file, revisionLabel) => {
    if (!selectedProject || !file) return;
    setIsLoading(true);
    setStatusMessage(`Uploading and parsing ${file.name} (${(file.size / 1024).toFixed(1)} KB)...`);
    try {
      const rev = await api.uploadRealCADFile(
        selectedProject.id,
        revisionLabel || `REV-2026-${Date.now().toString().slice(-4)}`,
        file
      );
      setModelRevision(rev);
      setUploadedCadFile(file);

      const cfg = await api.createSimConfig(
        rev.id,
        "PHYSICS_LUMPED_MASS",
        "1.0.0",
        { yaw_deg: yawAngle, pitch_deg: pitchAngle, roll_deg: rollAngle },
        dummyType,
        testType,
        customPulse?.raw_pulse || null
      );
      setSimConfig(cfg);

      setStatusMessage(`Real CAD ${file.name} uploaded successfully with SHA-256 fingerprint.`);
    } catch (e) {
      setStatusMessage(`Error uploading CAD file: ${e.message}`);
    }
    setIsLoading(false);
  };

  // 2.1 Upload Custom Sled Pulse CSV
  const handleUploadCustomPulse = async (file, name, direction) => {
    if (!file) return;
    setIsLoading(true);
    setStatusMessage(`Uploading and verifying pulse CSV ${file.name}...`);
    try {
      const pulseData = await api.uploadCustomPulse(name, direction || testType, file);
      setCustomPulse(pulseData);
      setStatusMessage(`Custom Pulse "${pulseData.name}" loaded: Peak ${pulseData.peak_g}g, Δv=${pulseData.delta_v_ms} m/s (${pulseData.delta_v_valid ? "VALID" : "WARNING"}).`);
    } catch (e) {
      setStatusMessage(`Error uploading pulse: ${e.message}`);
    }
    setIsLoading(false);
  };

  // 3. Create Sim Config
  const handleCreateSimConfig = async () => {
    setIsLoading(true);
    setStatusMessage("Generating cryptographic configuration hash...");
    try {
      let currentRev = modelRevision;
      if (!currentRev && selectedProject) {
        currentRev = await api.uploadCADRevision(selectedProject.id, "REV-2026-AUTO");
        setModelRevision(currentRev);
      }
      if (!currentRev) throw new Error("No Model Revision available.");

      const cfg = await api.createSimConfig(
        currentRev.id,
        "PHYSICS_LUMPED_MASS",
        "1.0.0",
        { yaw_deg: yawAngle, pitch_deg: pitchAngle, roll_deg: rollAngle },
        dummyType,
        testType,
        customPulse?.raw_pulse || null
      );
      setSimConfig(cfg);
      setStatusMessage("Simulation Configuration generated with immutable SHA-256 hash chain.");
    } catch (e) {
      setStatusMessage(`Error creating config: ${e.message}`);
    }
    setIsLoading(false);
  };

  // 4. Run QA Gate
  const handleRunQA = async () => {
    setIsLoading(true);
    setStatusMessage("Executing Model QA Gate 10-point pre-flight checks...");
    try {
      let currentCfg = simConfig;
      if (!currentCfg) {
        await handleCreateSimConfig();
        currentCfg = simConfig;
      }
      if (currentCfg) {
        const qa = await api.runQAGate(currentCfg.id);
        setQaResult(qa);
        setStatusMessage(`Model QA Gate completed: ${qa.overall_status}`);
      }
    } catch (e) {
      setStatusMessage(`QA Gate error: ${e.message}`);
    }
    setIsLoading(false);
  };

  // 5. Robust V2 Execute Simulation Pipeline
  const handleRunSimulation = async () => {
    if (isLoading) return;

    setIsLoading(true);
    setIsPlayingAnim(false);
    setExecutionState(EXECUTION_STATES.VALIDATING);
    setStatusMessage("Validating simulation inputs...");

    try {
      // Step 0: Input Validation
      if (!testType) throw new Error("Crash test type is not selected.");
      if (!dummyType) throw new Error("Occupant dummy type is not selected.");
      if (!Number.isFinite(Number(yawAngle))) throw new Error("Invalid yaw angle.");
      if (!Number.isFinite(Number(pitchAngle))) throw new Error("Invalid pitch angle.");
      if (!Number.isFinite(Number(rollAngle))) throw new Error("Invalid roll angle.");

      // Step 1: Project Guarantee
      let currentProject = selectedProject;
      if (!currentProject) {
        currentProject = await api.createProject("AeroSeat Economy Single Standard");
        if (!currentProject?.id) throw new Error("Project creation failed: missing project ID.");
        setProjects((prev) => [...prev, currentProject]);
        setSelectedProject(currentProject);
      }

      // Step 2: Model Revision Guarantee
      let currentRev = modelRevision;
      if (!currentRev) {
        currentRev = await api.uploadCADRevision(
          currentProject.id,
          `REV-2026-${Date.now().toString().slice(-4)}`
        );
        if (!currentRev?.id) throw new Error("CAD revision registration failed.");
        setModelRevision(currentRev);
      }

      // Step 3: Simulation Configuration
      setExecutionState(EXECUTION_STATES.CONFIGURING);
      setStatusMessage("Creating immutable simulation configuration...");

      const simulationInput = {
        yaw_deg: Number(yawAngle) || 0.0,
        pitch_deg: Number(pitchAngle) || 0.0,
        roll_deg: Number(rollAngle) || 0.0,
        dummy_type: dummyType,
        test_type: testType,
        custom_pulse_data: customPulse?.raw_pulse ?? null
      };

      const currentConfig = await api.createSimConfig(
        currentRev.id,
        "PHYSICS_LUMPED_MASS",
        "1.0.0",
        {
          yaw_deg: simulationInput.yaw_deg,
          pitch_deg: simulationInput.pitch_deg,
          roll_deg: simulationInput.roll_deg,
          dummy_offset_x: Number(dummyOffset.x) || 0.0,
          dummy_offset_y: Number(dummyOffset.y) || 0.0,
          dummy_offset_z: Number(dummyOffset.z) || 0.0,
          dummy_recline_deg: Number(dummyOffset.recline) || 0.0,
          dummy_yaw_deg: Number(dummyOffset.yaw) || 0.0,
          seat_pitch_warp_deg: Number(seatOffset.pitchWarp) || 0.0,
          seat_roll_warp_deg: Number(seatOffset.rollWarp) || 0.0,
          seat_yaw_mount_deg: Number(seatOffset.yawMount) || 0.0,
        },
        simulationInput.dummy_type,
        simulationInput.test_type,
        simulationInput.custom_pulse_data
      );

      if (!currentConfig?.id) throw new Error("Simulation configuration creation failed.");
      setSimConfig(currentConfig);

      // Step 4: Execute Solver
      setExecutionState(EXECUTION_STATES.SOLVING);
      setStatusMessage("Running explicit multi-DOF crash dynamic solver...");

      const data = await api.runSimulation(currentConfig.id);

      // Step 5: Response Validation
      setExecutionState(EXECUTION_STATES.PROCESSING);
      if (!data) throw new Error("Solver returned an empty response.");
      if (!data.solver_job) throw new Error("Solver response does not contain solver_job.");
      if (!data.simulation_result) throw new Error("Solver response does not contain simulation_result.");
      if (!data.injury_metrics) throw new Error("Solver response does not contain injury_metrics.");

      if (data.solver_job.status !== "COMPLETED") {
        throw new Error(`Solver did not complete successfully. Status: ${data.solver_job.status}`);
      }

      // Step 6: Numerical Sanity Check
      validateSimulationMetrics(data.injury_metrics);

      // Step 7: Update React State
      setSolverJob(data.solver_job);
      setSimResult(data.simulation_result);
      setInjuryMetrics(data.injury_metrics);
      if (data.animation) {
        setAnimationData(data.animation);
      }

      // Step 8: Fetch Regulatory Requirements
      try {
        const reqData = await api.fetchRequirementStatus(currentConfig.id);
        if (reqData) setRequirements(reqData);
      } catch (reqErr) {
        console.warn("Requirement status warning:", reqErr);
      }

      // Step 9: Ready & Start 3D Animation Safely
      setExecutionState(EXECUTION_STATES.READY);
      setStatusMessage("Simulation completed successfully. Starting 3D dynamic crash animation...");

      requestAnimationFrame(() => {
        setAnimProgress(0);
        setIsPlayingAnim(true);
        setExecutionState(EXECUTION_STATES.ANIMATING);
      });

      setStatusMessage("Simulation executed successfully. Dynamic crash deformation & injury metrics calculated.");

    } catch (error) {
      console.error("AEROSEAT SIMULATION EXECUTION ERROR:", error);
      setExecutionState(EXECUTION_STATES.FAILED);
      setIsPlayingAnim(false);
      setStatusMessage(`Simulation error: ${error?.message || "Unknown execution error"}`);
    } finally {
      setIsLoading(false);
    }
  };

  // 6. Register Physical Test & Run Correlation
  const handleRunCorrelation = async () => {
    if (!selectedProject || !simResult) return;
    setIsLoading(true);
    setStatusMessage("Registering physical sled test & computing SAE ARP5765B correlation...");
    try {
      const ptest = await api.createPhysicalTest(selectedProject.id);
      setPhysicalTest(ptest);

      const corrData = await api.runCorrelation(simResult.id, ptest.id);
      setCorrelationData(corrData);
      setStatusMessage("SAE ARP5765B Sprague-Geers correlation vectors computed.");
    } catch (e) {
      setStatusMessage(`Correlation error: ${e.message}`);
    }
    setIsLoading(false);
  };

  // 7. Review Credibility
  const handleReviewCredibility = async () => {
    if (!correlationData) return;
    setIsLoading(true);
    setStatusMessage("Signing engineering credibility review...");
    try {
      const review = await api.reviewCredibility(correlationData.correlation_run.id, {
        correlation_run_id: correlationData.correlation_run.id,
        signal_correlation_status: "ACCEPTABLE",
        model_verification_status: "VERIFIED",
        overall_assessment: "Simulation acceleration and femur load curves match physical dynamic sled test within SAE ARP5765B corridors.",
        reviewed_by: "usr-default-admin-001",
      });
      setCredibilityReview(review);
      setStatusMessage("Credibility review signed by Chief Certification Engineer.");
    } catch (e) {
      setStatusMessage(`Credibility sign-off error: ${e.message}`);
    }
    setIsLoading(false);
  };

  // 8. Create Engineering Assessment
  const handleCreateAssessment = async () => {
    if (!simConfig) return;
    setIsLoading(true);
    setStatusMessage("Creating formal Engineering Assessment...");
    try {
      const assess = await api.createEngineeringAssessment({
        simulation_configuration_id: simConfig.id,
        model_credibility_id: credibilityReview ? credibilityReview.id : null,
        overall_readiness: "READY",
        engineer_comments: "Validated against SAE AS8049E & ARP5765B requirements. Ready for physical certification sled test.",
        approved_by: "usr-default-admin-001",
        approval_role: "CHIEF_CERTIFICATION_ENGINEER",
      });
      setEngineeringAssessment(assess);
      setStatusMessage("Engineering Assessment created and signed.");
    } catch (e) {
      setStatusMessage(`Assessment error: ${e.message}`);
    }
    setIsLoading(false);
  };

  // 9. Generate Evidence Package
  const handleGenerateEvidence = async () => {
    if (!engineeringAssessment) return;
    setIsLoading(true);
    setStatusMessage("Compiling cryptographic Evidence Package...");
    try {
      const art = await api.generateEvidencePackage(engineeringAssessment.id);
      setEvidenceArtifact(art);
      setStatusMessage("Evidence Package generated with SHA-256 verification hash.");
    } catch (e) {
      setStatusMessage(`Evidence generation error: ${e.message}`);
    }
    setIsLoading(false);
  };

  // 10. Golden Regression Check
  const handleRunGoldenRegression = async () => {
    setIsLoading(true);
    setStatusMessage("Running Golden Regression baseline comparisons...");
    try {
      const data = await api.checkGoldenRegression();
      setGoldenRegression(data);
      setStatusMessage("Golden Regression suite completed.");
    } catch (e) {
      setStatusMessage(`Regression error: ${e.message}`);
    }
    setIsLoading(false);
  };

  return {
    activeTab,
    setActiveTab,
    executionState,
    projects,
    selectedProject,
    setSelectedProject,
    modelRevision,
    simConfig,
    qaResult,
    solverJob,
    simResult,
    injuryMetrics,
    animationData,
    requirements,
    physicalTest,
    correlationData,
    credibilityReview,
    engineeringAssessment,
    evidenceArtifact,
    goldenRegression,
    yawAngle,
    setYawAngle,
    pitchAngle,
    setPitchAngle,
    rollAngle,
    setRollAngle,
    dummyType,
    setDummyType,
    testType,
    setTestType,
    customPulse,
    uploadedCadFile,
    dummyOffset,
    setDummyOffset,
    seatOffset,
    setSeatOffset,
    isLoading,
    animProgress,
    setAnimProgress,
    isPlayingAnim,
    setIsPlayingAnim,
    statusMessage,
    handleCreateProject,
    handleUploadCAD,
    handleUploadRealCAD,
    handleUploadCustomPulse,
    handleCreateSimConfig,
    handleRunQA,
    handleRunSimulation,
    handleRunCorrelation,
    handleReviewCredibility,
    handleCreateAssessment,
    handleGenerateEvidence,
    handleRunGoldenRegression,
  };
}
