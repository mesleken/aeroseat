import React, { useRef } from 'react';
import {
  ShieldCheck, CheckCircle2, AlertTriangle, XCircle, Sliders, Upload, User, Zap, FileText, Check, ArrowDown, ArrowRight
} from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, ResponsiveContainer, Tooltip } from 'recharts';

export default function ScenarioQATab({
  simConfig,
  qaResult,
  handleCreateSimConfig,
  handleRunQA,
  isLoading,
  modelRevision,
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
  handleUploadCustomPulse,
  dummyOffset = { x: 0, y: 0, z: 0, recline: 0, yaw: 0 },
  setDummyOffset,
  seatOffset = { x: 0, y: 0, z: 0, pitchWarp: 0, rollWarp: 0, yawMount: 0 },
  setSeatOffset
}) {
  const fileInputRef = useRef(null);

  const onPulseFileSelected = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      handleUploadCustomPulse(file, file.name.replace(/\.[^/.]+$/, ""), testType);
    }
  };

  return (
    <div className="space-y-6">
      {/* 1. Scenario & Model QA Gate Header & Actions */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-5 shadow-xl">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="space-y-0.5">
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-cyan-400" /> Scenario Setup & Model QA Gate
            </h2>
            <p className="text-xs text-slate-400">
              Configure dynamic crash conditions, occupant dummy anthropometry, and custom deceleration pulses.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleCreateSimConfig}
              disabled={isLoading || !modelRevision}
              className="text-xs px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl border border-slate-700 font-semibold transition-all cursor-pointer disabled:opacity-50 active:scale-95 shadow-sm"
            >
              1. Create Config
            </button>
            <button
              onClick={handleRunQA}
              disabled={isLoading || !simConfig}
              className="text-xs px-4 py-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-semibold rounded-xl shadow-md shadow-cyan-500/20 transition-all cursor-pointer disabled:opacity-50 active:scale-95"
            >
              2. Run Model QA Gate
            </button>
          </div>
        </div>

        {/* 2. Test Type & Dummy Anthropometry Selection Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* 2.1 Dynamic Test Regulation Type */}
          <div className="bg-slate-950/90 p-4 rounded-xl border border-slate-800 space-y-3">
            <div className="flex items-center justify-between text-xs font-bold text-slate-200">
              <span className="flex items-center gap-1.5">
                <Zap className="w-3.5 h-3.5 text-amber-400" /> Dynamic Certification Test Condition
              </span>
              <span className="text-[10px] text-slate-500 font-mono">14 CFR § 25.562</span>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setTestType("FORWARD_16G")}
                className={`p-3 rounded-xl border text-left transition-all cursor-pointer ${
                  testType === "FORWARD_16G"
                    ? "bg-cyan-950/40 border-cyan-500/80 ring-1 ring-cyan-500/50 shadow-md shadow-cyan-950/30"
                    : "bg-slate-900/50 border-slate-800 text-slate-400 hover:border-slate-700"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-white flex items-center gap-1">
                    <ArrowRight className="w-3 h-3 text-cyan-400" /> Test 2: 16g Forward
                  </span>
                  {testType === "FORWARD_16G" && <Check className="w-3.5 h-3.5 text-cyan-400" />}
                </div>
                <div className="text-[10px] text-slate-400 mt-1">Longitudinal sled crash</div>
                <div className="text-[10px] font-mono text-cyan-400 mt-0.5">Δv &ge; 13.4 m/s (44 ft/s)</div>
              </button>

              <button
                type="button"
                onClick={() => setTestType("DOWNWARD_14G")}
                className={`p-3 rounded-xl border text-left transition-all cursor-pointer ${
                  testType === "DOWNWARD_14G"
                    ? "bg-cyan-950/40 border-cyan-500/80 ring-1 ring-cyan-500/50 shadow-md shadow-cyan-950/30"
                    : "bg-slate-900/50 border-slate-800 text-slate-400 hover:border-slate-700"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-white flex items-center gap-1">
                    <ArrowDown className="w-3 h-3 text-cyan-400" /> Test 1: 14g Downward
                  </span>
                  {testType === "DOWNWARD_14G" && <Check className="w-3.5 h-3.5 text-cyan-400" />}
                </div>
                <div className="text-[10px] text-slate-400 mt-1">Vertical floor impact</div>
                <div className="text-[10px] font-mono text-cyan-400 mt-0.5">Δv &ge; 10.7 m/s (35 ft/s)</div>
              </button>
            </div>
          </div>

          {/* 2.2 Anthropometric Test Dummy (ATD) Model */}
          <div className="bg-slate-950/90 p-4 rounded-xl border border-slate-800 space-y-3">
            <div className="flex items-center justify-between text-xs font-bold text-slate-200">
              <span className="flex items-center gap-1.5">
                <User className="w-3.5 h-3.5 text-cyan-400" /> Occupant Dummy Model (ATD)
              </span>
              <span className="text-[10px] text-slate-500 font-mono">SAE AS8049E Standard</span>
            </div>

            <div className="space-y-2">
              <select
                value={dummyType}
                onChange={(e) => setDummyType(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2.5 text-xs text-white focus:outline-none focus:border-cyan-500 font-medium cursor-pointer"
              >
                <option value="FAA_HIII_50M">FAA Hybrid III 50th Percentile Male (78 kg / 172 lbs)</option>
                <option value="FAA_HIII_5F">FAA Hybrid III 5th Percentile Female (49 kg / 108 lbs)</option>
                <option value="FAA_HIII_95M">FAA Hybrid III 95th Percentile Male (101 kg / 223 lbs)</option>
              </select>

              <div className="grid grid-cols-3 gap-2 text-[11px] font-mono text-center">
                <div className="bg-slate-900 p-2 rounded-lg border border-slate-800/80">
                  <div className="text-slate-500 text-[10px]">Head Mass</div>
                  <div className="text-cyan-400 font-bold">
                    {dummyType === "FAA_HIII_5F" ? "3.63 kg" : dummyType === "FAA_HIII_95M" ? "5.45 kg" : "4.54 kg"}
                  </div>
                </div>
                <div className="bg-slate-900 p-2 rounded-lg border border-slate-800/80">
                  <div className="text-slate-500 text-[10px]">Thorax Mass</div>
                  <div className="text-cyan-400 font-bold">
                    {dummyType === "FAA_HIII_5F" ? "17.28 kg" : dummyType === "FAA_HIII_95M" ? "27.65 kg" : "23.04 kg"}
                  </div>
                </div>
                <div className="bg-slate-900 p-2 rounded-lg border border-slate-800/80">
                  <div className="text-slate-500 text-[10px]">Total ATD</div>
                  <div className="text-amber-400 font-bold">
                    {dummyType === "FAA_HIII_5F" ? "49 kg" : dummyType === "FAA_HIII_95M" ? "101 kg" : "78 kg"}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* 3. Custom Sled Pulse CSV Uploader Zone */}
        <div className="bg-slate-950/90 p-4 rounded-xl border border-slate-800 space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="text-xs font-bold text-slate-200 flex items-center gap-1.5">
              <FileText className="w-3.5 h-3.5 text-cyan-400" /> Sled Deceleration Pulse Signal Profile
            </div>
            <div className="flex items-center gap-2">
              <input
                type="file"
                ref={fileInputRef}
                accept=".csv,.txt,.dat"
                onChange={onPulseFileSelected}
                className="hidden"
              />
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={isLoading}
                className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-lg border border-slate-700 flex items-center gap-1.5 transition-all cursor-pointer active:scale-95"
              >
                <Upload className="w-3 h-3 text-cyan-400" /> Upload Custom Pulse CSV
              </button>
              {customPulse && (
                <button
                  type="button"
                  onClick={() => setCustomPulse(null)}
                  className="text-[11px] text-slate-500 hover:text-rose-400 font-mono"
                >
                  Reset to Standard
                </button>
              )}
            </div>
          </div>

          {customPulse ? (
            <div className="space-y-2.5 bg-slate-900/80 p-3 rounded-xl border border-cyan-800/60">
              <div className="flex flex-wrap items-center justify-between text-xs font-mono">
                <span className="text-cyan-400 font-bold flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> Custom Pulse Loaded: {customPulse.name}
                </span>
                <div className="flex items-center gap-2">
                  <span className="text-amber-400 font-bold">Peak: {customPulse.peak_g}g</span>
                  <span className="text-slate-600">|</span>
                  <span className="text-slate-300">Δv: {customPulse.delta_v_ms} m/s</span>
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      customPulse.delta_v_valid
                        ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
                        : "bg-amber-950 text-amber-400 border border-amber-800"
                    }`}
                  >
                    {customPulse.delta_v_valid ? "ΔV VALID" : "ΔV LOW"}
                  </span>
                </div>
              </div>

              {customPulse.curve_preview && customPulse.curve_preview.length > 0 && (
                <div className="h-24 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={customPulse.curve_preview}>
                      <defs>
                        <linearGradient id="customPulseGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.4} />
                          <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.0} />
                        </linearGradient>
                      </defs>
                      <XAxis dataKey="time_s" hide />
                      <YAxis hide domain={[0, 'auto']} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "#0f172a",
                          borderColor: "#334155",
                          fontSize: "11px",
                          borderRadius: "6px",
                          color: "#f8fafc",
                        }}
                      />
                      <Area
                        type="monotone"
                        dataKey="accel_g"
                        stroke="#06b6d4"
                        fill="url(#customPulseGrad)"
                        strokeWidth={2}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>
          ) : (
            <div className="p-3 bg-slate-900/50 rounded-xl border border-slate-800 text-xs text-slate-400 flex items-center justify-between">
              <span>Standard SAE AS8049 Rev E Ideal Isosceles Triangular Pulse (0 &rarr; 16g in 90ms)</span>
              <span className="px-2 py-0.5 bg-slate-800 text-cyan-400 border border-slate-700 rounded text-[10px] font-mono">
                SAE DEFAULT
              </span>
            </div>
          )}
        </div>

        {/* 4. Yaw, Pitch, Roll 3D Vector Sliders */}
        <div className="bg-slate-950/90 p-4 rounded-xl border border-slate-800 space-y-3">
          <div className="flex items-center justify-between">
            <div className="text-xs font-bold text-slate-200 flex items-center gap-1.5">
              <Sliders className="w-3.5 h-3.5 text-cyan-400" /> Sled Impact Orientation Angles (Yaw, Pitch, Roll)
            </div>
            <span className="text-[10px] text-slate-500 font-mono">SAE AS8049 Rev E 3D Vector</span>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div className="space-y-1">
              <div className="flex justify-between text-[11px] text-slate-400">
                <span>Yaw (ψ):</span>
                <span className="text-cyan-400 font-mono font-bold">{yawAngle}°</span>
              </div>
              <input
                type="range"
                min="-45"
                max="45"
                step="1"
                value={yawAngle}
                onChange={(e) => setYawAngle(parseFloat(e.target.value))}
                className="w-full accent-cyan-500 cursor-pointer h-1.5 bg-slate-800 rounded-lg"
              />
            </div>

            <div className="space-y-1">
              <div className="flex justify-between text-[11px] text-slate-400">
                <span>Pitch (θ):</span>
                <span className="text-cyan-400 font-mono font-bold">{pitchAngle}°</span>
              </div>
              <input
                type="range"
                min="-30"
                max="30"
                step="1"
                value={pitchAngle}
                onChange={(e) => setPitchAngle(parseFloat(e.target.value))}
                className="w-full accent-cyan-500 cursor-pointer h-1.5 bg-slate-800 rounded-lg"
              />
            </div>

            <div className="space-y-1">
              <div className="flex justify-between text-[11px] text-slate-400">
                <span>Roll (ϕ):</span>
                <span className="text-cyan-400 font-mono font-bold">{rollAngle}°</span>
              </div>
              <input
                type="range"
                min="-30"
                max="30"
                step="1"
                value={rollAngle}
                onChange={(e) => setRollAngle(parseFloat(e.target.value))}
                className="w-full accent-cyan-500 cursor-pointer h-1.5 bg-slate-800 rounded-lg"
              />
            </div>
          </div>
        </div>

        {/* 4.1 Occupant ATD Seating Posture & Floor Track Warpage */}
        {setDummyOffset && setSeatOffset && (
          <div className="bg-slate-950/90 p-4 rounded-xl border border-slate-800 space-y-3">
            <div className="flex items-center justify-between">
              <div className="text-xs font-bold text-slate-200 flex items-center gap-1.5">
                <User className="w-3.5 h-3.5 text-amber-400" /> ATD Occupant Seating Posture & 14 CFR § 25.562 Floor Warpage
              </div>
              <button
                type="button"
                onClick={() => {
                  setDummyOffset({ x: 0, y: 0, z: 0, recline: 0, yaw: 0 });
                  setSeatOffset({ x: 0, y: 0, z: 0, pitchWarp: 0, rollWarp: 0, yawMount: 0 });
                }}
                className="text-[10px] text-slate-500 hover:text-rose-400 font-mono transition-colors"
              >
                Reset Posture to Baseline
              </button>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {/* Torso Recline */}
              <div className="space-y-1 bg-slate-900 p-2.5 rounded-lg border border-slate-800">
                <div className="flex justify-between text-[11px] text-slate-400">
                  <span>Torso Recline:</span>
                  <span className={`font-mono font-bold ${dummyOffset.recline !== 0 ? 'text-cyan-300' : 'text-slate-400'}`}>
                    {dummyOffset.recline > 0 ? `+${dummyOffset.recline}` : dummyOffset.recline}°
                  </span>
                </div>
                <input
                  type="range"
                  min="-10"
                  max="25"
                  step="1"
                  value={dummyOffset.recline}
                  onChange={(e) => setDummyOffset(prev => ({ ...prev, recline: parseFloat(e.target.value) }))}
                  className="w-full accent-cyan-500 cursor-pointer h-1.5 bg-slate-800 rounded-lg"
                />
              </div>

              {/* Fore/Aft Seating */}
              <div className="space-y-1 bg-slate-900 p-2.5 rounded-lg border border-slate-800">
                <div className="flex justify-between text-[11px] text-slate-400">
                  <span>Fore/Aft (Z):</span>
                  <span className={`font-mono font-bold ${dummyOffset.z !== 0 ? 'text-cyan-300' : 'text-slate-400'}`}>
                    {dummyOffset.z > 0 ? `+${dummyOffset.z}` : dummyOffset.z} cm
                  </span>
                </div>
                <input
                  type="range"
                  min="-8"
                  max="8"
                  step="0.5"
                  value={dummyOffset.z}
                  onChange={(e) => setDummyOffset(prev => ({ ...prev, z: parseFloat(e.target.value) }))}
                  className="w-full accent-cyan-500 cursor-pointer h-1.5 bg-slate-800 rounded-lg"
                />
              </div>

              {/* Occupant Yaw */}
              <div className="space-y-1 bg-slate-900 p-2.5 rounded-lg border border-slate-800">
                <div className="flex justify-between text-[11px] text-slate-400">
                  <span>Occupant Yaw:</span>
                  <span className={`font-mono font-bold ${dummyOffset.yaw !== 0 ? 'text-amber-300' : 'text-slate-400'}`}>
                    {dummyOffset.yaw > 0 ? `+${dummyOffset.yaw}` : dummyOffset.yaw}°
                  </span>
                </div>
                <input
                  type="range"
                  min="-20"
                  max="20"
                  step="1"
                  value={dummyOffset.yaw}
                  onChange={(e) => setDummyOffset(prev => ({ ...prev, yaw: parseFloat(e.target.value) }))}
                  className="w-full accent-amber-500 cursor-pointer h-1.5 bg-slate-800 rounded-lg"
                />
              </div>

              {/* Floor Pitch Warping */}
              <div className="space-y-1 bg-slate-900 p-2.5 rounded-lg border border-slate-800">
                <div className="flex justify-between text-[11px] text-slate-400">
                  <span>Floor Pitch Warp:</span>
                  <span className={`font-mono font-bold ${seatOffset.pitchWarp !== 0 ? 'text-emerald-300' : 'text-slate-400'}`}>
                    {seatOffset.pitchWarp > 0 ? `+${seatOffset.pitchWarp}` : seatOffset.pitchWarp}°
                  </span>
                </div>
                <input
                  type="range"
                  min="-15"
                  max="15"
                  step="1"
                  value={seatOffset.pitchWarp}
                  onChange={(e) => setSeatOffset(prev => ({ ...prev, pitchWarp: parseFloat(e.target.value) }))}
                  className="w-full accent-emerald-500 cursor-pointer h-1.5 bg-slate-800 rounded-lg"
                />
              </div>
            </div>
          </div>
        )}

        {/* 5. Model QA Gate Output Breakdown */}
        {qaResult && (
          <div className="space-y-3 pt-2">
            <div className="flex items-center justify-between bg-slate-950 p-3.5 rounded-xl border border-slate-800">
              <span className="text-xs text-slate-300 font-medium">Model QA Gate Pre-Flight Status:</span>
              <span
                className={`px-3 py-1 rounded-full text-xs font-bold font-mono ${
                  qaResult.overall_status === "PASS"
                    ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
                    : qaResult.overall_status === "WARNING"
                    ? "bg-amber-950 text-amber-400 border border-amber-800"
                    : "bg-red-950 text-red-400 border border-red-800"
                }`}
              >
                QA GATE: {qaResult.overall_status}
              </span>
            </div>

            <div className="space-y-1.5 max-h-64 overflow-y-auto pr-1">
              {Array.isArray(qaResult.checks) &&
                qaResult.checks.map((chk, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between bg-slate-950/70 p-2.5 rounded-lg border border-slate-800/80 text-xs hover:border-slate-700 transition-all"
                  >
                    <div className="flex items-center gap-2">
                      {chk.status === "PASS" && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />}
                      {chk.status === "WARNING" && <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0" />}
                      {chk.status === "BLOCKED" && <XCircle className="w-3.5 h-3.5 text-red-400 shrink-0" />}
                      <span className="font-mono text-slate-200">{chk.name}</span>
                    </div>
                    <span className="text-[11px] text-slate-400 truncate max-w-[280px]" title={chk.message}>
                      {chk.message}
                    </span>
                  </div>
                ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
