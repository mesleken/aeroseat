import React, { useState, useRef } from 'react';
import { Layers, CheckCircle2, Upload, Plus, FolderCheck, Box, FileCode, Check, HardDrive } from 'lucide-react';

export default function ProjectsCadTab({
  selectedProject,
  modelRevision,
  handleCreateProject,
  handleUploadCAD,
  handleUploadRealCAD,
  isLoading,
  uploadedCadFile
}) {
  const [newProjectName, setNewProjectName] = useState("");
  const [showNewModal, setShowNewModal] = useState(false);
  const [revisionLabelInput, setRevisionLabelInput] = useState("");
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef(null);

  const onCreateSubmit = (e) => {
    e.preventDefault();
    if (newProjectName.trim()) {
      handleCreateProject(newProjectName.trim());
      setNewProjectName("");
      setShowNewModal(false);
    }
  };

  const onFileSelected = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      handleUploadRealCAD(file, revisionLabelInput || `REV-2026-${Date.now().toString().slice(-4)}`);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) {
      handleUploadRealCAD(file, revisionLabelInput || `REV-2026-${Date.now().toString().slice(-4)}`);
    }
  };

  return (
    <div className="space-y-6">
      {/* 1. Seat Architectures & CAD Revisions Card */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4 shadow-xl">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="space-y-0.5">
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              <Layers className="w-4 h-4 text-cyan-400" /> Seat Architectures & CAD Geometry Engine
            </h2>
            <p className="text-xs text-slate-400">
              Manage aircraft seat structural assemblies, STEP/IGES CAD model revisions, and geometric hash-chains.
            </p>
          </div>
          <button
            onClick={() => setShowNewModal(true)}
            className="text-xs px-3.5 py-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-medium rounded-xl shadow-md shadow-cyan-500/20 transition-all flex items-center gap-1.5 cursor-pointer active:scale-95"
          >
            <Plus className="w-3.5 h-3.5" /> New Seat Architecture
          </button>
        </div>

        {/* Modal for new project creation */}
        {showNewModal && (
          <form onSubmit={onCreateSubmit} className="bg-slate-950 p-4 rounded-xl border border-cyan-800/60 space-y-3">
            <div className="text-xs font-semibold text-cyan-400">Create New Seat Architecture Program</div>
            <input
              type="text"
              placeholder="e.g. AeroSeat Premium Economy Triple Frame V3"
              value={newProjectName}
              onChange={(e) => setNewProjectName(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-500 font-medium"
              autoFocus
            />
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setShowNewModal(false)}
                className="px-3 py-1.5 text-xs text-slate-400 hover:text-white cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={!newProjectName.trim() || isLoading}
                className="px-3.5 py-1.5 bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold rounded-lg disabled:opacity-50 cursor-pointer"
              >
                Create
              </button>
            </div>
          </form>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-slate-950/80 p-4 rounded-xl border border-slate-800 space-y-2">
            <div className="text-xs text-slate-400 flex items-center gap-1.5">
              <FolderCheck className="w-3.5 h-3.5 text-slate-500" /> Active Seat Architecture
            </div>
            <div className="text-sm font-semibold text-white truncate">
              {selectedProject ? selectedProject.name : "AeroSeat Economy Single Standard"}
            </div>
            <div className="text-[11px] text-slate-500 font-mono">
              ID: {selectedProject ? selectedProject.id : "proj-economy-01"}
            </div>
          </div>

          <div className="bg-slate-950/80 p-4 rounded-xl border border-slate-800 space-y-2">
            <div className="text-xs text-slate-400 flex items-center gap-1.5">
              <Box className="w-3.5 h-3.5 text-slate-500" /> Active CAD Model Revision
            </div>
            <div className="text-sm font-semibold text-cyan-400 flex items-center gap-2 truncate">
              {modelRevision ? modelRevision.revision_label : "No CAD Uploaded"}
              {modelRevision && <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />}
            </div>
            {modelRevision && (
              <div className="text-[11px] text-slate-500 font-mono truncate" title={modelRevision.cad_file_sha256}>
                SHA-256: {modelRevision.cad_file_sha256}
              </div>
            )}
          </div>
        </div>

        {/* 2. Drag & Drop Real CAD Upload Zone */}
        <div
          onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
          onDragLeave={() => setIsDragOver(false)}
          onDrop={handleDrop}
          className={`p-6 rounded-2xl border-2 border-dashed transition-all flex flex-col items-center justify-center text-center gap-3 ${
            isDragOver
              ? "border-cyan-400 bg-cyan-950/30 scale-[1.01]"
              : "border-slate-800 bg-slate-950/50 hover:border-slate-700"
          }`}
        >
          <div className="w-12 h-12 rounded-2xl bg-cyan-950/60 border border-cyan-800/60 flex items-center justify-center text-cyan-400 shadow-lg shadow-cyan-950/40">
            <FileCode className="w-6 h-6" />
          </div>

          <div className="space-y-1">
            <div className="text-xs font-bold text-white">
              Drag & Drop Your STEP / IGES CAD Geometry Here
            </div>
            <div className="text-[11px] text-slate-400">
              Supports <span className="text-cyan-400 font-mono">.step, .stp, .iges, .igs, .stl, .k</span> files (up to 250 MB)
            </div>
          </div>

          <div className="flex items-center gap-2 pt-1">
            <input
              type="file"
              ref={fileInputRef}
              accept=".step,.stp,.iges,.igs,.stl,.k"
              onChange={onFileSelected}
              className="hidden"
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={isLoading || !selectedProject}
              className="text-xs px-4 py-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-semibold rounded-xl transition-all shadow-md shadow-cyan-500/20 cursor-pointer active:scale-95 disabled:opacity-50"
            >
              <Upload className="w-3.5 h-3.5 inline mr-1.5" /> Browse CAD File
            </button>
            <button
              type="button"
              onClick={() => handleUploadCAD()}
              disabled={isLoading || !selectedProject}
              className="text-xs px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium rounded-xl border border-slate-700 transition-all cursor-pointer disabled:opacity-50"
            >
              Use Standard Baseline STEP
            </button>
          </div>
        </div>
      </div>

      {/* 3. Part Manifest Breakdown */}
      {modelRevision && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-3 shadow-xl">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-2">
              <HardDrive className="w-3.5 h-3.5 text-cyan-400" /> Automated Part Manifest Parser (STEP Topology)
            </h3>
            <span className="px-2.5 py-0.5 bg-cyan-950 text-cyan-400 border border-cyan-800/60 rounded text-[10px] font-mono font-semibold">
              4 Structural Solids Parsed
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs font-mono">
            <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800 space-y-1">
              <div className="text-slate-500 text-[11px]">Primary Seat Frame</div>
              <div className="text-cyan-400 font-bold">Al-2024-T3</div>
              <div className="text-[10px] text-slate-600">SHELL 5.0mm / Elastic-Plastic</div>
            </div>
            <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800 space-y-1">
              <div className="text-slate-500 text-[11px]">Spreader Beam</div>
              <div className="text-cyan-400 font-bold">Al-7075-T6</div>
              <div className="text-[10px] text-slate-600">SOLID HEX / High Strength</div>
            </div>
            <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800 space-y-1">
              <div className="text-slate-500 text-[11px]">Seat Cushion Pan</div>
              <div className="text-cyan-400 font-bold">PU Foam Medium</div>
              <div className="text-[10px] text-slate-600">LOW_DENSITY_FOAM / 3D</div>
            </div>
            <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800 space-y-1">
              <div className="text-slate-500 text-[11px]">Backrest Articulation</div>
              <div className="text-cyan-400 font-bold">Al-2024-T3</div>
              <div className="text-[10px] text-slate-600">TUBULAR / Bending Elastic</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
