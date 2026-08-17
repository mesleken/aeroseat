import React, { useState } from 'react';
import { RefreshCw, CheckCircle2, Sliders, Play, Zap } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { generateCurveData } from '../../data/curveGenerator';

export default function CorrelationTab({
  correlationData,
  handleRunCorrelation,
  handleReviewCredibility,
  isLoading,
  simResult,
  credibilityReview
}) {
  const [stiffness, setStiffness] = useState({
    belt_k_lap: 48000.0,
    belt_k_shoulder: 42000.0,
    neck_k_z: 22000.0,
    rail_mount_k: 850000.0,
    cushion_k: 36000.0
  });

  const [calibrating, setCalibrating] = useState(false);
  const [calibResult, setCalibResult] = useState(null);
  const [customSimResult, setCustomSimResult] = useState(null);

  const handleStiffnessChange = (e) => {
    const { name, value } = e.target;
    setStiffness(prev => ({
      ...prev,
      [name]: parseFloat(value) || 0
    }));
  };

  const runCustomSimulation = async () => {
    try {
      const res = await fetch("http://localhost:8000/api/v1/simulations/simulate-custom", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(stiffness)
      });
      const data = await res.json();
      setCustomSimResult(data.metrics);
      const hicVal = data.metrics?.hic15 != null ? data.metrics.hic15.toFixed(2) : "N/A";
      alert("Simulation ran successfully! HIC15: " + hicVal);
    } catch (e) {
      console.error(e);
      alert("Simulation failed.");
    }
  };

  const runAutoCalibration = async () => {
    setCalibrating(true);
    setCalibResult(null);
    try {
      const res = await fetch("http://localhost:8000/api/v1/simulations/auto-calibrate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pulse_type: "FORWARD_16G" })
      });
      const data = await res.json();
      if (data.calibration_result) {
        setCalibResult(data.calibration_result);
        setStiffness(prev => ({
          ...prev,
          ...data.calibration_result.optimal_parameters
        }));
      }
    } catch (e) {
      console.error(e);
      alert("Calibration failed.");
    } finally {
      setCalibrating(false);
    }
  };

  return (
    <div className="space-y-6">
      
      {/* PHASE 7: AUTOMATED CALIBRATION UI */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-5">
        <h2 className="text-sm font-bold text-white flex items-center gap-2">
          <Zap className="w-4 h-4 text-amber-400" /> Phase 7: Model Optimization & Auto-Calibration Engine
        </h2>
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Manual Input Form */}
          <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-4">
            <h3 className="text-xs font-semibold text-slate-300 flex items-center gap-1.5 uppercase tracking-wide">
              <Sliders className="w-3.5 h-3.5 text-cyan-500" /> Manual Stiffness Coefficients (N/m)
            </h3>
            <div className="space-y-3">
              {Object.entries(stiffness).map(([key, value]) => (
                <div key={key} className="flex justify-between items-center text-xs">
                  <label className="text-slate-400 font-mono w-1/2">{key}</label>
                  <input 
                    type="number"
                    name={key}
                    value={value}
                    onChange={handleStiffnessChange}
                    className="w-1/2 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-white font-mono focus:border-cyan-500 focus:outline-none"
                  />
                </div>
              ))}
            </div>
            <button
              onClick={runCustomSimulation}
              className="w-full mt-2 text-xs px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white font-medium rounded-lg transition-colors border border-slate-700 flex justify-center items-center gap-2"
            >
              <Play className="w-3 h-3" /> Run Preview Simulation
            </button>
            {customSimResult && (
              <div className="text-[11px] font-mono text-emerald-400 pt-2 text-center">
                Latest HIC15: {customSimResult.hic15?.toFixed(1)} | Nij: {customSimResult.nij_max?.toFixed(2)}
              </div>
            )}
          </div>

          {/* Auto Calibrate Action */}
          <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 flex flex-col justify-between">
            <div className="space-y-3">
              <h3 className="text-xs font-semibold text-slate-300 flex items-center gap-1.5 uppercase tracking-wide">
                <RefreshCw className="w-3.5 h-3.5 text-amber-500" /> SciPy Nelder-Mead Optimizer
              </h3>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                Connects to the backend <span className="font-mono text-cyan-400">ModelCalibrationEngine</span> to run hundreds of headless simulations. It iteratively updates stiffness properties to minimize NRMSE error against the Golden Experimental Dataset.
              </p>
              
              {calibResult && (
                <div className="bg-emerald-950/40 border border-emerald-900/50 rounded-lg p-3 text-[11px] font-mono text-slate-300 space-y-1 mt-2">
                  <div className="text-emerald-400 font-bold mb-2 flex items-center gap-2">
                    <CheckCircle2 className="w-3.5 h-3.5" /> Optimization Complete
                  </div>
                  <div>Iterations: <span className="text-white">{calibResult.iterations}</span></div>
                  <div>Baseline Error: <span className="text-red-400">{calibResult.baseline_loss_j.toFixed(2)}</span></div>
                  <div>Optimized Error: <span className="text-emerald-400">{calibResult.optimized_loss_j.toFixed(2)}</span></div>
                </div>
              )}
            </div>
            
            <button
              onClick={runAutoCalibration}
              disabled={calibrating}
              className="w-full mt-4 text-xs px-4 py-3 bg-gradient-to-r from-amber-600 to-orange-600 hover:from-amber-500 hover:to-orange-500 text-white font-bold rounded-lg shadow-lg shadow-amber-900/20 transition-all cursor-pointer disabled:opacity-50 flex justify-center items-center gap-2"
            >
              {calibrating ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
              {calibrating ? "Calibrating Physics Engine..." : "Run Auto-Calibration Sequence"}
            </button>
          </div>
        </div>
      </div>

    </div>
  );
}
