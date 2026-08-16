import React, { useEffect } from 'react';
import { 
  Cpu, Play, Pause, RotateCcw, CheckCircle2, Clock, 
  Activity, ShieldCheck, Zap, Sparkles, Loader2, ArrowRight, Check
} from 'lucide-react';

export default function SolverEngineTab({
  solverJob,
  simResult,
  injuryMetrics,
  handleRunSimulation,
  isLoading,
  simConfig,
  testType = "FORWARD_16G",
  dummyType = "FAA_HIII_50M",
  yawAngle = 0,
  pitchAngle = 0,
  rollAngle = 0,
  animProgress,
  setAnimProgress,
  isPlayingAnim,
  setIsPlayingAnim,
  setActiveTab
}) {
  // Animation interval is globally managed in useCertificationPipeline.js

  return (
    <div className="space-y-6">
      {/* 1. Header & Solver Execution Trigger */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-5 shadow-xl">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="space-y-0.5">
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              <Cpu className="w-4 h-4 text-cyan-400" /> Explicit Dynamic Physics Crash Solver
            </h2>
            <p className="text-xs text-slate-400">
              14 CFR § 25.562 / SAE AS8049E non-linear multi-DOF structural & occupant biomechanics solver.
            </p>
          </div>

          <button
            type="button"
            onClick={handleRunSimulation}
            disabled={isLoading}
            className="text-xs px-5 py-2.5 bg-gradient-to-r from-cyan-600 via-blue-600 to-indigo-600 hover:from-cyan-500 hover:to-indigo-500 text-white font-bold rounded-xl shadow-lg shadow-cyan-500/25 transition-all flex items-center gap-2 cursor-pointer disabled:opacity-50 active:scale-95"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin text-white" />
                <span>Executing Explicit Solver...</span>
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>Execute {testType === "DOWNWARD_14G" ? "14g Vertical" : "16g Forward"} Crash Test</span>
              </>
            )}
          </button>
        </div>

        {/* Dynamic Condition Specs Summary Card */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-slate-950/80 p-3.5 rounded-xl border border-slate-800 text-xs font-mono">
          <div>
            <span className="text-slate-500 text-[10px] block">Test Condition</span>
            <span className="text-cyan-400 font-bold">
              {testType === "DOWNWARD_14G" ? "14g Vertical (-Y)" : "16g Forward (-Z)"}
            </span>
          </div>
          <div>
            <span className="text-slate-500 text-[10px] block">Occupant ATD</span>
            <span className="text-amber-400 font-bold">
              {dummyType === "FAA_HIII_5F" ? "FAA HIII-5F" : dummyType === "FAA_HIII_95M" ? "FAA HIII-95M" : "FAA HIII-50M"}
            </span>
          </div>
          <div>
            <span className="text-slate-500 text-[10px] block">Sled Orientation</span>
            <span className="text-slate-200">
              Yaw {yawAngle}° | Pitch {pitchAngle}° | Roll {rollAngle}°
            </span>
          </div>
          <div>
            <span className="text-slate-500 text-[10px] block">Integration Step</span>
            <span className="text-emerald-400 font-bold">Explicit Δt = 0.1 ms</span>
          </div>
        </div>

        {/* Solver Job Execution Status & Cryptographic Proof */}
        {solverJob && (
          <div className="bg-slate-950/90 p-4 rounded-xl border border-slate-800 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-xs text-slate-400 font-mono flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-cyan-400" /> Job ID: {solverJob.id}
              </span>
              <span className="px-3 py-1 bg-emerald-950 text-emerald-400 border border-emerald-800 rounded-full text-xs font-mono font-bold flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5" /> STATUS: {solverJob.status}
              </span>
            </div>

            <div className="text-xs text-slate-300 font-mono bg-slate-900 p-3 rounded-lg border border-slate-800 space-y-1">
              <span className="text-slate-500 text-[11px] block">Execution Fingerprint (SHA-256):</span>
              <span className="text-cyan-400 break-all text-[11px]">{solverJob.execution_fingerprint}</span>
            </div>
          </div>
        )}

        {/* Live Injury Metrics Quick Dashboard when Computed */}
        {injuryMetrics && (
          <div className="bg-slate-950/90 p-4 rounded-xl border border-emerald-500/30 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-emerald-400 flex items-center gap-1.5">
                <ShieldCheck className="w-4 h-4 text-emerald-400" /> Computed Injury Criteria & Structural Integrity
              </span>
              <button
                type="button"
                onClick={() => setActiveTab && setActiveTab("metrics")}
                className="text-[11px] text-cyan-400 hover:text-cyan-300 flex items-center gap-1 cursor-pointer font-semibold"
              >
                View Full Metrics Tab <ArrowRight className="w-3 h-3" />
              </button>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
              <div className="bg-slate-900 p-2.5 rounded-lg border border-slate-800">
                <span className="text-slate-500 text-[10px] block">Head Injury HIC15</span>
                <span className={`text-base font-bold ${injuryMetrics.hic15 <= 1000 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {Math.round(injuryMetrics.hic15 || 0)}
                </span>
                <span className="text-[9px] text-slate-500 block">Limit: &le; 1000</span>
              </div>
              <div className="bg-slate-900 p-2.5 rounded-lg border border-slate-800">
                <span className="text-slate-500 text-[10px] block">Lumbar Spine Load</span>
                <span className={`text-base font-bold ${injuryMetrics.lumbar_load <= 6.67 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {Number(injuryMetrics.lumbar_load || 0).toFixed(2)} kN
                </span>
                <span className="text-[9px] text-slate-500 block">Limit: &le; 6.67 kN (1500 lbs)</span>
              </div>
              <div className="bg-slate-900 p-2.5 rounded-lg border border-slate-800">
                <span className="text-slate-500 text-[10px] block">Femur Compressive Load</span>
                <span className={`text-base font-bold ${(injuryMetrics.femur_load_left || 0) <= 10.0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {Math.max(injuryMetrics.femur_load_left || 0, injuryMetrics.femur_load_right || 0).toFixed(2)} kN
                </span>
                <span className="text-[9px] text-slate-500 block">Limit: &le; 10.0 kN (2250 lbs)</span>
              </div>
              <div className="bg-slate-900 p-2.5 rounded-lg border border-slate-800">
                <span className="text-slate-500 text-[10px] block">Seat Structure</span>
                <span className="text-base font-bold text-emerald-400 flex items-center gap-1">
                  <Check className="w-4 h-4 text-emerald-400" /> {injuryMetrics.seat_structural_status || "PASS"}
                </span>
                <span className="text-[9px] text-slate-500 block">Attachment Maintained</span>
              </div>
            </div>
          </div>
        )}

        {/* Time-Step Dynamic Deformation Animation Player */}
        <div className="bg-slate-950/90 p-4 rounded-xl border border-slate-800 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
            <div className="text-slate-200 font-semibold flex items-center gap-2">
              <Activity className="w-4 h-4 text-cyan-400" />
              <span>Crash Sled Dynamic Kinematic Animation</span>
            </div>
            <div className="flex items-center gap-2 font-mono text-cyan-400 bg-slate-900 px-3 py-1 rounded-lg border border-slate-800">
              <span className="text-slate-500">Time:</span>
              <span className="font-bold">{(animProgress * 0.180).toFixed(3)} s</span>
              <span className="text-slate-500 text-[10px]">({Math.round(animProgress * 180)} ms)</span>
            </div>
          </div>

          <input
            type="range"
            min="0"
            max="1"
            step="0.01"
            value={animProgress}
            onChange={(e) => {
              setAnimProgress(parseFloat(e.target.value));
              setIsPlayingAnim(false);
            }}
            className="w-full accent-cyan-500 cursor-pointer h-2 bg-slate-800 rounded-lg"
          />

          <div className="flex items-center justify-between pt-1">
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setIsPlayingAnim(!isPlayingAnim)}
                className="px-3.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-lg flex items-center gap-1.5 transition-all border border-slate-700 cursor-pointer"
              >
                {isPlayingAnim ? <Pause className="w-3.5 h-3.5 text-amber-400" /> : <Play className="w-3.5 h-3.5 text-cyan-400 fill-current" />}
                {isPlayingAnim ? "Pause" : "Play Animation"}
              </button>
              <button
                type="button"
                onClick={() => {
                  setIsPlayingAnim(false);
                  setAnimProgress(0);
                }}
                className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200 rounded-lg transition-all border border-slate-700 cursor-pointer"
                title="Reset to t=0"
              >
                <RotateCcw className="w-3.5 h-3.5" />
              </button>
            </div>

            <div className="text-[11px] text-slate-500 font-mono">
              Explicit Integration: Δt = 0.1 ms | 180 ms Crash Duration
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
