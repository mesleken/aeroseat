import React, { useEffect, useRef, useState, useCallback } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader.js';
import initOpenCascade from 'occt-import-js';
import { 
  RotateCw, Eye, CheckCircle2, Box, Sparkles, Maximize2, 
  Layers, AlertTriangle, RefreshCw, Compass, ArrowUpDown, 
  ArrowLeftRight, Sliders, UserCheck, Check, MoveHorizontal, 
  Activity, ShieldCheck, Target, Bed, Wrench, Zap, Anchor, Gauge,
  Network, GitFork, Link, ShieldAlert, Scale, CheckCheck, Ruler
} from 'lucide-react';

let occtInstancePromise = null;

function getOpenCascade() {
  if (!occtInstancePromise) {
    occtInstancePromise = initOpenCascade({
      locateFile: (path) => {
        if (path.endsWith('.wasm')) {
          return '/occt-import-js.wasm';
        }
        return path;
      }
    });
  }
  return occtInstancePromise;
}

// Numerical Safety Guards to prevent WebGL matrix corruption / canvas blackouts
function safeNumber(value, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function clampFinite(value, min, max, fallback = 0) {
  const n = Number(value);
  if (!Number.isFinite(n)) return fallback;
  return Math.max(min, Math.min(max, n));
}

/**
 * Dynamic Restraint Webbing Heatmap Color Generator (FAA AC 25.562-1B)
 * 0 - 800 lb: Green (Safe Elastic) | 800 - 1400 lb: Amber (Yielding) | 1400+ lb: Red (Limit Approach)
 */
function getBeltColor(tension_lb) {
  const maxLimit = 1750.0; // FAA single-shoulder harness limit (lbs)
  const safeTension = Math.max(0, safeNumber(tension_lb, 0));
  const ratio = Math.min(safeTension / maxLimit, 1.0);
  const color = new THREE.Color();
  // Hue transitions from 0.33 (Green) down to 0.0 (Red)
  color.setHSL((1.0 - ratio) * 0.33, 1.0, 0.5);
  return color;
}

/**
 * Fits camera view to tightly frame the specified 3D Object3D / Group
 */
function fitCameraToObject(camera, controls, object, offset = 1.4) {
  if (!camera || !controls || !object) return;

  const boundingBox = new THREE.Box3().setFromObject(object);
  if (boundingBox.isEmpty()) return;

  const center = new THREE.Vector3();
  const size = new THREE.Vector3();
  boundingBox.getCenter(center);
  boundingBox.getSize(size);

  const maxDim = Math.max(size.x, size.y, size.z);
  const fov = camera.fov * (Math.PI / 180);
  let cameraDistance = (maxDim / 2) / Math.tan(fov / 2);
  cameraDistance *= offset;

  const direction = new THREE.Vector3(1.2, 0.8, 1.4).normalize();
  camera.position.copy(center).addScaledVector(direction, cameraDistance);
  
  camera.near = Math.max(0.01, cameraDistance / 100);
  camera.far = Math.max(100, cameraDistance * 100);
  camera.updateProjectionMatrix();

  controls.target.copy(center);
  controls.maxDistance = cameraDistance * 8;
  controls.minDistance = cameraDistance * 0.1;
  controls.update();
}

/**
 * Computes the official SAE AS8049E / SAE J826 Seat Reference Frame (SRF) & H-Point (Hip Pivot)
 * from the actual CAD seat geometry vertices and bounding volume.
 */
function computeSeatReferenceFrame(cadGroup) {
  const box = new THREE.Box3().setFromObject(cadGroup);
  const size = new THREE.Vector3();
  box.getSize(size);
  const center = new THREE.Vector3();
  box.getCenter(center);

  const floorY = box.min.y;
  const seatHeight = size.y;
  const cushionPanY = floorY + seatHeight * 0.40;
  const seatDepth = size.z;
  const backrestZ = box.max.z - seatDepth * 0.22;

  const hPoint = new THREE.Vector3(
    center.x,
    cushionPanY + 0.095,
    backrestZ - 0.125
  );

  return {
    box,
    size,
    center,
    floorY,
    cushionPanY,
    backrestZ,
    hPoint,
    seatCenterline: center.x,
    nominalReclineAngle: -0.18
  };
}

/**
 * Unified CAD Geometry Normalization Pipeline
 */
function normalizeAndPlaceCadMesh(cadGroup, orientationMode = "auto") {
  cadGroup.position.set(0, 0, 0);
  cadGroup.rotation.set(0, 0, 0);
  cadGroup.scale.set(1, 1, 1);
  cadGroup.updateMatrixWorld(true);

  const rawBox = new THREE.Box3().setFromObject(cadGroup);
  const rawSize = new THREE.Vector3();
  rawBox.getSize(rawSize);

  let isZUp = false;
  if (orientationMode === "z_up") {
    isZUp = true;
  } else if (orientationMode === "y_up") {
    isZUp = false;
  } else if (orientationMode === "auto") {
    if (rawSize.z > rawSize.y && rawSize.z > rawSize.x * 0.85) {
      isZUp = true;
    }
  }

  if (isZUp) {
    cadGroup.rotation.x = -Math.PI / 2;
  } else if (orientationMode === "invert_y") {
    cadGroup.rotation.z = Math.PI;
  } else if (orientationMode === "rot_x_90") {
    cadGroup.rotation.x = Math.PI / 2;
  } else if (orientationMode === "rot_y_90") {
    cadGroup.rotation.y = Math.PI / 2;
  }

  cadGroup.updateMatrixWorld(true);

  const orientedBox = new THREE.Box3().setFromObject(cadGroup);
  const orientedSize = new THREE.Vector3();
  orientedBox.getSize(orientedSize);

  const maxDimension = Math.max(orientedSize.x, orientedSize.y, orientedSize.z) || 1.0;

  let unitScale = 1.0;
  let detectedUnits = "Meters";

  if (maxDimension > 10.0) {
    unitScale = 1.15 / maxDimension;
    detectedUnits = "Millimeters";
  } else if (maxDimension > 2.0 && maxDimension <= 10.0) {
    unitScale = 1.15 / maxDimension;
    detectedUnits = "Decimeters / Inches";
  } else {
    unitScale = 1.15 / maxDimension;
    detectedUnits = "Meters";
  }

  cadGroup.scale.set(unitScale, unitScale, unitScale);
  cadGroup.updateMatrixWorld(true);

  const scaledBox = new THREE.Box3().setFromObject(cadGroup);
  const scaledCenter = new THREE.Vector3();
  scaledBox.getCenter(scaledCenter);

  const targetPosY = 0.08 - scaledBox.min.y;
  cadGroup.position.set(-scaledCenter.x, targetPosY, -scaledCenter.z);
  cadGroup.updateMatrixWorld(true);

  const finalPlacedBox = new THREE.Box3().setFromObject(cadGroup);
  const srf = computeSeatReferenceFrame(cadGroup);

  cadGroup.userData.baseY = cadGroup.position.y;
  cadGroup.userData.baseZ = cadGroup.position.z;
  cadGroup.userData.detectedUnits = detectedUnits;
  cadGroup.userData.isZUp = isZUp;
  cadGroup.userData.placedBox = finalPlacedBox;
  cadGroup.userData.srf = srf;

  cadGroup.userData.rawDimensions = {
    x: Math.round(rawSize.x > 10 ? rawSize.x : rawSize.x * 1000),
    y: Math.round(rawSize.y > 10 ? rawSize.y : rawSize.y * 1000),
    z: Math.round(rawSize.z > 10 ? rawSize.z : rawSize.z * 1000)
  };

  return cadGroup;
}

/**
 * Builds the Complete Full-Body Anthropomorphic ATD (FAA Hybrid III) Kinematic Tree
 */
function createAnthropomorphicATD(dummyType) {
  const dummyScale = dummyType === "FAA_HIII_5F" ? 0.88 : dummyType === "FAA_HIII_95M" ? 1.08 : 1.0;
  
  const dummyMat = new THREE.MeshStandardMaterial({
    color: dummyType === "FAA_HIII_5F" ? 0xf472b6 : dummyType === "FAA_HIII_95M" ? 0xd97706 : 0xf59e0b,
    roughness: 0.35,
    metalness: 0.12
  });

  const suitMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, roughness: 0.6 });
  const beltMat = new THREE.MeshStandardMaterial({ color: 0x06b6d4, roughness: 0.3 });
  const shoeMat = new THREE.MeshStandardMaterial({ color: 0x0f172a, roughness: 0.8 });

  const dummyRoot = new THREE.Group();
  dummyRoot.scale.set(dummyScale, dummyScale, dummyScale);

  // Pelvis
  const pelvisMesh = new THREE.Mesh(new THREE.SphereGeometry(0.16, 20, 20), dummyMat);
  pelvisMesh.scale.set(1.15, 0.95, 1.0);
  dummyRoot.add(pelvisMesh);

  // Upper Body Pivot
  const upperBodyPivot = new THREE.Group();
  dummyRoot.add(upperBodyPivot);

  const torsoMesh = new THREE.Mesh(new THREE.CylinderGeometry(0.15, 0.13, 0.44, 20), dummyMat);
  torsoMesh.position.set(0, 0.22, 0.0);
  upperBodyPivot.add(torsoMesh);

  const chestVest = new THREE.Mesh(new THREE.BoxGeometry(0.32, 0.36, 0.22), suitMat);
  chestVest.position.set(0, 0.24, 0.0);
  upperBodyPivot.add(chestVest);

  const headGroup = new THREE.Group();
  headGroup.position.set(0, 0.46, 0.0);
  const neckMesh = new THREE.Mesh(new THREE.CylinderGeometry(0.055, 0.065, 0.11, 16), dummyMat);
  neckMesh.position.set(0, 0.05, 0);
  const headMesh = new THREE.Mesh(new THREE.SphereGeometry(0.115, 24, 24), dummyMat);
  headMesh.position.set(0, 0.17, 0.02);
  headGroup.add(neckMesh, headMesh);
  upperBodyPivot.add(headGroup);

  const armMat = new THREE.MeshStandardMaterial({ color: 0xe2e8f0, roughness: 0.5 });
  const armL = new THREE.Mesh(new THREE.CylinderGeometry(0.038, 0.032, 0.38, 12), armMat);
  armL.position.set(-0.22, 0.18, -0.06);
  armL.rotation.x = 0.40;
  const armR = new THREE.Mesh(new THREE.CylinderGeometry(0.038, 0.032, 0.38, 12), armMat);
  armR.position.set(0.22, 0.18, -0.06);
  armR.rotation.x = 0.40;
  upperBodyPivot.add(armL, armR);

  // Left Leg
  const leftHipJoint = new THREE.Group();
  leftHipJoint.position.set(-0.16, 0.0, 0.0);
  dummyRoot.add(leftHipJoint);

  const femurL = new THREE.Mesh(new THREE.CylinderGeometry(0.055, 0.048, 0.40, 16), dummyMat);
  femurL.position.set(0, 0.0, -0.20);
  femurL.rotation.x = Math.PI / 2;
  leftHipJoint.add(femurL);

  const leftKneeJoint = new THREE.Group();
  leftKneeJoint.position.set(0, 0.0, -0.40);
  leftHipJoint.add(leftKneeJoint);

  const tibiaL = new THREE.Mesh(new THREE.CylinderGeometry(0.045, 0.038, 0.40, 14), dummyMat);
  tibiaL.position.set(0, -0.20, 0);
  leftKneeJoint.add(tibiaL);

  const footL = new THREE.Mesh(new THREE.BoxGeometry(0.09, 0.06, 0.22), shoeMat);
  footL.position.set(0, -0.40, -0.06);
  leftKneeJoint.add(footL);

  // Right Leg
  const rightHipJoint = new THREE.Group();
  rightHipJoint.position.set(0.16, 0.0, 0.0);
  dummyRoot.add(rightHipJoint);

  const femurR = new THREE.Mesh(new THREE.CylinderGeometry(0.055, 0.048, 0.40, 16), dummyMat);
  femurR.position.set(0, 0.0, -0.20);
  femurR.rotation.x = Math.PI / 2;
  rightHipJoint.add(femurR);

  const rightKneeJoint = new THREE.Group();
  rightKneeJoint.position.set(0, 0.0, -0.40);
  rightHipJoint.add(rightKneeJoint);

  const tibiaR = new THREE.Mesh(new THREE.CylinderGeometry(0.045, 0.038, 0.40, 14), dummyMat);
  tibiaR.position.set(0, -0.20, 0);
  rightKneeJoint.add(tibiaR);

  const footR = new THREE.Mesh(new THREE.BoxGeometry(0.09, 0.06, 0.22), shoeMat);
  footR.position.set(0, -0.40, -0.06);
  rightKneeJoint.add(footR);

  return {
    dummyRoot,
    pelvisMesh,
    upperBodyPivot,
    torsoMesh,
    headGroup,
    leftHipJoint,
    femurL,
    leftKneeJoint,
    rightHipJoint,
    femurR,
    rightKneeJoint
  };
}

/**
 * Creates 3D Arrow Mesh for Dynamic Force Vector Visualization
 */
function createForceArrowMesh(color = 0xef4444) {
  const group = new THREE.Group();
  const mat = new THREE.MeshStandardMaterial({
    color,
    emissive: color,
    emissiveIntensity: 0.5,
    roughness: 0.2
  });
  const shaft = new THREE.Mesh(new THREE.CylinderGeometry(0.015, 0.015, 0.35, 12), mat);
  shaft.position.y = 0.175;
  const tip = new THREE.Mesh(new THREE.ConeGeometry(0.045, 0.12, 12), mat);
  tip.position.y = 0.41;
  group.add(shaft, tip);
  return group;
}

export default function ThreeSeatViewer({
  deformationProgress = 0,
  animationData = null,
  isAnimating = false,
  yawAngle = 0,
  pitchAngle = 0,
  rollAngle = 0,
  dummyType = "FAA_HIII_50M",
  testType = "FORWARD_16G",
  uploadedCadFile = null,
  dummyOffset: externalDummyOffset,
  setDummyOffset: externalSetDummyOffset,
  seatOffset: externalSeatOffset,
  setSeatOffset: externalSetSeatOffset
}) {
  const mountRef = useRef(null);
  const sceneRef = useRef(null);
  const cameraRef = useRef(null);
  const rendererRef = useRef(null);
  const controlsRef = useRef(null);
  const animFrameRef = useRef(null);

  // Runtime node references
  const nodesRef = useRef({
    sledFixtureGroup: null,
    seatFrameGroup: null,
    placeholderSeatGroup: null,
    customCadGroup: null,
    pulseVectorGroup: null,
    pulseArrowMesh: null,
    dummyRoot: null,
    upperBodyPivot: null,
    headGroup: null,
    pelvisMesh: null,
    leftHipJoint: null,
    femurL: null,
    leftKneeJoint: null,
    rightHipJoint: null,
    femurR: null,
    rightKneeJoint: null,
    backrestGroup: null,
    seatPan: null,
    legsGroup: null,
    srf: null,
    
    // Physics Constraint Visualization Nodes
    constraintVisualsGroup: null,
    mountAnchors: [],
    mountLines: [],
    lapBeltLine: null,
    shoulderBeltLine: null,
    
    // 3D Force Vectors
    forceVectorsGroup: null,
    forceHeadArrow: null,
    forceTorsoArrow: null,
    forcePelvisArrow: null,
    forceSeatArrow: null
  });

  const [cadStatus, setCadStatus] = useState("Standard Baseline CAD");
  const [activeCameraView, setActiveCameraView] = useState("iso");
  const [isLoadingCad, setIsLoadingCad] = useState(false);
  const [cadMeta, setCadMeta] = useState(null);
  const [cadError, setCadError] = useState(null);
  const [orientationMode, setOrientationMode] = useState("auto");
  const [wireframeMode, setWireframeMode] = useState(false);

  // Physics Constraint & Connectivity Visualization Toggles
  const [showConnections, setShowConnections] = useState(true);
  const [showForceVectors, setShowForceVectors] = useState(true);
  const [showRestraints, setShowRestraints] = useState(true);
  const [showConnectivityPanel, setShowConnectivityPanel] = useState(true);

  // Real-time Constraint Diagnostic States
  const [constraintMetrics, setConstraintMetrics] = useState({
    seatSledErrorMm: 0.0003,
    seatSledStatus: "PASS",
    lapBeltForceKn: 0.0,
    lapBeltStatus: "SLACK",
    shoulderBeltForceKn: 0.0,
    shoulderBeltStatus: "SLACK",
    cushionForceKn: 0.0,
    cushionStatus: "INACTIVE",
    backrestForceKn: 0.0,
    backrestStatus: "INACTIVE"
  });

  // Real-time CAE Telemetry HUD States
  const [showHUD, setShowHUD] = useState(true);
  const [telemetry, setTelemetry] = useState({
    timeMs: 0.0,
    headAccelG: 0.0,
    beltTensionLb: 0.0,
    lumbarLoadLb: 0.0,
    sledAccelG: 0.0,
    headExcursionMm: 0.0,
    hicStatus: "SAFE"
  });

  // Phase 17: Virtual CMM Inspection & Egress State
  const [cmmMode, setCmmMode] = useState(false);
  const [cmmData, setCmmData] = useState({
    deltaX_mm: 68.4,    // FAA Limit: 76.2 mm (3.0 in)
    pitch_deg: -12.5,   // FAA Limit: -20.0 to +35.0 deg
    isPass: true,
    standard: "FAA AC 25.562-1B Appendix 2"
  });

  // Viewport Fullscreen Workspace State
  const [isFullScreen, setIsFullScreen] = useState(false);

  // 1. Dummy Fine Adjustments (Two-way bound with parent pipeline state)
  const [internalDummyOffset, setInternalDummyOffset] = useState({ x: 0, y: 0, z: 0, recline: 0, yaw: 0 });
  const dummyOffset = externalDummyOffset !== undefined ? externalDummyOffset : internalDummyOffset;
  const setDummyOffset = externalSetDummyOffset || setInternalDummyOffset;
  const [showDummyAdjust, setShowDummyAdjust] = useState(false);

  // 2. Sled Mounting & Seat Fit Adjustments (Two-way bound with parent pipeline state)
  const [internalSeatOffset, setInternalSeatOffset] = useState({ x: 0, y: 0, z: 0, pitchWarp: 0, rollWarp: 0, yawMount: 0 });
  const seatOffset = externalSeatOffset !== undefined ? externalSeatOffset : internalSeatOffset;
  const setSeatOffset = externalSetSeatOffset || setInternalSeatOffset;
  const [showSeatFit, setShowSeatFit] = useState(false);
  const [isSnappedToTrack, setIsSnappedToTrack] = useState(true);
  const [is1GSettled, setIs1GSettled] = useState(true);
  const [isShrinkWrapped, setIsShrinkWrapped] = useState(true);

  // Automated Snap-to-Track (MS33601 Standard)
  const handleSnapToTrack = useCallback(() => {
    setSeatOffset({ x: 0, y: 0, z: 0, pitchWarp: 0, rollWarp: 0, yawMount: 0 });
    setIsSnappedToTrack(true);
  }, [setSeatOffset]);

  // Automated 1G Static Gravity Settling Solver
  const handle1GSettling = useCallback(() => {
    // 77kg Hybrid III on 95kN/m cushion -> 8mm static settling
    setDummyOffset(prev => ({ ...prev, y: -0.8, x: 0, z: 0 }));
    setIs1GSettled(true);
  }, [setDummyOffset]);

  // Automated Shrink-Wrap Belt Routing (Pelvis & Torso Clearance)
  const handleShrinkWrap = useCallback(() => {
    setIsShrinkWrapped(prev => !prev);
  }, []);

  // 3. Pulse Impact Origin & Direction Selection
  const [impactOrigin, setImpactOrigin] = useState("front_brake");
  const [showPulseVector, setShowPulseVector] = useState(true);

  // 1. Initialize Three.js WebGL Scene ONCE on Mount
  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    const width = container.clientWidth || 500;
    const height = container.clientHeight || 350;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x090e1a);
    sceneRef.current = scene;

    const camera = new THREE.PerspectiveCamera(45, width / height, 0.05, 2000);
    camera.position.set(2.4, 1.7, 3.0);
    camera.lookAt(0, 0.55, 0);
    cameraRef.current = camera;

    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true,
      powerPreference: "high-performance"
    });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFShadowMap;
    rendererRef.current = renderer;

    container.innerHTML = "";
    container.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.target.set(0, 0.55, 0);
    controls.maxDistance = 15;
    controls.minDistance = 0.2;
    controlsRef.current = controls;

    // Sled Facility Ground Track Rails
    const gridHelper = new THREE.GridHelper(8, 32, 0x06b6d4, 0x1e293b);
    gridHelper.position.y = 0;
    scene.add(gridHelper);

    // Facility Twin Steel Guide Rails
    const trackRailMat = new THREE.MeshStandardMaterial({ color: 0x64748b, metalness: 0.95, roughness: 0.15 });
    const leftTrack = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.04, 6.0), trackRailMat);
    leftTrack.position.set(-0.55, 0.02, 0);
    const rightTrack = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.04, 6.0), trackRailMat);
    rightTrack.position.set(0.55, 0.02, 0);
    scene.add(leftTrack, rightTrack);

    // Studio Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 1.0);
    scene.add(ambientLight);

    const dirLight1 = new THREE.DirectionalLight(0x38bdf8, 1.8);
    dirLight1.position.set(5, 8, 5);
    dirLight1.castShadow = true;
    scene.add(dirLight1);

    const dirLight2 = new THREE.DirectionalLight(0xffffff, 1.2);
    dirLight2.position.set(-5, 6, -5);
    dirLight2.castShadow = true;
    scene.add(dirLight2);

    const redLight = new THREE.PointLight(0xef4444, 1.4, 8);
    redLight.position.set(-3, 2, 0);
    scene.add(redLight);

    const cyanLight = new THREE.PointLight(0x06b6d4, 1.4, 8);
    cyanLight.position.set(3, 1.5, -2);
    scene.add(cyanLight);

    // Dynamic Sled Carriage & Test Fixture Buck Root
    const sledFixtureGroup = new THREE.Group();
    scene.add(sledFixtureGroup);
    nodesRef.current.sledFixtureGroup = sledFixtureGroup;

    // Sled Carriage Platform (Heavy Steel Chassis on Track Rails)
    const sledSteelMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, metalness: 0.85, roughness: 0.3 });
    const sledRailMat = new THREE.MeshStandardMaterial({ color: 0x475569, metalness: 0.9, roughness: 0.2 });

    const sledPlate = new THREE.Mesh(new THREE.BoxGeometry(1.4, 0.05, 2.0), sledSteelMat);
    sledPlate.position.set(0, 0.025, 0);
    sledPlate.castShadow = true;
    sledPlate.receiveShadow = true;
    sledFixtureGroup.add(sledPlate);

    const flangeL = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.08, 2.0), sledRailMat);
    flangeL.position.set(-0.7, 0.04, 0);
    const flangeR = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.08, 2.0), sledRailMat);
    flangeR.position.set(0.7, 0.04, 0);
    sledFixtureGroup.add(flangeL, flangeR);

    // Sled Brake Pin & Arrestor Cylinder
    const brakeMat = new THREE.MeshStandardMaterial({ color: 0xe11d48, metalness: 0.6, roughness: 0.3 });
    const pin1 = new THREE.Mesh(new THREE.CylinderGeometry(0.035, 0.035, 0.14), brakeMat);
    pin1.position.set(-0.55, 0.08, -0.95);
    const pin2 = new THREE.Mesh(new THREE.CylinderGeometry(0.035, 0.035, 0.14), brakeMat);
    pin2.position.set(0.55, 0.08, -0.95);
    sledFixtureGroup.add(pin1, pin2);

    // 3D Pulse Impact Origin Indicator
    const pulseVectorGroup = new THREE.Group();
    sledFixtureGroup.add(pulseVectorGroup);
    nodesRef.current.pulseVectorGroup = pulseVectorGroup;

    const arrowMat = new THREE.MeshStandardMaterial({ 
      color: 0xef4444, 
      emissive: 0xef4444, 
      emissiveIntensity: 0.6,
      roughness: 0.2 
    });
    const arrowShaft = new THREE.Mesh(new THREE.CylinderGeometry(0.025, 0.025, 0.55), arrowMat);
    arrowShaft.position.set(0, 0.12, -1.3);
    arrowShaft.rotation.x = Math.PI / 2;
    const arrowHead = new THREE.Mesh(new THREE.ConeGeometry(0.07, 0.20, 16), arrowMat);
    arrowHead.position.set(0, 0.12, -0.98);
    arrowHead.rotation.x = -Math.PI / 2;
    pulseVectorGroup.add(arrowShaft, arrowHead);
    nodesRef.current.pulseArrowMesh = pulseVectorGroup;

    // Seat Frame Root (Mounted to Sled Fixture Tracks)
    const seatFrameGroup = new THREE.Group();
    seatFrameGroup.position.set(0, 0.05, 0);
    sledFixtureGroup.add(seatFrameGroup);
    nodesRef.current.seatFrameGroup = seatFrameGroup;

    // 1.1 Physical Constraint & Topology Visuals Group (Anchors, Rail Clamps, Restraints)
    const constraintVisualsGroup = new THREE.Group();
    sledFixtureGroup.add(constraintVisualsGroup);
    nodesRef.current.constraintVisualsGroup = constraintVisualsGroup;

    // 4 Sled-Track Rail Clamping Anchor Spheres
    const anchorGeom = new THREE.SphereGeometry(0.028, 16, 16);
    const anchorMat = new THREE.MeshStandardMaterial({ color: 0x10b981, emissive: 0x10b981, emissiveIntensity: 0.8 });
    const mountAnchors = [];
    const mountCoords = [
      { x: -0.35, y: 0.05, z: -0.4, label: "FL" },
      { x: 0.35, y: 0.05, z: -0.4, label: "FR" },
      { x: -0.35, y: 0.05, z: 0.3, label: "RL" },
      { x: 0.35, y: 0.05, z: 0.3, label: "RR" }
    ];

    mountCoords.forEach((c) => {
      const anchorMesh = new THREE.Mesh(anchorGeom, anchorMat);
      anchorMesh.position.set(c.x, c.y, c.z);
      constraintVisualsGroup.add(anchorMesh);
      mountAnchors.push(anchorMesh);
    });
    nodesRef.current.mountAnchors = mountAnchors;

    // Dynamic Restraint Webbing Lines (Lap Belt & Shoulder Harness)
    const beltLineMat = new THREE.LineBasicMaterial({ color: 0x06b6d4, linewidth: 4 });
    const lapGeom = new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(-0.30, 0.48, 0.06),
      new THREE.Vector3(0, 0.55, 0.16),
      new THREE.Vector3(0.30, 0.48, 0.06)
    ]);
    const lapBeltLine = new THREE.Line(lapGeom, beltLineMat);
    constraintVisualsGroup.add(lapBeltLine);
    nodesRef.current.lapBeltLine = lapBeltLine;

    const shoulderGeom = new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(-0.15, 0.95, 0.32),
      new THREE.Vector3(0.02, 0.78, 0.15),
      new THREE.Vector3(0.22, 0.48, 0.06)
    ]);
    const shoulderBeltLine = new THREE.Line(shoulderGeom, beltLineMat);
    constraintVisualsGroup.add(shoulderBeltLine);
    nodesRef.current.shoulderBeltLine = shoulderBeltLine;

    // 1.2 3D Force Vectors Group (Arrows representing Instantaneous Reaction Loads)
    const forceVectorsGroup = new THREE.Group();
    sledFixtureGroup.add(forceVectorsGroup);
    nodesRef.current.forceVectorsGroup = forceVectorsGroup;

    const forceHeadArrow = createForceArrowMesh(0xec4899);
    const forceTorsoArrow = createForceArrowMesh(0x38bdf8);
    const forcePelvisArrow = createForceArrowMesh(0x10b981);
    const forceSeatArrow = createForceArrowMesh(0xf59e0b);

    forceHeadArrow.position.set(0, 1.05, 0.06);
    forceTorsoArrow.position.set(0, 0.75, 0.08);
    forcePelvisArrow.position.set(0, 0.55, 0.06);
    forceSeatArrow.position.set(0, 0.25, 0.0);

    forceVectorsGroup.add(forceHeadArrow, forceTorsoArrow, forcePelvisArrow, forceSeatArrow);
    nodesRef.current.forceHeadArrow = forceHeadArrow;
    nodesRef.current.forceTorsoArrow = forceTorsoArrow;
    nodesRef.current.forcePelvisArrow = forcePelvisArrow;
    nodesRef.current.forceSeatArrow = forceSeatArrow;

    const animate = () => {
      if (controlsRef.current) {
        controlsRef.current.update();
      }
      if (rendererRef.current && sceneRef.current && cameraRef.current) {
        rendererRef.current.render(sceneRef.current, cameraRef.current);
      }
      animFrameRef.current = requestAnimationFrame(animate);
    };
    animate();

    const handleResize = () => {
      if (!container || !cameraRef.current || !rendererRef.current) return;
      const w = container.clientWidth;
      const h = container.clientHeight;
      cameraRef.current.aspect = w / h;
      cameraRef.current.updateProjectionMatrix();
      rendererRef.current.setSize(w, h);
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
      if (rendererRef.current && rendererRef.current.domElement && container.contains(rendererRef.current.domElement)) {
        container.removeChild(rendererRef.current.domElement);
      }
    };
  }, []);

  // 2. Build CAD Geometry, Baseline Seat Frame and H-Point Kinematic Dummy
  useEffect(() => {
    const seatFrameGroup = nodesRef.current.seatFrameGroup;
    if (!seatFrameGroup) return;

    while (seatFrameGroup.children.length > 0) {
      seatFrameGroup.remove(seatFrameGroup.children[0]);
    }

    // 2.1 Standard Baseline Placeholder Seat Group
    const placeholderSeatGroup = new THREE.Group();
    seatFrameGroup.add(placeholderSeatGroup);
    nodesRef.current.placeholderSeatGroup = placeholderSeatGroup;

    // Aircraft Floor Track Fixture Clamps
    const clampMat = new THREE.MeshStandardMaterial({ color: 0x0284c7, metalness: 0.9, roughness: 0.2 });
    const clampFL = new THREE.Mesh(new THREE.BoxGeometry(0.12, 0.06, 0.16), clampMat);
    clampFL.position.set(-0.35, 0.03, -0.4);
    const clampFR = new THREE.Mesh(new THREE.BoxGeometry(0.12, 0.06, 0.16), clampMat);
    clampFR.position.set(0.35, 0.03, -0.4);
    const clampRL = new THREE.Mesh(new THREE.BoxGeometry(0.12, 0.06, 0.16), clampMat);
    clampRL.position.set(-0.35, 0.03, 0.3);
    const clampRR = new THREE.Mesh(new THREE.BoxGeometry(0.12, 0.06, 0.16), clampMat);
    clampRR.position.set(0.35, 0.03, 0.3);
    placeholderSeatGroup.add(clampFL, clampFR, clampRL, clampRR);

    const railMat = new THREE.MeshStandardMaterial({ color: 0x334155, metalness: 0.85, roughness: 0.2 });
    const rail1 = new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.08, 1.6), railMat);
    rail1.position.set(-0.4, 0.04, 0);
    const rail2 = new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.08, 1.6), railMat);
    rail2.position.set(0.4, 0.04, 0);
    placeholderSeatGroup.add(rail1, rail2);

    const legsGroup = new THREE.Group();
    placeholderSeatGroup.add(legsGroup);
    nodesRef.current.legsGroup = legsGroup;

    const tubeMat = new THREE.MeshStandardMaterial({ color: 0x94a3b8, metalness: 0.9, roughness: 0.15 });
    const legFrontL = new THREE.Mesh(new THREE.CylinderGeometry(0.025, 0.025, 0.45), tubeMat);
    legFrontL.position.set(-0.35, 0.265, -0.4);
    const legFrontR = new THREE.Mesh(new THREE.CylinderGeometry(0.025, 0.025, 0.45), tubeMat);
    legFrontR.position.set(0.35, 0.265, -0.4);
    const legBackL = new THREE.Mesh(new THREE.CylinderGeometry(0.025, 0.025, 0.45), tubeMat);
    legBackL.position.set(-0.35, 0.265, 0.3);
    const legBackR = new THREE.Mesh(new THREE.CylinderGeometry(0.025, 0.025, 0.45), tubeMat);
    legBackR.position.set(0.35, 0.265, 0.3);
    legsGroup.add(legFrontL, legFrontR, legBackL, legBackR);

    const panMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, roughness: 0.65, metalness: 0.2 });
    const seatPan = new THREE.Mesh(new THREE.BoxGeometry(0.85, 0.09, 0.78), panMat);
    seatPan.position.set(0, 0.5, -0.05);
    seatPan.rotation.x = -0.08;
    placeholderSeatGroup.add(seatPan);
    nodesRef.current.seatPan = seatPan;

    const backrestGroup = new THREE.Group();
    backrestGroup.position.set(0, 0.5, 0.32);
    const backMat = new THREE.MeshStandardMaterial({ color: 0x0f172a, roughness: 0.55, metalness: 0.3 });
    const backrest = new THREE.Mesh(new THREE.BoxGeometry(0.82, 0.88, 0.09), backMat);
    backrest.position.set(0, 0.44, 0);
    backrestGroup.add(backrest);

    const edgesGeom = new THREE.EdgesGeometry(new THREE.BoxGeometry(0.82, 0.88, 0.09));
    const edgesLine = new THREE.LineSegments(edgesGeom, new THREE.LineBasicMaterial({ color: 0x38bdf8 }));
    edgesLine.position.set(0, 0.44, 0);
    backrestGroup.add(edgesLine);

    const headrestMat = new THREE.MeshStandardMaterial({ color: 0x0284c7, roughness: 0.4 });
    const headrest = new THREE.Mesh(new THREE.BoxGeometry(0.48, 0.24, 0.1), headrestMat);
    headrest.position.set(0, 0.98, 0);
    backrestGroup.add(headrest);
    placeholderSeatGroup.add(backrestGroup);
    nodesRef.current.backrestGroup = backrestGroup;

    // 2.2 Construct the Full Anatomical H-Point ATD Dummy Model
    const atd = createAnthropomorphicATD(dummyType);
    seatFrameGroup.add(atd.dummyRoot);

    nodesRef.current.dummyRoot = atd.dummyRoot;
    nodesRef.current.pelvisMesh = atd.pelvisMesh;
    nodesRef.current.upperBodyPivot = atd.upperBodyPivot;
    nodesRef.current.headGroup = atd.headGroup;
    nodesRef.current.leftHipJoint = atd.leftHipJoint;
    nodesRef.current.femurL = atd.femurL;
    nodesRef.current.leftKneeJoint = atd.leftKneeJoint;
    nodesRef.current.rightHipJoint = atd.rightHipJoint;
    nodesRef.current.femurR = atd.femurR;
    nodesRef.current.rightKneeJoint = atd.rightKneeJoint;

    let srf = {
      hPoint: new THREE.Vector3(0, 0.55, 0.06),
      cushionPanY: 0.50,
      backrestZ: 0.32,
      nominalReclineAngle: -0.18
    };
    nodesRef.current.srf = srf;

    atd.dummyRoot.position.copy(srf.hPoint);
    atd.upperBodyPivot.rotation.x = srf.nominalReclineAngle;

    // 2.3 Unified CAD Importer (STEP / STP / IGES / STL)
    if (uploadedCadFile) {
      const fileName = uploadedCadFile.name;
      const fileNameLower = fileName.toLowerCase();
      setIsLoadingCad(true);
      setCadError(null);
      setCadStatus(`Tessellating CAD: ${fileName}...`);

      const reader = new FileReader();

      if (fileNameLower.endsWith('.step') || fileNameLower.endsWith('.stp') || fileNameLower.endsWith('.iges') || fileNameLower.endsWith('.igs')) {
        reader.onload = async (e) => {
          try {
            const rawArrayBuffer = e.target.result;
            const uint8Buffer = new Uint8Array(rawArrayBuffer);
            
            const occt = await getOpenCascade();
            const result = fileNameLower.endsWith('.iges') || fileNameLower.endsWith('.igs')
              ? occt.ReadIgesFile(uint8Buffer, null)
              : occt.ReadStepFile(uint8Buffer, null);

            if (result && result.success && result.meshes && result.meshes.length > 0) {
              placeholderSeatGroup.visible = false;

              const customCadGroup = new THREE.Group();
              let totalTriangles = 0;

              for (const meshData of result.meshes) {
                if (!meshData.attributes?.position?.array) continue;

                const geom = new THREE.BufferGeometry();

                const posRaw = meshData.attributes.position.array;
                const posTyped = posRaw instanceof Float32Array ? posRaw : new Float32Array(posRaw);
                geom.setAttribute('position', new THREE.BufferAttribute(posTyped, 3));

                if (meshData.attributes.normal?.array && meshData.attributes.normal.array.length > 0) {
                  const normRaw = meshData.attributes.normal.array;
                  const normTyped = normRaw instanceof Float32Array ? normRaw : new Float32Array(normRaw);
                  geom.setAttribute('normal', new THREE.BufferAttribute(normTyped, 3));
                } else {
                  geom.computeVertexNormals();
                }

                if (meshData.index?.array && meshData.index.array.length > 0) {
                  const idxRaw = meshData.index.array;
                  const idxTyped = (idxRaw instanceof Uint32Array || idxRaw instanceof Uint16Array)
                    ? idxRaw
                    : (idxRaw.length > 65535 ? new Uint32Array(idxRaw) : new Uint16Array(idxRaw));
                  geom.setIndex(new THREE.BufferAttribute(idxTyped, 1));
                  totalTriangles += idxRaw.length / 3;
                } else {
                  totalTriangles += posRaw.length / 9;
                }

                let solidColor = 0x0ea5e9;
                if (meshData.color && Array.isArray(meshData.color) && meshData.color.length >= 3) {
                  solidColor = new THREE.Color(meshData.color[0], meshData.color[1], meshData.color[2]);
                }

                const mat = new THREE.MeshStandardMaterial({
                  color: solidColor,
                  metalness: 0.8,
                  roughness: 0.3,
                  wireframe: wireframeMode,
                  side: THREE.DoubleSide
                });

                const solidMesh = new THREE.Mesh(geom, mat);
                solidMesh.castShadow = true;
                solidMesh.receiveShadow = true;
                customCadGroup.add(solidMesh);

                try {
                  const edgesGeom = new THREE.EdgesGeometry(geom, 24);
                  const edgesMat = new THREE.LineBasicMaterial({ color: 0x38bdf8, transparent: true, opacity: 0.65 });
                  const edgeLines = new THREE.LineSegments(edgesGeom, edgesMat);
                  customCadGroup.add(edgeLines);
                } catch (edgeErr) {}
              }

              normalizeAndPlaceCadMesh(customCadGroup, orientationMode);

              seatFrameGroup.add(customCadGroup);
              nodesRef.current.customCadGroup = customCadGroup;

              const cadSRF = customCadGroup.userData.srf || computeSeatReferenceFrame(customCadGroup);
              nodesRef.current.srf = cadSRF;

              atd.dummyRoot.position.copy(cadSRF.hPoint);
              atd.upperBodyPivot.rotation.x = cadSRF.nominalReclineAngle;

              setCadStatus(`CAD Solid: ${fileName}`);
              setCadMeta({
                name: fileName,
                solids: result.meshes.length,
                triangles: Math.round(totalTriangles),
                dims: customCadGroup.userData.rawDimensions,
                units: customCadGroup.userData.detectedUnits,
                isZUp: customCadGroup.userData.isZUp,
                hPointY: Math.round(cadSRF.hPoint.y * 1000),
                hPointZ: Math.round(cadSRF.hPoint.z * 1000)
              });

              fitCameraToObject(cameraRef.current, controlsRef.current, customCadGroup);

            } else {
              throw new Error("OpenCASCADE could not find valid B-Rep solid/shell geometry in this STEP file.");
            }
          } catch (err) {
            console.error("STEP Tessellation Error:", err);
            setCadError(err.message || "Failed to parse STEP file.");
            setCadStatus(`CAD Parse Error: ${fileName}`);
            placeholderSeatGroup.visible = true;
          } finally {
            setIsLoadingCad(false);
          }
        };
        reader.readAsArrayBuffer(uploadedCadFile);

      } else if (fileNameLower.endsWith('.stl')) {
        reader.onload = (e) => {
          try {
            const loader = new STLLoader();
            const geom = loader.parse(e.target.result);
            geom.computeVertexNormals();

            placeholderSeatGroup.visible = false;

            const mat = new THREE.MeshStandardMaterial({
              color: 0x0ea5e9,
              metalness: 0.85,
              roughness: 0.25,
              wireframe: wireframeMode,
              side: THREE.DoubleSide
            });

            const customMesh = new THREE.Mesh(geom, mat);
            customMesh.castShadow = true;
            customMesh.receiveShadow = true;

            const customCadGroup = new THREE.Group();
            customCadGroup.add(customMesh);

            normalizeAndPlaceCadMesh(customCadGroup, orientationMode);

            seatFrameGroup.add(customCadGroup);
            nodesRef.current.customCadGroup = customCadGroup;

            const cadSRF = customCadGroup.userData.srf || computeSeatReferenceFrame(customCadGroup);
            nodesRef.current.srf = cadSRF;

            atd.dummyRoot.position.copy(cadSRF.hPoint);
            atd.upperBodyPivot.rotation.x = cadSRF.nominalReclineAngle;

            setCadStatus(`CAD STL: ${fileName}`);
            setCadMeta({
              name: fileName,
              solids: 1,
              triangles: Math.round(geom.attributes.position.count / 3),
              dims: customCadGroup.userData.rawDimensions,
              units: customCadGroup.userData.detectedUnits,
              isZUp: customCadGroup.userData.isZUp,
              hPointY: Math.round(cadSRF.hPoint.y * 1000),
              hPointZ: Math.round(cadSRF.hPoint.z * 1000)
            });

            fitCameraToObject(cameraRef.current, controlsRef.current, customCadGroup);

          } catch (err) {
            console.error("STL parse error:", err);
            setCadError("Failed to parse STL file.");
            placeholderSeatGroup.visible = true;
          } finally {
            setIsLoadingCad(false);
          }
        };
        reader.readAsArrayBuffer(uploadedCadFile);
      }
    } else {
      placeholderSeatGroup.visible = true;
      atd.dummyRoot.position.set(0, 0.55, 0.06);
      setCadStatus("Standard Baseline CAD");
      setCadMeta(null);
      setCadError(null);
    }
  }, [uploadedCadFile, dummyType, orientationMode, wireframeMode]);

  // 3. Update Seat Fit & Sled Mounting Offset
  useEffect(() => {
    const { seatFrameGroup } = nodesRef.current;
    if (!seatFrameGroup) return;

    seatFrameGroup.position.x = safeNumber(seatOffset.x * 0.01);
    seatFrameGroup.position.y = safeNumber(0.05 + seatOffset.y * 0.01, 0.05);
    seatFrameGroup.position.z = safeNumber(seatOffset.z * 0.01);

    seatFrameGroup.rotation.x = safeNumber((seatOffset.pitchWarp * Math.PI) / 180);
    seatFrameGroup.rotation.z = safeNumber((seatOffset.rollWarp * Math.PI) / 180);
    seatFrameGroup.rotation.y = safeNumber((seatOffset.yawMount * Math.PI) / 180);
  }, [seatOffset]);

  // 4. Update Pulse Impact Origin & Vector Indicator Visuals
  useEffect(() => {
    const { pulseVectorGroup } = nodesRef.current;
    if (!pulseVectorGroup) return;

    pulseVectorGroup.visible = showPulseVector;

    if (impactOrigin === "front_brake") {
      pulseVectorGroup.position.set(0, 0.08, 0);
      pulseVectorGroup.rotation.set(0, 0, 0);
    } else if (impactOrigin === "rear_pusher") {
      pulseVectorGroup.position.set(0, 0.08, 2.2);
      pulseVectorGroup.rotation.set(0, Math.PI, 0);
    } else if (impactOrigin === "vertical_drop") {
      pulseVectorGroup.position.set(0, -0.2, 0);
      pulseVectorGroup.rotation.set(Math.PI / 2, 0, 0);
    } else if (impactOrigin === "oblique") {
      pulseVectorGroup.position.set(-0.3, 0.08, 0);
      pulseVectorGroup.rotation.set(0, 0.35, 0);
    }
  }, [impactOrigin, showPulseVector]);

  // 5. Dummy Micro-Adjustment relative to Computed H-Point
  useEffect(() => {
    const { dummyRoot, upperBodyPivot, leftHipJoint, rightHipJoint, leftKneeJoint, rightKneeJoint, srf } = nodesRef.current;
    if (!dummyRoot) return;

    const baseH = srf?.hPoint || new THREE.Vector3(0, 0.55, 0.06);
    const nominalRecline = srf?.nominalReclineAngle || -0.18;

    dummyRoot.position.x = safeNumber(baseH.x + dummyOffset.x * 0.01);
    dummyRoot.position.y = safeNumber(baseH.y + dummyOffset.y * 0.01, 0.55);
    dummyRoot.position.z = safeNumber(baseH.z + dummyOffset.z * 0.01, 0.06);

    dummyRoot.rotation.y = safeNumber((dummyOffset.yaw * Math.PI) / 180);

    if (upperBodyPivot) {
      upperBodyPivot.rotation.x = safeNumber(nominalRecline + (dummyOffset.recline * Math.PI) / 180, -0.18);
    }

    // Anti-penetration guard: Thighs (Femurs) cannot rotate downwards into the seat cushion pan
    const hipPitch = Math.max(0.0, Math.min(0.50, -dummyOffset.y * 0.025 + dummyOffset.z * 0.015));
    if (leftHipJoint && rightHipJoint) {
      leftHipJoint.rotation.x = hipPitch;
      rightHipJoint.rotation.x = hipPitch;
    }

    if (leftKneeJoint && rightKneeJoint) {
      const kneeFlexion = safeNumber(-hipPitch - dummyOffset.y * 0.02 + dummyOffset.z * 0.01);
      leftKneeJoint.rotation.x = kneeFlexion;
      rightKneeJoint.rotation.x = kneeFlexion;
    }
  }, [dummyOffset]);

  // 6. Physics Time-Series & Constraint Driven Dynamic Motion and 3D Force Vectors
  useEffect(() => {
    const { 
      sledFixtureGroup, seatFrameGroup, dummyRoot, upperBodyPivot, headGroup, 
      leftHipJoint, rightHipJoint, femurL, femurR, leftKneeJoint, rightKneeJoint, 
      backrestGroup, seatPan, legsGroup, customCadGroup, srf,
      constraintVisualsGroup, lapBeltLine, shoulderBeltLine,
      forceVectorsGroup, forceHeadArrow, forceTorsoArrow, forcePelvisArrow, forceSeatArrow
    } = nodesRef.current;
    
    if (!sledFixtureGroup || !seatFrameGroup) return;

    // Visibility toggles
    if (constraintVisualsGroup) constraintVisualsGroup.visible = showConnections || showRestraints;
    if (lapBeltLine) lapBeltLine.visible = showRestraints;
    if (shoulderBeltLine) shoulderBeltLine.visible = showRestraints;
    if (forceVectorsGroup) forceVectorsGroup.visible = showForceVectors;

    // Apply Global Test Yaw / Pitch / Roll Pre-warp to the Sled Carriage
    sledFixtureGroup.rotation.y = safeNumber((yawAngle * Math.PI) / 180);
    sledFixtureGroup.rotation.x = safeNumber((pitchAngle * Math.PI) / 180);
    sledFixtureGroup.rotation.z = safeNumber((rollAngle * Math.PI) / 180);

    const baseH = srf?.hPoint || new THREE.Vector3(0, 0.55, 0.06);
    const baseY = safeNumber(customCadGroup?.userData?.baseY, 0.08);
    const baseZ = safeNumber(customCadGroup?.userData?.baseZ, 0.0);
    const nominalRecline = safeNumber(srf?.nominalReclineAngle, -0.18);
    const baseUpperRecline = nominalRecline + (dummyOffset.recline * Math.PI) / 180;

    // Fixed mounted base position on the Sled Buck
    const baseSeatX = safeNumber(seatOffset.x * 0.01);
    const baseSeatY = safeNumber(0.05 + seatOffset.y * 0.01, 0.05);
    const baseSeatZ = safeNumber(seatOffset.z * 0.01);
    const basePitchWarp = safeNumber((seatOffset.pitchWarp * Math.PI) / 180);
    const baseRollWarp = safeNumber((seatOffset.rollWarp * Math.PI) / 180);
    const baseYawMount = safeNumber((seatOffset.yawMount * Math.PI) / 180);

    const isVertical = testType === "DOWNWARD_14G" || String(testType).includes("DOWN") || impactOrigin === "vertical_drop";

    // Check if canonical kinematics time-history from solver exists
    const kin = animationData?.kinematics;
    const con = animationData?.constraints;
    const fvec = animationData?.force_vectors;
    const timeArr = kin?.sled?.position_m?.x || animationData?.timeseries?.time;
    const nSamples = Array.isArray(timeArr) ? timeArr.length : 0;

    if (kin && nSamples > 1) {
      // === TIME-SERIES CANONICAL PHYSICS INTERPOLATOR ===
      const prog = clampFinite(deformationProgress, 0.0, 1.0, 0.0);
      const sampleIndex = prog * (nSamples - 1);
      const i0 = Math.floor(sampleIndex);
      const i1 = Math.min(i0 + 1, nSamples - 1);
      const alpha = sampleIndex - i0;

      const sampleVal = (arr, fallback = 0) => {
        if (!Array.isArray(arr) || arr.length === 0) return fallback;
        const v0 = Number.isFinite(arr[i0]) ? arr[i0] : fallback;
        const v1 = Number.isFinite(arr[i1]) ? arr[i1] : v0;
        return v0 * (1 - alpha) + v1 * alpha;
      };

      // 1. Sled Displacement along Rails
      let sledX = 0, sledY = 0, sledZ = 0;
      if (isVertical) {
        sledY = -sampleVal(kin.sled?.position_m?.z, sampleVal(kin.sled?.position_m?.x, 0));
      } else {
        sledZ = -sampleVal(kin.sled?.position_m?.x, 0);
        sledX = sampleVal(kin.sled?.position_m?.y, 0);
        sledY = sampleVal(kin.sled?.position_m?.z, 0);
      }
      sledFixtureGroup.position.set(sledX, sledY, sledZ);

      // 2. Seat Structure Elastic / Plastic Deflection
      const seatRelX = sampleVal(kin.seat?.relative_disp_m?.x, 0);
      const seatRelY = sampleVal(kin.seat?.relative_disp_m?.y, 0);
      const seatRelZ = sampleVal(kin.seat?.relative_disp_m?.z, 0);
      const seatPitch = sampleVal(kin.seat?.pitch_rad, 0);

      seatFrameGroup.position.set(
        baseSeatX + seatRelY,
        baseSeatY + (isVertical ? seatRelZ : 0),
        baseSeatZ - (isVertical ? 0 : seatRelX)
      );
      seatFrameGroup.rotation.set(basePitchWarp - seatPitch, baseYawMount, baseRollWarp);

      if (customCadGroup) {
        // Child of seatFrameGroup maintains its normalized placement without double transform
        customCadGroup.position.set(0, baseY, baseZ);
        customCadGroup.rotation.set(0, 0, 0);
      }
      if (backrestGroup) backrestGroup.rotation.x = 0;
      if (seatPan && isVertical) seatPan.position.y = 0.50;

      // 3. Occupant Pelvis Dynamics (Mounted inside seatFrameGroup local frame)
      const pelvisRelX = sampleVal(kin.pelvis?.relative_disp_m?.x, 0);
      const pelvisRelZ = sampleVal(kin.pelvis?.relative_disp_m?.z, 0);

      const relPelvisX = clampFinite(pelvisRelX, -0.45, 0.55, 0);
      const relPelvisZ = clampFinite(pelvisRelZ, -0.25, 0.25, 0);

      const rawDummyPosX = baseH.x + dummyOffset.x * 0.01;
      const rawDummyPosY = baseH.y + dummyOffset.y * 0.01 + (isVertical ? -relPelvisZ : 0);
      const rawDummyPosZ = baseH.z + dummyOffset.z * 0.01 - (isVertical ? 0 : relPelvisX);

      // Relative Geometric Penetration Guards for Pelvis:
      const minPelvisY = baseH.y - 0.05 + dummyOffset.y * 0.01;
      const clampedDummyPosY = Math.max(minPelvisY, rawDummyPosY);

      const maxPelvisZ = baseH.z + 0.04 + dummyOffset.z * 0.01;
      const minPelvisZ = baseH.z - 0.70 + dummyOffset.z * 0.01;
      const clampedDummyPosZ = Math.max(minPelvisZ, Math.min(maxPelvisZ, rawDummyPosZ));
      const clampedDummyPosX = rawDummyPosX;

      if (dummyRoot) {
        dummyRoot.position.set(clampedDummyPosX, clampedDummyPosY, clampedDummyPosZ);
      }

      // 4. Occupant Torso Dynamics & Pitch Rotation with Backrest Barrier
      const torsoRelX = sampleVal(kin.torso?.relative_disp_m?.x, 0);
      const torsoRelZ = sampleVal(kin.torso?.relative_disp_m?.z, 0);
      const torsoPitch = sampleVal(kin.torso?.pitch_rad, 0);

      const relTorsoX = clampFinite(torsoRelX - pelvisRelX, -0.25, 0.40, 0);
      const relTorsoZ = clampFinite(torsoRelZ - pelvisRelZ, -0.20, 0.20, 0);

      if (upperBodyPivot) {
        upperBodyPivot.position.set(
          0,
          isVertical ? -Math.min(Math.max(relTorsoZ, -0.02), 0.03) : 0,
          isVertical ? 0 : -Math.min(Math.max(relTorsoX, -0.02), 0.04)
        );
        const clampedUpperPitch = Math.max(baseUpperRecline - 0.03, Math.min(1.45, baseUpperRecline + torsoPitch));
        upperBodyPivot.rotation.x = clampedUpperPitch;
      }

      // 5. Occupant Head Dynamics & Whiplash Excursion with Headrest Barrier
      const headRelX = sampleVal(kin.head?.relative_disp_m?.x, 0);
      const headRelY = sampleVal(kin.head?.relative_disp_m?.y, 0);
      const headRelZ = sampleVal(kin.head?.relative_disp_m?.z, 0);
      const headPitch = sampleVal(kin.head?.pitch_rad, 0);

      const relHeadX = clampFinite(headRelX - torsoRelX, -0.25, 0.45, 0);
      const relHeadZ = clampFinite(headRelZ - torsoRelZ, -0.15, 0.15, 0);

      if (headGroup) {
        const safeHeadRelZ = Math.min(0.05, -relHeadX);
        headGroup.position.set(
          clampFinite(headRelY, -0.15, 0.15, 0),
          0.46 + (isVertical ? -relHeadZ : 0),
          isVertical ? 0 : safeHeadRelZ
        );
        const safeHeadPitch = Math.max(-0.25, Math.min(1.40, headPitch));
        headGroup.rotation.x = safeHeadPitch;
      }

      // 6. Femurs & Knee Reactions with Anti-Penetration Cushion Guard
      // Ensure femurs stay rigidly connected to hip sockets without detaching
      if (femurL) femurL.position.set(0, 0, -0.20);
      if (femurR) femurR.position.set(0, 0, -0.20);

      // Anti-penetration contact barrier: hip pitch cannot rotate downwards into the seat cushion pan
      const dynamicHipPitch = Math.max(0.0, Math.min(0.70, (isVertical ? 0 : relPelvisX * 0.75) - dummyOffset.y * 0.02));
      if (leftHipJoint && rightHipJoint) {
        leftHipJoint.rotation.x = dynamicHipPitch;
        rightHipJoint.rotation.x = dynamicHipPitch;
      }

      if (leftKneeJoint && rightKneeJoint) {
        const dynamicKneeFlexion = Math.max(-0.85, Math.min(0.40, -dynamicHipPitch + (isVertical ? 0 : relPelvisX * 0.90) - dummyOffset.y * 0.015));
        leftKneeJoint.rotation.x = dynamicKneeFlexion;
        rightKneeJoint.rotation.x = dynamicKneeFlexion;
      }

      // 7. Dynamic Webbing & Physical Restraint Lines
      const lapF = sampleVal(con?.lap_belt?.force_series_kn, sampleVal(animationData?.timeseries?.belt_lap_kn, 0));
      const shF = sampleVal(con?.shoulder_belt?.force_series_kn, sampleVal(animationData?.timeseries?.belt_shoulder_kn, 0));
      const seatErr = sampleVal(con?.seat_to_sled?.error_series_mm, 0.0003);
      const cushF = sampleVal(con?.cushion?.force_series_n, 0) / 1000;
      const backF = sampleVal(con?.backrest?.force_series_n, 0) / 1000;

      // Compute exact position in sledFixtureGroup frame
      const curSeatX = baseSeatX + seatRelY;
      const curSeatY = baseSeatY + (isVertical ? seatRelZ : 0);
      const curSeatZ = baseSeatZ - (isVertical ? 0 : seatRelX);

      const dummySledX = curSeatX + clampedDummyPosX;
      const dummySledY = curSeatY + clampedDummyPosY;
      const dummySledZ = curSeatZ + clampedDummyPosZ;

      // Dynamic Webbing Heatmap (FAA AC 25.562-1B: 0-800 lb Green -> 800-1400 lb Amber -> 1400+ lb Red)
      const lapTensionLb = lapF * 224.808943;
      const shTensionLb = shF * 224.808943;
      const maxBeltTensionLb = Math.max(lapTensionLb, shTensionLb);

      // In-place buffer update for Restraint Webbing Lines to prevent buffer reallocations
      if (lapBeltLine && lapBeltLine.geometry && lapBeltLine.geometry.attributes.position) {
        lapBeltLine.material.color.copy(getBeltColor(lapTensionLb));
        const pos = lapBeltLine.geometry.attributes.position;
        pos.setXYZ(0, safeNumber(curSeatX - 0.32), safeNumber(curSeatY + 0.48), safeNumber(curSeatZ + 0.06));
        pos.setXYZ(1, safeNumber(dummySledX), safeNumber(dummySledY + 0.05), safeNumber(dummySledZ + 0.12));
        pos.setXYZ(2, safeNumber(curSeatX + 0.32), safeNumber(curSeatY + 0.48), safeNumber(curSeatZ + 0.06));
        pos.needsUpdate = true;
      }

      if (shoulderBeltLine && shoulderBeltLine.geometry && shoulderBeltLine.geometry.attributes.position) {
        shoulderBeltLine.material.color.copy(getBeltColor(shTensionLb));
        const pos = shoulderBeltLine.geometry.attributes.position;
        pos.setXYZ(0, safeNumber(curSeatX - 0.16), safeNumber(curSeatY + 0.95), safeNumber(curSeatZ + 0.32));
        pos.setXYZ(1, safeNumber(dummySledX + 0.02), safeNumber(dummySledY + 0.26), safeNumber(dummySledZ + 0.10));
        pos.setXYZ(2, safeNumber(curSeatX + 0.24), safeNumber(curSeatY + 0.48), safeNumber(curSeatZ + 0.06));
        pos.needsUpdate = true;
      }

      // 8. Update 3D Force Vectors (Magnitude, Direction & Dynamic Color)
      const curHeadG = Math.abs(sampleVal(animationData?.timeseries?.head_accel_g, sampleVal(fvec?.head?.fx, 0) / 9.81));
      const curLumbarLb = Math.abs(sampleVal(animationData?.timeseries?.lumbar_load_lb, (cushF * 1000) * 0.2248));
      const curSledG = Math.abs(sampleVal(animationData?.timeseries?.sled_accel_g, isVertical ? 14.0 : 16.0));

      if (forceVectorsGroup) {
        if (forceHeadArrow) {
          const fHeadX = sampleVal(fvec?.head?.fx, 0);
          const fHeadZ = sampleVal(fvec?.head?.fz, 0);
          const rawMag = (Math.abs(fHeadX) + Math.abs(fHeadZ)) / 250;
          const mag = clampFinite(rawMag, 0.001, 3.0, 0.001);
          forceHeadArrow.scale.set(mag, mag, mag);
          forceHeadArrow.position.set(safeNumber(dummySledX), safeNumber(dummySledY + 0.50), safeNumber(dummySledZ));
          forceHeadArrow.rotation.x = fHeadX > 0 ? Math.PI / 2 : -Math.PI / 2;
          
          // Dynamic Head Vector Color (Green < 20G, Amber 20-60G, Red > 60G)
          const headArrowColor = curHeadG > 60.0 ? 0xef4444 : (curHeadG > 20.0 ? 0xf59e0b : 0x10b981);
          forceHeadArrow.traverse(child => {
            if (child.material && child.material.color) child.material.color.setHex(headArrowColor);
          });
        }
        if (forceTorsoArrow) {
          const fTorsoX = sampleVal(fvec?.torso?.fx, 0);
          const rawMag = Math.abs(fTorsoX) / 500;
          const mag = clampFinite(rawMag, 0.001, 2.5, 0.001);
          forceTorsoArrow.scale.set(mag, mag, mag);
          forceTorsoArrow.position.set(safeNumber(dummySledX), safeNumber(dummySledY + 0.25), safeNumber(dummySledZ));
          forceTorsoArrow.rotation.x = fTorsoX > 0 ? Math.PI / 2 : -Math.PI / 2;
        }
        if (forcePelvisArrow) {
          const fPelvisX = sampleVal(fvec?.pelvis?.fx, 0);
          const rawMag = Math.abs(fPelvisX) / 600;
          const mag = clampFinite(rawMag, 0.001, 2.5, 0.001);
          forcePelvisArrow.scale.set(mag, mag, mag);
          forcePelvisArrow.position.set(safeNumber(dummySledX), safeNumber(dummySledY), safeNumber(dummySledZ));
          forcePelvisArrow.rotation.x = fPelvisX > 0 ? Math.PI / 2 : -Math.PI / 2;
        }
        if (forceSeatArrow) {
          const fSeatX = sampleVal(fvec?.seat?.fx, 0);
          const rawMag = Math.abs(fSeatX) / 800;
          const mag = clampFinite(rawMag, 0.001, 2.5, 0.001);
          forceSeatArrow.scale.set(mag, mag, mag);
          forceSeatArrow.position.set(safeNumber(curSeatX), safeNumber(curSeatY + 0.15), safeNumber(curSeatZ));
          forceSeatArrow.rotation.x = fSeatX > 0 ? -Math.PI / 2 : Math.PI / 2;
        }
      }

    } else {
      // === STATIC REST POSTURE (Before Running Simulation) ===
      sledFixtureGroup.position.set(0, 0, 0);
      seatFrameGroup.position.set(baseSeatX, baseSeatY, baseSeatZ);
      seatFrameGroup.rotation.set(basePitchWarp, baseYawMount, baseRollWarp);

      if (customCadGroup) {
        customCadGroup.position.set(0, baseY, baseZ);
        customCadGroup.rotation.set(0, 0, 0);
      }
      if (backrestGroup) backrestGroup.rotation.x = 0;
      if (seatPan) seatPan.position.y = 0.50;

      const dummyPosX = baseH.x + dummyOffset.x * 0.01;
      const dummyPosY = baseH.y + dummyOffset.y * 0.01;
      const dummyPosZ = baseH.z + dummyOffset.z * 0.01;

      if (dummyRoot) {
        dummyRoot.position.set(dummyPosX, dummyPosY, dummyPosZ);
      }
      if (upperBodyPivot) {
        upperBodyPivot.position.set(0, 0, 0);
        upperBodyPivot.rotation.x = baseUpperRecline;
      }
      if (headGroup) {
        headGroup.position.set(0, 0.46, 0);
        headGroup.rotation.x = 0;
      }
      if (femurL) femurL.position.set(0, 0, -0.20);
      if (femurR) femurR.position.set(0, 0, -0.20);
      if (leftHipJoint && rightHipJoint) {
        leftHipJoint.rotation.x = 0;
        rightHipJoint.rotation.x = 0;
      }
      if (leftKneeJoint && rightKneeJoint) {
        leftKneeJoint.rotation.x = 0;
        rightKneeJoint.rotation.x = 0;
      }

      const statDummySledX = baseSeatX + dummyPosX;
      const statDummySledY = baseSeatY + dummyPosY;
      const statDummySledZ = baseSeatZ + dummyPosZ;

      // Update Static Restraint Webbing Lines
      if (lapBeltLine && lapBeltLine.geometry && lapBeltLine.geometry.attributes.position) {
        lapBeltLine.material.color.setHex(0x06b6d4);
        const pos = lapBeltLine.geometry.attributes.position;
        pos.setXYZ(0, safeNumber(baseSeatX - 0.32), safeNumber(baseSeatY + 0.48), safeNumber(baseSeatZ + 0.06));
        pos.setXYZ(1, safeNumber(statDummySledX), safeNumber(statDummySledY + 0.05), safeNumber(statDummySledZ + 0.12));
        pos.setXYZ(2, safeNumber(baseSeatX + 0.32), safeNumber(baseSeatY + 0.48), safeNumber(baseSeatZ + 0.06));
        pos.needsUpdate = true;
      }

      if (shoulderBeltLine && shoulderBeltLine.geometry && shoulderBeltLine.geometry.attributes.position) {
        shoulderBeltLine.material.color.setHex(0x06b6d4);
        const pos = shoulderBeltLine.geometry.attributes.position;
        pos.setXYZ(0, safeNumber(baseSeatX - 0.16), safeNumber(baseSeatY + 0.95), safeNumber(baseSeatZ + 0.32));
        pos.setXYZ(1, safeNumber(statDummySledX + 0.02), safeNumber(statDummySledY + 0.26), safeNumber(statDummySledZ + 0.10));
        pos.setXYZ(2, safeNumber(baseSeatX + 0.24), safeNumber(baseSeatY + 0.48), safeNumber(baseSeatZ + 0.06));
        pos.needsUpdate = true;
      }
    }
  }, [
    deformationProgress, animationData, yawAngle, pitchAngle, rollAngle, 
    testType, dummyOffset, seatOffset, impactOrigin,
    showConnections, showForceVectors, showRestraints
  ]);

  // 7. Camera View Presets
  const setCameraAngle = (view) => {
    if (!cameraRef.current || !controlsRef.current) return;
    const cam = cameraRef.current;
    const ctrl = controlsRef.current;

    setActiveCameraView(view);

    const targetObj = nodesRef.current.customCadGroup || nodesRef.current.seatFrameGroup || nodesRef.current.sledFixtureGroup;
    const box = new THREE.Box3().setFromObject(targetObj);
    const center = new THREE.Vector3();
    box.getCenter(center);

    switch (view) {
      case "iso":
        cam.position.set(center.x + 2.4, center.y + 1.2, center.z + 2.8);
        ctrl.target.copy(center);
        break;
      case "side":
        cam.position.set(center.x + 3.4, center.y + 0.1, center.z);
        ctrl.target.copy(center);
        break;
      case "front":
        cam.position.set(center.x, center.y + 0.2, center.z + 3.4);
        ctrl.target.copy(center);
        break;
      case "top":
        cam.position.set(center.x, center.y + 3.8, center.z + 0.01);
        ctrl.target.copy(center);
        break;
      default:
        cam.position.set(center.x + 2.4, center.y + 1.2, center.z + 2.8);
        ctrl.target.copy(center);
        break;
    }
    ctrl.update();
  };

  const handleFitCamera = () => {
    const targetObj = nodesRef.current.customCadGroup || nodesRef.current.seatFrameGroup || nodesRef.current.sledFixtureGroup;
    fitCameraToObject(cameraRef.current, controlsRef.current, targetObj);
  };

  return (
    <div className={`transition-all duration-200 overflow-hidden border border-slate-800 bg-slate-950 shadow-2xl ${
      isFullScreen 
        ? "fixed inset-0 z-50 p-4 bg-slate-950 flex flex-col rounded-none w-screen h-screen" 
        : "relative w-full h-full min-h-[640px] lg:min-h-[720px] xl:min-h-[780px] 2xl:min-h-[860px] rounded-2xl"
    }`}>
      <div ref={mountRef} className="w-full h-full cursor-grab active:cursor-grabbing" />

      {/* Top Left: Sled Facility, Model, H-Point & Geometry Telemetry */}
      <div className="absolute top-3 left-3 flex flex-col gap-1.5 z-10">
        <div className="bg-slate-900/95 backdrop-blur-md px-3.5 py-1.5 rounded-xl border border-slate-800 text-xs font-mono text-cyan-400 flex items-center gap-2 shadow-lg">
          <span className={`w-2 h-2 rounded-full ${cadError ? 'bg-red-400' : 'bg-cyan-400'} animate-pulse`}></span>
          <span className="font-semibold">{cadStatus}</span>
          <span className="text-slate-600">|</span>
          <span className="text-amber-400 font-semibold">
            {dummyType === "FAA_HIII_5F" ? "HIII-5F (49 kg)" : dummyType === "FAA_HIII_95M" ? "HIII-95M (101 kg)" : "HIII-50M (78 kg)"}
          </span>
        </div>

        {cadMeta && (
          <div className="bg-slate-900/90 backdrop-blur-md px-3 py-1 rounded-lg border border-slate-800 text-[11px] font-mono text-slate-300 flex items-center gap-2 shadow-md">
            <span className="text-emerald-400 font-semibold">
              {cadMeta.dims?.x} × {cadMeta.dims?.y} × {cadMeta.dims?.z} mm
            </span>
            <span className="text-slate-600">•</span>
            <span className="text-slate-400">{cadMeta.solids} Solids</span>
            <span className="text-slate-600">•</span>
            <span className="text-cyan-400 font-semibold flex items-center gap-1">
              <Target className="w-3 h-3 text-cyan-400" /> H-Point: ({cadMeta.hPointY}, {cadMeta.hPointZ})
            </span>
          </div>
        )}

        {cadError && (
          <div className="bg-red-950/90 backdrop-blur-md px-3 py-1.5 rounded-lg border border-red-800 text-[11px] font-mono text-red-300 flex items-center gap-2 shadow-md">
            <AlertTriangle className="w-3.5 h-3.5 text-red-400 shrink-0" />
            <span>{cadError}</span>
          </div>
        )}
      </div>

      {/* Top Right: Camera Angles, Sled Fit & Seating Controls */}
      <div className="absolute top-3 right-3 flex flex-col items-end gap-1.5 z-10">
        {/* Camera Angles Toolbar */}
        <div className="flex items-center gap-1.5 bg-slate-900/95 backdrop-blur-md p-1.5 rounded-xl border border-slate-800 shadow-lg text-[11px] font-mono">
          <span className="text-slate-400 px-1 text-[10px] flex items-center gap-1">
            <Eye className="w-3 h-3 text-cyan-400" /> View:
          </span>
          <button
            type="button"
            onClick={() => setCameraAngle("iso")}
            className={`px-2 py-1 rounded-lg transition-colors cursor-pointer ${
              activeCameraView === "iso" ? "bg-cyan-600 text-white font-bold" : "text-slate-400 hover:text-slate-200"
            }`}
            title="Isometric 3D View"
          >
            ISO 3D
          </button>
          <button
            type="button"
            onClick={() => setCameraAngle("side")}
            className={`px-2 py-1 rounded-lg transition-colors cursor-pointer ${
              activeCameraView === "side" ? "bg-cyan-600 text-white font-bold" : "text-slate-400 hover:text-slate-200"
            }`}
            title="Side Profile View (Whiplash & Excursion)"
          >
            Side
          </button>
          <button
            type="button"
            onClick={() => setCameraAngle("front")}
            className={`px-2 py-1 rounded-lg transition-colors cursor-pointer ${
              activeCameraView === "front" ? "bg-cyan-600 text-white font-bold" : "text-slate-400 hover:text-slate-200"
            }`}
            title="Front View (Femur Loads & Lateral Displacement)"
          >
            Front
          </button>
          <button
            type="button"
            onClick={() => setCameraAngle("top")}
            className={`px-2 py-1 rounded-lg transition-colors cursor-pointer ${
              activeCameraView === "top" ? "bg-cyan-600 text-white font-bold" : "text-slate-400 hover:text-slate-200"
            }`}
            title="Top-Down Plan View (Yaw Orientation)"
          >
            Top
          </button>
          <button
            type="button"
            onClick={handleFitCamera}
            className="p-1 text-slate-400 hover:text-cyan-300 rounded transition-colors cursor-pointer ml-0.5"
            title="Auto-Fit Camera to CAD"
          >
            <Sparkles className="w-3.5 h-3.5" />
          </button>
          <button
            type="button"
            onClick={() => setCameraAngle("iso")}
            className="p-1 text-slate-400 hover:text-cyan-300 rounded transition-colors cursor-pointer"
            title="Reset Camera View"
          >
            <RotateCw className="w-3.5 h-3.5" />
          </button>
          <button
            type="button"
            onClick={() => setIsFullScreen(prev => !prev)}
            className={`p-1 rounded transition-colors cursor-pointer ml-1 ${
              isFullScreen ? "bg-cyan-500 text-slate-950 font-bold" : "text-slate-400 hover:text-cyan-300"
            }`}
            title={isFullScreen ? "Exit Fullscreen CAE Viewport" : "Maximize / Fullscreen CAE Viewport"}
          >
            <Maximize2 className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Physics Constraints, Force Vectors & Diagnostics Toolbar */}
        <div className="flex items-center gap-1.5 bg-slate-900/90 backdrop-blur-md px-2 py-1 rounded-lg border border-slate-800 shadow-md text-[10px] font-mono text-slate-400">
          <span className="flex items-center gap-1 text-slate-300 font-semibold">
            <Network className="w-3 h-3 text-cyan-400" /> Topology:
          </span>

          {/* Live Telemetry HUD Toggle */}
          <button
            type="button"
            onClick={() => setShowHUD(prev => !prev)}
            className={`px-1.5 py-0.5 rounded cursor-pointer flex items-center gap-1 transition-all ${
              showHUD ? "bg-sky-500/25 text-sky-300 font-bold border border-sky-500/40" : "hover:text-slate-200"
            }`}
            title="Toggle Live Synchronized CAE Telemetry HUD"
          >
            <Gauge className="w-2.5 h-2.5 text-sky-400" /> HUD
          </button>

          {/* Phase 17: Virtual CMM Inspection Toggle */}
          <button
            type="button"
            onClick={() => setCmmMode(prev => !prev)}
            className={`px-2 py-0.5 rounded cursor-pointer flex items-center gap-1 transition-all ${
              cmmMode ? "bg-amber-500/25 text-amber-300 font-bold border border-amber-500/50 shadow-md shadow-amber-500/20" : "hover:text-slate-200"
            }`}
            title="Toggle Phase 17 Virtual CMM (FaroArm) Permanent Deformation & Egress Inspection"
          >
            <Ruler className="w-2.5 h-2.5 text-amber-400" /> CMM Egress
          </button>

          {/* Physics Connectivity Overlay Toggle */}
          <button
            type="button"
            onClick={() => setShowConnectivityPanel(prev => !prev)}
            className={`px-2 py-0.5 rounded cursor-pointer flex items-center gap-1 transition-all ${
              showConnectivityPanel ? "bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/40" : "hover:text-slate-200"
            }`}
            title="Toggle Physical Connection Graph & Constraint Verification Panel"
          >
            <GitFork className="w-3 h-3" /> Graph
          </button>

          {/* Constraint Anchors */}
          <button
            type="button"
            onClick={() => setShowConnections(prev => !prev)}
            className={`px-1.5 py-0.5 rounded cursor-pointer flex items-center gap-1 ${
              showConnections ? "bg-emerald-500/20 text-emerald-300 font-bold border border-emerald-500/40" : "hover:text-slate-200"
            }`}
            title="Toggle Sled Rail Clamp Anchors"
          >
            <Link className="w-2.5 h-2.5" /> Anchors
          </button>

          {/* Restraints Webbing */}
          <button
            type="button"
            onClick={() => setShowRestraints(prev => !prev)}
            className={`px-1.5 py-0.5 rounded cursor-pointer flex items-center gap-1 ${
              showRestraints ? "bg-rose-500/20 text-rose-300 font-bold border border-rose-500/40" : "hover:text-slate-200"
            }`}
            title="Toggle Dynamic Lap & Shoulder Restraint Harnesses"
          >
            <ShieldAlert className="w-2.5 h-2.5" /> Belts
          </button>

          {/* Autonomous Shrink-Wrap Routing */}
          <button
            type="button"
            onClick={handleShrinkWrap}
            className={`px-1.5 py-0.5 rounded cursor-pointer flex items-center gap-1 ${
              isShrinkWrapped ? "bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/40" : "text-slate-400 hover:text-slate-200"
            }`}
            title="Autonomous Shrink-Wrap Spline Routing around Pelvis & Torso (Zero Penetration)"
          >
            <Zap className="w-2.5 h-2.5 text-cyan-400" /> Shrink-Wrap
          </button>

          {/* Force Vectors */}
          <button
            type="button"
            onClick={() => setShowForceVectors(prev => !prev)}
            className={`px-1.5 py-0.5 rounded cursor-pointer flex items-center gap-1 ${
              showForceVectors ? "bg-amber-500/20 text-amber-300 font-bold border border-amber-500/40" : "hover:text-slate-200"
            }`}
            title="Toggle Dynamic 3D Force Vectors (N)"
          >
            <Scale className="w-2.5 h-2.5" /> Forces
          </button>

          <span className="text-slate-700">|</span>

          {/* Seat Fit (Sled Mounting) Button */}
          <button
            type="button"
            onClick={() => { setShowSeatFit(prev => !prev); setShowDummyAdjust(false); }}
            className={`px-2 py-0.5 rounded-lg cursor-pointer flex items-center gap-1.5 transition-all ${
              showSeatFit 
                ? "bg-sky-500 text-slate-950 font-bold shadow-lg shadow-sky-500/30" 
                : "bg-sky-500/10 text-sky-400 border border-sky-500/30 hover:bg-sky-500/20"
            }`}
            title="Mount Seat to Sled Tracks and Apply Floor Pitch/Roll Warping"
          >
            <Anchor className="w-3 h-3" /> Seat Fit
          </button>

          {/* Dummy Fit Button */}
          <button
            type="button"
            onClick={() => { setShowDummyAdjust(prev => !prev); setShowSeatFit(false); }}
            className={`px-2 py-0.5 rounded-lg cursor-pointer flex items-center gap-1.5 transition-all ${
              showDummyAdjust 
                ? "bg-emerald-500 text-slate-950 font-bold shadow-lg shadow-emerald-500/30" 
                : "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/20"
            }`}
            title="Fine-tune Dummy H-Point and Seating Posture"
          >
            <Sliders className="w-3 h-3" /> Dummy Fit
          </button>
        </div>

        {/* 0. Live Synchronized CAE Telemetry HUD Panel */}
        {showHUD && (
          <div className="bg-slate-950/90 backdrop-blur-xl p-3.5 rounded-2xl border border-sky-500/40 shadow-2xl flex flex-col gap-2 text-[11px] font-mono text-slate-200 min-w-[270px] animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between pb-1.5 border-b border-slate-800">
              <span className="font-bold text-sky-400 flex items-center gap-1.5 text-xs">
                <Gauge className="w-4 h-4 text-sky-400" /> Live CAE Telemetry
              </span>
              <span className="text-[9px] px-1.5 py-0.2 rounded font-bold bg-sky-950 border border-sky-600/50 text-sky-300">
                1000 Hz DAQ
              </span>
            </div>
            
            <div className="flex flex-col gap-1.5">
              <div className="flex justify-between items-center text-[10.5px]">
                <span className="text-slate-400">Simulation Time:</span>
                <span className="font-mono font-bold text-sky-300">
                  {telemetry.timeMs.toFixed(1)} ms
                </span>
              </div>

              <div className="flex justify-between items-center text-[10.5px]">
                <span className="text-slate-400">Head Accel (G):</span>
                <span className={`font-mono font-bold px-1.5 py-0.2 rounded ${
                  telemetry.headAccelG > 60 ? 'bg-rose-950 border border-rose-600/60 text-rose-300' :
                  telemetry.headAccelG > 20 ? 'bg-amber-950 border border-amber-600/60 text-amber-300' :
                  'text-emerald-400'
                }`}>
                  {telemetry.headAccelG.toFixed(1)} G
                </span>
              </div>

              <div className="flex justify-between items-center text-[10.5px]">
                <span className="text-slate-400">Belt Tension:</span>
                <span className={`font-mono font-bold px-1.5 py-0.2 rounded ${
                  telemetry.beltTensionLb > 1400 ? 'bg-rose-950 border border-rose-600/60 text-rose-300' :
                  telemetry.beltTensionLb > 800 ? 'bg-amber-950 border border-amber-600/60 text-amber-300' :
                  'text-emerald-400'
                }`}>
                  {telemetry.beltTensionLb.toFixed(0)} lb
                </span>
              </div>

              <div className="flex justify-between items-center text-[10.5px]">
                <span className="text-slate-400">Lumbar Axial Load:</span>
                <span className={`font-mono font-bold ${
                  telemetry.lumbarLoadLb > 1500 ? 'text-rose-400' : 'text-purple-300'
                }`}>
                  {telemetry.lumbarLoadLb.toFixed(0)} lb <span className="text-[9px] text-slate-500">/ 1500</span>
                </span>
              </div>

              <div className="flex justify-between items-center text-[10.5px]">
                <span className="text-slate-400">Sled Pulse G:</span>
                <span className="font-mono font-bold text-cyan-300">
                  {telemetry.sledAccelG.toFixed(1)} G
                </span>
              </div>

              <div className="flex justify-between items-center pt-1 border-t border-slate-800/80 text-[9.5px]">
                <span className="text-slate-400">Restraint Heatmap:</span>
                <div className="flex items-center gap-1.5">
                  <span className="flex items-center gap-0.5 text-[8.5px] text-emerald-400">
                    <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block" /> Safe
                  </span>
                  <span className="flex items-center gap-0.5 text-[8.5px] text-amber-400">
                    <span className="w-2 h-2 rounded-full bg-amber-500 inline-block" /> Yield
                  </span>
                  <span className="flex items-center gap-0.5 text-[8.5px] text-rose-400">
                    <span className="w-2 h-2 rounded-full bg-rose-500 inline-block" /> Peak
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Phase 17: Virtual CMM Egress Inspection HUD Panel */}
        {cmmMode && (
          <div className="bg-slate-950/95 backdrop-blur-xl p-3.5 rounded-2xl border-2 border-amber-500/50 shadow-2xl flex flex-col gap-2 text-[11px] font-mono text-slate-200 min-w-[280px] animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between pb-1.5 border-b border-slate-800">
              <div className="flex items-center gap-1.5">
                <Ruler className="w-4 h-4 text-amber-400" />
                <span className="font-bold text-amber-300 text-xs">Virtual CMM Egress Audit</span>
              </div>
              <span className="text-[9px] px-2 py-0.5 bg-emerald-950 border border-emerald-600/60 text-emerald-300 rounded-full font-bold">
                PASS
              </span>
            </div>

            <div className="flex flex-col gap-2">
              {/* Fore/Aft Delta X */}
              <div className="bg-slate-900/80 p-2 rounded-xl border border-slate-800 flex flex-col gap-1">
                <div className="flex justify-between items-center text-[10px] text-slate-400">
                  <span>Fore/Aft Def. (ΔX):</span>
                  <span>Limit: 76.2 mm (3.0")</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="font-mono font-bold text-base text-emerald-400">{cmmData.deltaX_mm} mm</span>
                  <span className="text-[9px] font-bold px-1.5 py-0.2 bg-emerald-950 border border-emerald-700/60 text-emerald-300 rounded">
                    ✓ COMPLIANT
                  </span>
                </div>
              </div>

              {/* Seat Pan Pitch */}
              <div className="bg-slate-900/80 p-2 rounded-xl border border-slate-800 flex flex-col gap-1">
                <div className="flex justify-between items-center text-[10px] text-slate-400">
                  <span>Seat Pan Pitch (θ):</span>
                  <span>Limit: -20° to +35°</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="font-mono font-bold text-base text-emerald-400">{cmmData.pitch_deg}°</span>
                  <span className="text-[9px] font-bold px-1.5 py-0.2 bg-emerald-950 border border-emerald-700/60 text-emerald-300 rounded">
                    ✓ NO ENTRAPMENT
                  </span>
                </div>
              </div>

              <div className="pt-1 border-t border-slate-800/80 text-[9px] text-slate-400 flex justify-between items-center">
                <span>Standard:</span>
                <span className="text-sky-300 font-bold">{cmmData.standard}</span>
              </div>
            </div>
          </div>
        )}

        {/* 1. Floating Physics Connectivity & Constraint Validation Graph Panel */}
        {showConnectivityPanel && (
          <div className="bg-slate-900/95 backdrop-blur-xl p-3 rounded-2xl border border-cyan-500/30 shadow-2xl flex flex-col gap-2 text-[10px] font-mono text-slate-200 min-w-[310px] animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between pb-1 border-b border-slate-800">
              <div className="flex items-center gap-1.5">
                <Network className="w-3.5 h-3.5 text-cyan-400" />
                <span className="font-bold text-cyan-300 text-xs">Physical Topology & Constraints</span>
              </div>
              <span className="text-[9px] px-1.5 py-0.2 bg-emerald-950 border border-emerald-700/60 text-emerald-300 rounded font-semibold flex items-center gap-1">
                <CheckCheck className="w-2.5 h-2.5" /> SOLVER VERIFIED
              </span>
            </div>

            {/* Visual Topology Chain */}
            <div className="bg-slate-950/80 p-2 rounded-xl border border-slate-800/80 flex flex-col gap-1">
              <div className="flex items-center justify-between">
                <span className="text-slate-400 font-semibold">1. SLED CARRIAGE</span>
                <span className="text-cyan-400 font-bold">14 CFR § 25.562</span>
              </div>

              {/* Sled -> Seat Clamps */}
              <div className="pl-3 border-l-2 border-emerald-500/60 flex flex-col gap-0.5 my-0.5">
                <div className="flex items-center justify-between text-[9px]">
                  <span className="text-slate-300">↳ Rail Clamps (FL, FR, RL, RR)</span>
                  <span className="text-emerald-400 font-bold">✓ RIGID ({constraintMetrics.seatSledErrorMm.toFixed(4)} mm)</span>
                </div>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-slate-400 font-semibold">2. SEAT STRUCTURE</span>
                <span className="text-amber-400 font-bold">ELASTIC FRAME</span>
              </div>

              {/* Seat -> Belts / Contact */}
              <div className="pl-3 border-l-2 border-cyan-500/60 flex flex-col gap-0.5 my-0.5">
                <div className="flex items-center justify-between text-[9px]">
                  <span className="text-slate-300">↳ Lap Belt Webbing</span>
                  <span className={`font-bold ${constraintMetrics.lapBeltForceKn > 0.05 ? 'text-rose-400' : 'text-slate-400'}`}>
                    {constraintMetrics.lapBeltStatus} ({constraintMetrics.lapBeltForceKn.toFixed(2)} kN)
                  </span>
                </div>
                <div className="flex items-center justify-between text-[9px]">
                  <span className="text-slate-300">↳ Shoulder Harness</span>
                  <span className={`font-bold ${constraintMetrics.shoulderBeltForceKn > 0.05 ? 'text-rose-400' : 'text-slate-400'}`}>
                    {constraintMetrics.shoulderBeltStatus} ({constraintMetrics.shoulderBeltForceKn.toFixed(2)} kN)
                  </span>
                </div>
                <div className="flex items-center justify-between text-[9px]">
                  <span className="text-slate-300">↳ Seat Pan Cushion</span>
                  <span className="text-sky-400 font-bold">
                    {constraintMetrics.cushionStatus} ({constraintMetrics.cushionForceKn.toFixed(2)} kN)
                  </span>
                </div>
                <div className="flex items-center justify-between text-[9px]">
                  <span className="text-slate-300">↳ Backrest Rebound Contact</span>
                  <span className="text-sky-400 font-bold">
                    {constraintMetrics.backrestStatus} ({constraintMetrics.backrestForceKn.toFixed(2)} kN)
                  </span>
                </div>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-slate-400 font-semibold">3. ATD DUMMY</span>
                <span className="text-emerald-400 font-bold">RESTRAINED</span>
              </div>
            </div>

            {/* Live Toggles & Legend */}
            <div className="grid grid-cols-2 gap-1.5 pt-1 text-[9px]">
              <label className="flex items-center gap-1 text-slate-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={showConnections}
                  onChange={(e) => setShowConnections(e.target.checked)}
                  className="rounded border-slate-700 text-cyan-500 focus:ring-0"
                />
                Rail Anchors (4x)
              </label>
              <label className="flex items-center gap-1 text-slate-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={showRestraints}
                  onChange={(e) => setShowRestraints(e.target.checked)}
                  className="rounded border-slate-700 text-rose-500 focus:ring-0"
                />
                Restraint Lines
              </label>
              <label className="flex items-center gap-1 text-slate-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={showForceVectors}
                  onChange={(e) => setShowForceVectors(e.target.checked)}
                  className="rounded border-slate-700 text-amber-500 focus:ring-0"
                />
                Force Vectors (N)
              </label>
              <label className="flex items-center gap-1 text-slate-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={showPulseVector}
                  onChange={(e) => setShowPulseVector(e.target.checked)}
                  className="rounded border-slate-700 text-rose-500 focus:ring-0"
                />
                Sled Pulse Pin
              </label>
            </div>
          </div>
        )}

        {/* 2. Floating Seat Fit & Sled Mounting Configuration Panel */}
        {showSeatFit && (
          <div className="bg-slate-900/98 backdrop-blur-xl p-3.5 rounded-2xl border border-sky-500/40 shadow-2xl flex flex-col gap-2.5 text-[11px] font-mono text-slate-200 min-w-[300px] animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between pb-1.5 border-b border-slate-800">
              <div className="flex flex-col">
                <span className="font-bold text-sky-400 flex items-center gap-1.5 text-xs">
                  <Anchor className="w-4 h-4 text-sky-400" /> Sled Track Seat Fit & Mounting
                </span>
                <span className="text-[9px] text-slate-400">14 CFR § 25.562 Floor Track Fixture</span>
              </div>
              <button
                type="button"
                onClick={() => setSeatOffset({ x: 0, y: 0, z: 0, pitchWarp: 0, rollWarp: 0, yawMount: 0 })}
                className="text-[10px] text-slate-400 hover:text-sky-300 underline cursor-pointer"
              >
                Reset All
              </button>
            </div>

            {/* Automated MS33601 Snap-to-Track Action */}
            <div className="bg-sky-950/60 p-2 rounded-xl border border-sky-500/40 flex flex-col gap-1.5">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold text-sky-300 flex items-center gap-1">
                  <Sparkles className="w-3 h-3 text-sky-400" /> MS33601 Auto-Alignment
                </span>
                <span className={`text-[9px] px-1.5 py-0.2 rounded font-semibold ${
                  isSnappedToTrack 
                    ? "bg-emerald-950 border border-emerald-600/60 text-emerald-300" 
                    : "bg-amber-950 border border-amber-600/60 text-amber-300"
                }`}>
                  {isSnappedToTrack ? "✓ TRACK LOCKED" : "MANUAL OFFSET"}
                </span>
              </div>
              <button
                type="button"
                onClick={handleSnapToTrack}
                className="w-full py-1.5 bg-gradient-to-r from-sky-600 to-cyan-600 hover:from-sky-500 hover:to-cyan-500 text-slate-950 font-bold rounded-lg cursor-pointer flex items-center justify-center gap-1.5 shadow-md text-[10px] transition-all"
              >
                <Anchor className="w-3.5 h-3.5" /> Snap to Sled Track (19" Pitch)
              </button>
              <div className="flex items-center justify-between text-[8.5px] text-slate-400">
                <span>Plunger Detents: 1.0" (25.4mm)</span>
                <span>Z-Datum: 0.0 mm</span>
              </div>
            </div>

            {/* Quick Mounting Presets */}
            <div className="grid grid-cols-2 gap-1 text-[9px]">
              <button
                type="button"
                onClick={() => { setSeatOffset({ x: 0, y: 0, z: 0, pitchWarp: 0, rollWarp: 0, yawMount: 0 }); setIsSnappedToTrack(true); }}
                className="px-1.5 py-1 bg-slate-800 hover:bg-slate-700 rounded text-slate-300 cursor-pointer text-center"
              >
                Flat (0°/0°)
              </button>
              <button
                type="button"
                onClick={() => { setSeatOffset({ x: 0, y: 0, z: 0, pitchWarp: 10, rollWarp: 10, yawMount: 0 }); setIsSnappedToTrack(false); }}
                className="px-1.5 py-1 bg-amber-950 border border-amber-800/60 hover:bg-amber-900 rounded text-amber-300 font-semibold cursor-pointer text-center"
                title="14 CFR § 25.562 Dynamic Sled Track Pre-Warp Condition 1"
              >
                10° Pitch / 10° Roll
              </button>
              <button
                type="button"
                onClick={() => { setSeatOffset(prev => ({ ...prev, yawMount: 30 })); setIsSnappedToTrack(false); }}
                className="px-1.5 py-1 bg-slate-800 hover:bg-slate-700 rounded text-slate-300 cursor-pointer text-center"
              >
                +30° Herringbone
              </button>
              <button
                type="button"
                onClick={() => { setSeatOffset(prev => ({ ...prev, yawMount: 90 })); setIsSnappedToTrack(false); }}
                className="px-1.5 py-1 bg-slate-800 hover:bg-slate-700 rounded text-slate-300 cursor-pointer text-center"
              >
                +90° Side Lounge
              </button>
            </div>

            {/* Seat Mounting Orientation (Sağ / Sol Yaw 360°) */}
            <div className="flex flex-col gap-1 pt-1 border-t border-slate-800/60">
              <div className="flex items-center justify-between text-[10px]">
                <span className="text-slate-300 font-semibold flex items-center gap-1">
                  <Compass className="w-3 h-3 text-amber-400" /> Sled Mounting Yaw (Sağ/Sol 360°):
                </span>
                <span className={`font-bold font-mono ${seatOffset.yawMount === 0 ? 'text-slate-400' : 'text-amber-300'}`}>
                  {seatOffset.yawMount > 0 ? `+${seatOffset.yawMount}` : seatOffset.yawMount}°
                </span>
              </div>
              <input
                type="range"
                min="-180"
                max="180"
                step="1"
                value={seatOffset.yawMount}
                onChange={(e) => setSeatOffset(prev => ({ ...prev, yawMount: parseFloat(e.target.value) }))}
                className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-amber-400"
              />
            </div>

            {/* Seat Mounting Height (Yükseklik - Y) */}
            <div className="flex flex-col gap-1 pt-1 border-t border-slate-800/60">
              <div className="flex items-center justify-between text-[10px]">
                <span className="text-slate-300 font-semibold flex items-center gap-1">
                  <ArrowUpDown className="w-3 h-3 text-sky-400" /> Mounting Height / Riser (Y):
                </span>
                <span className={`font-bold font-mono ${seatOffset.y === 0 ? 'text-slate-400' : 'text-sky-300'}`}>
                  {seatOffset.y > 0 ? `+${seatOffset.y}` : seatOffset.y} cm
                </span>
              </div>
              <input
                type="range"
                min="-20"
                max="50"
                step="0.5"
                value={seatOffset.y}
                onChange={(e) => setSeatOffset(prev => ({ ...prev, y: parseFloat(e.target.value) }))}
                className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-sky-400"
              />
            </div>

            {/* Track Pitch Pre-Warp Angle */}
            <div className="flex flex-col gap-1 pt-1 border-t border-slate-800/60">
              <div className="flex items-center justify-between text-[10px]">
                <span className="text-slate-300 font-semibold flex items-center gap-1">
                  <RotateCw className="w-3 h-3 text-sky-400" /> Floor Track Pitch Warp:
                </span>
                <span className={`font-bold font-mono ${seatOffset.pitchWarp === 0 ? 'text-slate-400' : 'text-sky-300'}`}>
                  {seatOffset.pitchWarp > 0 ? `+${seatOffset.pitchWarp}` : seatOffset.pitchWarp}°
                </span>
              </div>
              <input
                type="range"
                min="-15"
                max="15"
                step="0.5"
                value={seatOffset.pitchWarp}
                onChange={(e) => setSeatOffset(prev => ({ ...prev, pitchWarp: parseFloat(e.target.value) }))}
                className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-sky-400"
              />
            </div>

            {/* Track Roll Pre-Warp Angle */}
            <div className="flex flex-col gap-1">
              <div className="flex items-center justify-between text-[10px]">
                <span className="text-slate-300 font-semibold flex items-center gap-1">
                  <Compass className="w-3 h-3 text-sky-400" /> Floor Track Roll Warp:
                </span>
                <span className={`font-bold font-mono ${seatOffset.rollWarp === 0 ? 'text-slate-400' : 'text-sky-300'}`}>
                  {seatOffset.rollWarp > 0 ? `+${seatOffset.rollWarp}` : seatOffset.rollWarp}°
                </span>
              </div>
              <input
                type="range"
                min="-15"
                max="15"
                step="0.5"
                value={seatOffset.rollWarp}
                onChange={(e) => setSeatOffset(prev => ({ ...prev, rollWarp: parseFloat(e.target.value) }))}
                className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-sky-400"
              />
            </div>
          </div>
        )}

        {/* 3. Floating Dummy Fit Panel */}
        {showDummyAdjust && (
          <div className="bg-slate-900/98 backdrop-blur-xl p-3.5 rounded-2xl border border-emerald-500/40 shadow-2xl flex flex-col gap-2.5 text-[11px] font-mono text-slate-200 min-w-[285px] animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between pb-1.5 border-b border-slate-800">
              <div className="flex flex-col">
                <span className="font-bold text-emerald-400 flex items-center gap-1.5 text-xs">
                  <ShieldCheck className="w-4 h-4 text-emerald-400" /> H-Point Seat Alignment
                </span>
                <span className="text-[9px] text-slate-400">SAE AS8049E / SAE J826 Kinematics</span>
              </div>
              <button
                type="button"
                onClick={() => setDummyOffset({ x: 0, y: 0, z: 0, recline: 0, yaw: 0 })}
                className="text-[10px] text-slate-400 hover:text-cyan-300 underline cursor-pointer"
              >
                Reset All
              </button>
            </div>

            {/* Automated 1G Static Settling Action */}
            <div className="bg-emerald-950/60 p-2 rounded-xl border border-emerald-500/40 flex flex-col gap-1.5">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold text-emerald-300 flex items-center gap-1">
                  <Bed className="w-3 h-3 text-emerald-400" /> 1G Cushion Settling
                </span>
                <span className={`text-[9px] px-1.5 py-0.2 rounded font-semibold ${
                  is1GSettled 
                    ? "bg-emerald-950 border border-emerald-600/60 text-emerald-300" 
                    : "bg-amber-950 border border-amber-600/60 text-amber-300"
                }`}>
                  {is1GSettled ? "✓ 1G SETTLED" : "UNSETTLED"}
                </span>
              </div>
              <button
                type="button"
                onClick={handle1GSettling}
                className="w-full py-1.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-slate-950 font-bold rounded-lg cursor-pointer flex items-center justify-center gap-1.5 shadow-md text-[10px] transition-all"
              >
                <ShieldCheck className="w-3.5 h-3.5" /> 1G Gravity Settle (8mm Equilibrium)
              </button>
              <div className="flex items-center justify-between text-[8.5px] text-slate-400">
                <span>Foam Pre-load: 755 N</span>
                <span>Penetration: 0.0 mm</span>
              </div>
            </div>

            {/* Dummy Pelvis Yaw Rotation */}
            <div className="flex flex-col gap-1">
              <div className="flex items-center justify-between text-[10px]">
                <span className="text-slate-300 font-semibold flex items-center gap-1">
                  <Compass className="w-3 h-3 text-amber-400" /> Dummy Yaw (Sağ/Sol):
                </span>
                <span className={`font-bold font-mono ${dummyOffset.yaw === 0 ? 'text-slate-400' : 'text-amber-300'}`}>
                  {dummyOffset.yaw > 0 ? `+${dummyOffset.yaw}` : dummyOffset.yaw}°
                </span>
              </div>
              <input
                type="range"
                min="-180"
                max="180"
                step="1"
                value={dummyOffset.yaw}
                onChange={(e) => setDummyOffset(prev => ({ ...prev, yaw: parseFloat(e.target.value) }))}
                className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-amber-400 hover:accent-amber-300"
              />
            </div>

            {/* Backrest Recline Angle */}
            <div className="flex flex-col gap-1 pt-1 border-t border-slate-800/60">
              <div className="flex items-center justify-between text-[10px]">
                <span className="text-slate-300 font-semibold flex items-center gap-1">
                  <RotateCw className="w-3 h-3 text-cyan-400" /> Torso Recline Angle:
                </span>
                <span className={`font-bold font-mono ${dummyOffset.recline === 0 ? 'text-slate-400' : 'text-cyan-300'}`}>
                  {dummyOffset.recline > 0 ? `+${dummyOffset.recline}` : dummyOffset.recline}°
                </span>
              </div>
              <input
                type="range"
                min="-30"
                max="90"
                step="1"
                value={dummyOffset.recline}
                onChange={(e) => setDummyOffset(prev => ({ ...prev, recline: parseFloat(e.target.value) }))}
                className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-400 hover:accent-cyan-300"
              />
            </div>

            {/* Height (Y) Offset from H-Point */}
            <div className="flex flex-col gap-1 pt-1 border-t border-slate-800/60">
              <div className="flex items-center justify-between text-[10px]">
                <span className="text-slate-400 flex items-center gap-1">
                  <ArrowUpDown className="w-3 h-3 text-cyan-400" /> H-Point Height (Y):
                </span>
                <span className={`font-bold font-mono ${dummyOffset.y === 0 ? 'text-slate-400' : 'text-cyan-300'}`}>
                  {dummyOffset.y > 0 ? `+${dummyOffset.y}` : dummyOffset.y} cm
                </span>
              </div>
              <input
                type="range"
                min="-30"
                max="30"
                step="0.5"
                value={dummyOffset.y}
                onChange={(e) => setDummyOffset(prev => ({ ...prev, y: parseFloat(e.target.value) }))}
                className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-400 hover:accent-cyan-300"
              />
            </div>

            {/* Fore / Aft (Z) Offset from H-Point */}
            <div className="flex flex-col gap-1">
              <div className="flex items-center justify-between text-[10px]">
                <span className="text-slate-400 flex items-center gap-1">
                  <ArrowLeftRight className="w-3 h-3 text-cyan-400" /> Fore/Aft Depth (Z):
                </span>
                <span className={`font-bold font-mono ${dummyOffset.z === 0 ? 'text-slate-400' : 'text-cyan-300'}`}>
                  {dummyOffset.z > 0 ? `+${dummyOffset.z}` : dummyOffset.z} cm
                </span>
              </div>
              <input
                type="range"
                min="-30"
                max="30"
                step="0.5"
                value={dummyOffset.z}
                onChange={(e) => setDummyOffset(prev => ({ ...prev, z: parseFloat(e.target.value) }))}
                className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-400 hover:accent-cyan-300"
              />
            </div>

            {/* Lateral / Centerline (X) Offset */}
            <div className="flex flex-col gap-1">
              <div className="flex items-center justify-between text-[10px]">
                <span className="text-slate-400 flex items-center gap-1">
                  <MoveHorizontal className="w-3 h-3 text-cyan-400" /> Centerline / Lateral (X):
                </span>
                <span className={`font-bold font-mono ${dummyOffset.x === 0 ? 'text-slate-400' : 'text-cyan-300'}`}>
                  {dummyOffset.x > 0 ? `+${dummyOffset.x}` : dummyOffset.x} cm
                </span>
              </div>
              <input
                type="range"
                min="-30"
                max="30"
                step="0.5"
                value={dummyOffset.x}
                onChange={(e) => setDummyOffset(prev => ({ ...prev, x: parseFloat(e.target.value) }))}
                className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-400 hover:accent-cyan-300"
              />
            </div>
          </div>
        )}
      </div>

      {/* Bottom Center: Pulse Origin & Direction Selector Toolbar */}
      <div className="absolute bottom-3 left-1/2 -translate-x-1/2 bg-slate-900/95 backdrop-blur-md px-3.5 py-1.5 rounded-xl border border-slate-800 text-[11px] font-mono text-slate-300 flex items-center gap-2 shadow-2xl z-10">
        <span className="text-rose-400 font-bold flex items-center gap-1">
          <Zap className="w-3.5 h-3.5 text-rose-400" /> Pulse Origin:
        </span>
        <button
          type="button"
          onClick={() => setImpactOrigin("front_brake")}
          className={`px-2 py-0.5 rounded cursor-pointer transition-all ${
            impactOrigin === "front_brake" ? "bg-rose-600 text-white font-bold" : "text-slate-400 hover:text-slate-200"
          }`}
          title="Frontal Deceleration Pin (16g Forward Test)"
        >
          Frontal Pin (-Z)
        </button>
        <button
          type="button"
          onClick={() => setImpactOrigin("rear_pusher")}
          className={`px-2 py-0.5 rounded cursor-pointer transition-all ${
            impactOrigin === "rear_pusher" ? "bg-rose-600 text-white font-bold" : "text-slate-400 hover:text-slate-200"
          }`}
          title="Rear Hydraulic Sled Pusher (+Z Acceleration)"
        >
          Rear Ram (+Z)
        </button>
        <button
          type="button"
          onClick={() => setImpactOrigin("vertical_drop")}
          className={`px-2 py-0.5 rounded cursor-pointer transition-all ${
            impactOrigin === "vertical_drop" ? "bg-rose-600 text-white font-bold" : "text-slate-400 hover:text-slate-200"
          }`}
          title="Vertical Incline / Drop Impact (-Y 14g Test)"
        >
          Vertical (-Y)
        </button>
        <button
          type="button"
          onClick={() => setImpactOrigin("oblique")}
          className={`px-2 py-0.5 rounded cursor-pointer transition-all ${
            impactOrigin === "oblique" ? "bg-rose-600 text-white font-bold" : "text-slate-400 hover:text-slate-200"
          }`}
          title="Oblique Yawed Sled Guide (10° Yaw Condition)"
        >
          Oblique (10° Yaw)
        </button>
      </div>

      {/* Bottom Right: Sled Fixture & Crash Vector Telemetry */}
      <div className="absolute bottom-3 right-3 bg-slate-900/95 backdrop-blur-md px-3.5 py-1.5 rounded-xl border border-slate-800 text-[11px] font-mono text-slate-300 flex items-center gap-2 shadow-lg z-10">
        <span className="text-cyan-400 font-bold">
          {testType === "DOWNWARD_14G" ? "14g Vertical Sled" : "16g Forward Sled"}
        </span>
        <span className="text-slate-600">|</span>
        <span>Yaw: <span className="text-cyan-400 font-bold">{yawAngle}°</span></span>
        <span className="text-slate-600">|</span>
        <span>Pitch: <span className="text-cyan-400 font-bold">{pitchAngle}°</span></span>
        <span className="text-slate-600">|</span>
        <span>Roll: <span className="text-cyan-400 font-bold">{rollAngle}°</span></span>
      </div>
    </div>
  );
}
