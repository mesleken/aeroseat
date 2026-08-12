import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';

export default function ThreeSeatViewer({ deformationProgress = 0, isAnimating = false }) {
  const mountRef = useRef(null);
  const animFrameRef = useRef(null);

  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    const width = container.clientWidth || 500;
    const height = container.clientHeight || 350;

    // Scene, Camera, Renderer
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0a0f1d);

    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    camera.position.set(2.5, 1.8, 3.2);
    camera.lookAt(0, 0.6, 0);

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.shadowMap.enabled = true;

    container.appendChild(renderer.domElement);

    // Grid Floor (Sled Track)
    const gridHelper = new THREE.GridHelper(6, 20, 0x06b6d4, 0x1e293b);
    gridHelper.position.y = 0;
    scene.add(gridHelper);

    // Lights
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.8);
    scene.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0x38bdf8, 1.5);
    dirLight.position.set(5, 8, 5);
    dirLight.castShadow = true;
    scene.add(dirLight);

    const redLight = new THREE.PointLight(0xef4444, 1, 5);
    redLight.position.set(-2, 2, 0);
    scene.add(redLight);

    // Group for the Seat Frame
    const seatGroup = new THREE.Group();
    scene.add(seatGroup);

    // Seat Rail Feet (Fixed 6DOF boundary conditions)
    const railMat = new THREE.MeshStandardMaterial({ color: 0x475569, metalness: 0.8, roughness: 0.2 });
    const rail1 = new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.08, 1.6), railMat);
    rail1.position.set(-0.4, 0.04, 0);
    const rail2 = new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.08, 1.6), railMat);
    rail2.position.set(0.4, 0.04, 0);
    seatGroup.add(rail1);
    seatGroup.add(rail2);

    // Leg Tubes (Tubular Steel/Titanium)
    const tubeMat = new THREE.MeshStandardMaterial({ color: 0x94a3b8, metalness: 0.9, roughness: 0.1 });
    const legFrontL = new THREE.Mesh(new THREE.CylinderGeometry(0.025, 0.025, 0.45), tubeMat);
    legFrontL.position.set(-0.35, 0.265, -0.4);
    const legFrontR = new THREE.Mesh(new THREE.CylinderGeometry(0.025, 0.025, 0.45), tubeMat);
    legFrontR.position.set(0.35, 0.265, -0.4);
    const legBackL = new THREE.Mesh(new THREE.CylinderGeometry(0.025, 0.025, 0.45), tubeMat);
    legBackL.position.set(-0.35, 0.265, 0.3);
    const legBackR = new THREE.Mesh(new THREE.CylinderGeometry(0.025, 0.025, 0.45), tubeMat);
    legBackR.position.set(0.35, 0.265, 0.3);
    seatGroup.add(legFrontL, legFrontR, legBackL, legBackR);

    // Seat Bucket Base (Pan Cushion)
    const panMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, roughness: 0.6 });
    const seatPan = new THREE.Mesh(new THREE.BoxGeometry(0.85, 0.08, 0.75), panMat);
    seatPan.position.set(0, 0.5, -0.05);
    seatPan.rotation.x = -0.08;
    seatGroup.add(seatPan);

    // Backrest Frame & Cushion
    const backrestGroup = new THREE.Group();
    backrestGroup.position.set(0, 0.5, 0.3);
    const backMat = new THREE.MeshStandardMaterial({ color: 0x0f172a, roughness: 0.5 });
    const backrest = new THREE.Mesh(new THREE.BoxGeometry(0.82, 0.85, 0.08), backMat);
    backrest.position.set(0, 0.42, 0);
    backrestGroup.add(backrest);
    seatGroup.add(backrestGroup);

    // Headrest
    const headrestMat = new THREE.MeshStandardMaterial({ color: 0x0284c7, roughness: 0.4 });
    const headrest = new THREE.Mesh(new THREE.BoxGeometry(0.45, 0.22, 0.09), headrestMat);
    headrest.position.set(0, 0.95, 0);
    backrestGroup.add(headrest);

    // Dummy Model (FAA HIII-50M simplified representation)
    const dummyGroup = new THREE.Group();
    dummyGroup.position.set(0, 0.5, 0);
    seatGroup.add(dummyGroup);

    const dummyMat = new THREE.MeshStandardMaterial({ color: 0xf59e0b, roughness: 0.3 }); // Humanetics Amber Dummy Tint

    // Pelvis
    const pelvis = new THREE.Mesh(new THREE.SphereGeometry(0.18, 16, 16), dummyMat);
    pelvis.position.set(0, 0.12, 0.05);
    dummyGroup.add(pelvis);

    // Torso (Spine)
    const torso = new THREE.Mesh(new THREE.CylinderGeometry(0.16, 0.14, 0.48, 16), dummyMat);
    torso.position.set(0, 0.4, 0.05);
    torso.rotation.x = -0.15;
    dummyGroup.add(torso);

    // Head
    const headGroup = new THREE.Group();
    headGroup.position.set(0, 0.72, 0.0);
    const headMesh = new THREE.Mesh(new THREE.SphereGeometry(0.12, 16, 16), dummyMat);
    headGroup.add(headMesh);
    dummyGroup.add(headGroup);

    // Upper Legs (Femurs)
    const femurL = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.05, 0.42), dummyMat);
    femurL.position.set(-0.2, 0.15, -0.22);
    femurL.rotation.x = Math.PI / 2 - 0.1;
    const femurR = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.05, 0.42), dummyMat);
    femurR.position.set(0.2, 0.15, -0.22);
    femurR.rotation.x = Math.PI / 2 - 0.1;
    dummyGroup.add(femurL, femurR);

    // 16g Vector Arrow (Forward Sled Vector)
    const arrowDir = new THREE.Vector3(0, 0, -1);
    const arrowOrigin = new THREE.Vector3(0, 1.4, 1.2);
    const arrowLength = 0.8;
    const arrowHelper = new THREE.ArrowHelper(arrowDir, arrowOrigin, arrowLength, 0x06b6d4, 0.2, 0.12);
    scene.add(arrowHelper);

    // Animation Loop
    let angle = 0;
    const render = () => {
      angle += 0.005;
      camera.position.x = 2.5 * Math.cos(angle * 0.5);
      camera.position.z = 2.5 * Math.sin(angle * 0.5) + 0.8;
      camera.lookAt(0, 0.6, 0);

      // Apply dynamic crash deformation based on deformationProgress prop
      const prog = deformationProgress; // 0.0 to 1.0
      torso.rotation.x = -0.15 - prog * 0.65; // Forward pitch
      headGroup.position.z = -prog * 0.55;   // Head excursion forward
      headGroup.position.y = 0.72 - prog * 0.15;
      backrestGroup.rotation.x = -prog * 0.12; // Structural compliance

      renderer.render(scene, camera);
      animFrameRef.current = requestAnimationFrame(render);
    };

    render();

    return () => {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
      if (container.contains(renderer.domElement)) container.removeChild(renderer.domElement);
    };
  }, [deformationProgress]);

  return (
    <div className="relative w-full h-full min-h-[350px] rounded-xl overflow-hidden border border-slate-800 bg-slate-950">
      <div ref={mountRef} className="w-full h-full" />
      <div className="absolute top-3 left-3 bg-slate-900/80 backdrop-blur-md px-3 py-1.5 rounded-lg border border-slate-800 text-xs font-mono text-cyan-400 flex items-center gap-2">
        <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse"></span>
        3D Interactive FE Mesh & Dummy Visualizer
      </div>
      <div className="absolute bottom-3 right-3 bg-slate-900/80 backdrop-blur-md px-3 py-1.5 rounded-lg border border-slate-800 text-[11px] font-mono text-slate-400">
        Vector: 16g Forward Pulse (-Z)
      </div>
    </div>
  );
}
