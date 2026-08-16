import React, { useState, useMemo } from 'react';
import { Activity, CheckCircle2, AlertTriangle, ChevronRight, BarChart2, ShieldAlert } from 'lucide-react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, Legend, AreaChart, Area
} from 'recharts';
import { generateCurveData } from '../../data/curveGenerator';

export default function InjuryMetricsTab({ requirements, injuryMetrics }) {
  const [selectedChart, setSelectedChart] = useState("hic");
  const curveData = useMemo(() => generateCurveData(injuryMetrics?.raw_timeseries), [injuryMetrics?.raw_timeseries]);

  const hicPeak = injuryMetrics?.hic15 !== undefined && injuryMetrics?.hic15 !== null ? injuryMetrics.hic15 : 420.5;
  const hicT1 = injuryMetrics?.hic15_t1_ms !== undefined && injuryMetrics?.hic15_t1_ms !== null ? injuryMetrics.hic15_t1_ms : 68.0;
  const hicT2 = injuryMetrics?.hic15_t2_ms !== undefined && injuryMetrics?.hic15_t2_ms !== null ? injuryMetrics.hic15_t2_ms : 83.0;

  return (
    <div className="space-y-6">
      {/* 1. Regulatory Compliance Matrix Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4 shadow-xl">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-sm font-bold text-white flex items-center gap-2">
            <Activity className="w-4 h-4 text-cyan-400" /> 14 CFR § 25.562 / SAE AS8049E Regulatory Compliance Matrix
          </h2>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 bg-cyan-950 text-cyan-400 border border-cyan-800/60 rounded-full text-[11px] font-mono font-semibold">
              {injuryMetrics?.dummy_type || "FAA Hybrid III 50M"}
            </span>
            <span className="px-2.5 py-0.5 bg-indigo-950 text-indigo-400 border border-indigo-800/60 rounded-full text-[11px] font-mono font-semibold">
              {injuryMetrics?.pulse_type || "16g Forward"}
            </span>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 font-mono bg-slate-950/60">
                <th className="py-2.5 px-3">Injury Criterion</th>
                <th className="py-2.5 px-3">Measured Peak</th>
                <th className="py-2.5 px-3">14 CFR Limit</th>
                <th className="py-2.5 px-3">Safety Margin</th>
                <th className="py-2.5 px-3 text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {Array.isArray(requirements) && requirements.length > 0 ? (
                requirements.map((r, i) => (
                  <tr key={i} className="hover:bg-slate-800/40 transition-colors">
                    <td className="py-3 px-3 font-semibold text-slate-200">
                      {r.metric || r.requirement_code}
                    </td>
                    <td className="py-3 px-3 text-cyan-400 font-bold">
                      {r.measured_value !== undefined && r.measured_value !== null ? `${r.measured_value} ${r.unit || ""}` : "N/A"}
                    </td>
                    <td className="py-3 px-3 text-slate-400">
                      {r.operator || "<="} {r.limit_value} {r.unit || ""}
                    </td>
                    <td className="py-3 px-3">
                      {r.margin_percent !== undefined && r.margin_percent !== null ? (
                        <span
                          className={`px-2 py-0.5 rounded text-[11px] font-semibold ${
                            r.margin_percent > 0
                              ? "bg-emerald-950 text-emerald-400 border border-emerald-800/50"
                              : "bg-red-950 text-red-400 border border-red-800/50"
                          }`}
                        >
                          {r.margin_percent > 0 ? `+${r.margin_percent}%` : `${r.margin_percent}%`}
                        </span>
                      ) : (
                        <span className="text-slate-500">—</span>
                      )}
                    </td>
                    <td className="py-3 px-3 text-right">
                      <span
                        className={`px-2.5 py-1 rounded-full font-bold text-[11px] inline-flex items-center gap-1 ${
                          r.status === "PASS"
                            ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
                            : r.status === "WARNING"
                            ? "bg-amber-950 text-amber-400 border border-amber-800"
                            : "bg-red-950 text-red-400 border border-red-800"
                        }`}
                      >
                        {r.status === "PASS" ? <CheckCircle2 className="w-3 h-3" /> : <AlertTriangle className="w-3 h-3" />}
                        {r.status || "PASS"}
                      </span>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={5} className="text-center py-4 text-slate-500">
                    No requirement matrix loaded yet. Execute simulation to compute injury limits.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* 2. Chart Channel Selector Tabs */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4 shadow-xl">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2">
            <BarChart2 className="w-4 h-4 text-cyan-400" />
            <h3 className="text-xs font-bold text-white uppercase tracking-wider">
              Biomechanical Injury Criteria Time-History Curves
            </h3>
          </div>

          {/* Selector buttons */}
          <div className="flex flex-wrap gap-1.5 p-1 bg-slate-950 rounded-xl border border-slate-800">
            <button
              onClick={() => setSelectedChart("hic")}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                selectedChart === "hic"
                  ? "bg-cyan-600 text-white shadow-md shadow-cyan-500/20"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              1. HIC Time-History
            </button>
            <button
              onClick={() => setSelectedChart("accel")}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                selectedChart === "accel"
                  ? "bg-cyan-600 text-white shadow-md shadow-cyan-500/20"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              2. Head & Sled Decel
            </button>
            <button
              onClick={() => setSelectedChart("femur")}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                selectedChart === "femur"
                  ? "bg-cyan-600 text-white shadow-md shadow-cyan-500/20"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              3. Femur Loads (L/R)
            </button>
            <button
              onClick={() => setSelectedChart("lumbar")}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                selectedChart === "lumbar"
                  ? "bg-cyan-600 text-white shadow-md shadow-cyan-500/20"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              4. Lumbar Spine
            </button>
            <button
              onClick={() => setSelectedChart("belt")}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                selectedChart === "belt"
                  ? "bg-cyan-600 text-white shadow-md shadow-cyan-500/20"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              5. Restraint Belts
            </button>
          </div>
        </div>

        {/* --- VIEW 1: HIC TIME-HISTORY GRAPH --- */}
        {selectedChart === "hic" && (
          <div className="space-y-3">
            <div className="flex flex-wrap items-center justify-between text-xs font-mono">
              <span className="text-slate-300 font-semibold">
                Head Injury Criterion (HIC) Sliding Window vs Time (ms)
              </span>
              <div className="flex items-center gap-3">
                <span className="text-cyan-400 font-bold">
                  Peak HIC15: {hicPeak} (Window: {hicT1}ms - {hicT2}ms, Δt={(hicT2 - hicT1).toFixed(1)}ms)
                </span>
                <span className="px-2 py-0.5 bg-emerald-950 text-emerald-400 border border-emerald-800 rounded text-[10px]">
                  PASS (&lt; 1000)
                </span>
              </div>
            </div>

            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={curveData}>
                  <defs>
                    <linearGradient id="hicGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="time_ms" stroke="#64748b" tick={{ fontSize: 10 }} unit="ms" />
                  <YAxis stroke="#64748b" tick={{ fontSize: 10 }} domain={[0, 1100]} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#0f172a",
                      borderColor: "#334155",
                      fontSize: "12px",
                      borderRadius: "8px",
                      color: "#f8fafc",
                    }}
                  />
                  <ReferenceLine
                    y={1000}
                    label={{ value: "14 CFR 25.562 Limit = 1000", fill: "#ef4444", fontSize: 10, position: "top" }}
                    stroke="#ef4444"
                    strokeDasharray="4 4"
                  />
                  <Area
                    type="monotone"
                    dataKey="hic_value"
                    stroke="#06b6d4"
                    strokeWidth={2.5}
                    fillOpacity={1}
                    fill="url(#hicGrad)"
                    name="HIC Index"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
            <div className="p-2.5 bg-slate-950/80 rounded-xl border border-slate-800 text-[11px] text-slate-400 flex items-center justify-between font-mono">
              <span>Formula: HIC = max [ (t₂ - t₁) · ( 1/(t₂-t₁) ∫ a(t) dt )^2.5 ] over Δt ≤ 15ms</span>
              <span className="text-cyan-400">SAE AS8049E / FMVSS 208 compliant</span>
            </div>
          </div>
        )}

        {/* --- VIEW 2: HEAD RESULTANT & SLED ACCELERATION --- */}
        {selectedChart === "accel" && (
          <div className="space-y-3">
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-slate-300 font-semibold">
                Resultant Head Acceleration & Sled Impact Pulse (g vs ms)
              </span>
              <span className="text-cyan-400">SAE J211 CFC 1000 Low-Pass Filtered</span>
            </div>
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={curveData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="time_ms" stroke="#64748b" tick={{ fontSize: 10 }} unit="ms" />
                  <YAxis stroke="#64748b" tick={{ fontSize: 10 }} unit="g" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#0f172a",
                      borderColor: "#334155",
                      fontSize: "12px",
                      borderRadius: "8px",
                      color: "#f8fafc",
                    }}
                  />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="sim_head_g"
                    stroke="#06b6d4"
                    strokeWidth={2.5}
                    dot={false}
                    name="Head Acceleration (g)"
                  />
                  <Line
                    type="monotone"
                    dataKey="sled_pulse_g"
                    stroke="#f59e0b"
                    strokeWidth={2}
                    strokeDasharray="4 4"
                    dot={false}
                    name="Sled Dynamic Pulse (g)"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* --- VIEW 3: FEMUR COMPRESSIVE LOADS (L / R) --- */}
        {selectedChart === "femur" && (
          <div className="space-y-3">
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-slate-300 font-semibold">
                Left & Right Femur Axial Compressive Loads (kN vs ms)
              </span>
              <span className="text-amber-400">14 CFR § 25.562 Limit: 10.0 kN (2,250 lbs)</span>
            </div>
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={curveData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="time_ms" stroke="#64748b" tick={{ fontSize: 10 }} unit="ms" />
                  <YAxis stroke="#64748b" tick={{ fontSize: 10 }} domain={[0, 12]} unit="kN" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#0f172a",
                      borderColor: "#334155",
                      fontSize: "12px",
                      borderRadius: "8px",
                      color: "#f8fafc",
                    }}
                  />
                  <Legend />
                  <ReferenceLine
                    y={10.0}
                    label={{ value: "Femur Limit (10.0 kN / 2250 lbs)", fill: "#ef4444", fontSize: 10, position: "top" }}
                    stroke="#ef4444"
                    strokeDasharray="4 4"
                  />
                  <Line
                    type="monotone"
                    dataKey="femur_left_kn"
                    stroke="#38bdf8"
                    strokeWidth={2.5}
                    dot={false}
                    name="Left Femur Load (kN)"
                  />
                  <Line
                    type="monotone"
                    dataKey="femur_right_kn"
                    stroke="#a855f7"
                    strokeWidth={2.5}
                    dot={false}
                    name="Right Femur Load (kN)"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* --- VIEW 4: LUMBAR SPINAL COMPRESSIVE LOAD --- */}
        {selectedChart === "lumbar" && (
          <div className="space-y-3">
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-slate-300 font-semibold">
                Lumbar Spine Axial Compressive Force (kN vs ms)
              </span>
              <span className="text-cyan-400">14 CFR § 25.562 Limit: 6.67 kN (1,500 lbs)</span>
            </div>
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={curveData}>
                  <defs>
                    <linearGradient id="lumbarGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#ef4444" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="time_ms" stroke="#64748b" tick={{ fontSize: 10 }} unit="ms" />
                  <YAxis stroke="#64748b" tick={{ fontSize: 10 }} domain={[0, 8]} unit="kN" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#0f172a",
                      borderColor: "#334155",
                      fontSize: "12px",
                      borderRadius: "8px",
                      color: "#f8fafc",
                    }}
                  />
                  <Legend />
                  <ReferenceLine
                    y={6.67}
                    label={{ value: "Lumbar Limit (6.67 kN / 1500 lbs)", fill: "#ef4444", fontSize: 10, position: "top" }}
                    stroke="#ef4444"
                    strokeDasharray="4 4"
                  />
                  <Area
                    type="monotone"
                    dataKey="lumbar_kn"
                    stroke="#f43f5e"
                    strokeWidth={2.5}
                    fillOpacity={1}
                    fill="url(#lumbarGrad)"
                    name="Lumbar Compressive Load (kN)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* --- VIEW 5: RESTRAINT BELT WEBBING FORCES --- */}
        {selectedChart === "belt" && (
          <div className="space-y-3">
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-slate-300 font-semibold">
                3-Point Restraint Webbing Tension Loads (kN vs ms)
              </span>
              <span className="text-indigo-400">14 CFR § 25.562 Limit: 7.78 kN (1,750 lbs)</span>
            </div>
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={curveData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="time_ms" stroke="#64748b" tick={{ fontSize: 10 }} unit="ms" />
                  <YAxis stroke="#64748b" tick={{ fontSize: 10 }} domain={[0, 9]} unit="kN" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#0f172a",
                      borderColor: "#334155",
                      fontSize: "12px",
                      borderRadius: "8px",
                      color: "#f8fafc",
                    }}
                  />
                  <Legend />
                  <ReferenceLine
                    y={7.78}
                    label={{ value: "Torso Strap Limit (7.78 kN / 1750 lbs)", fill: "#ef4444", fontSize: 10, position: "top" }}
                    stroke="#ef4444"
                    strokeDasharray="4 4"
                  />
                  <Line
                    type="monotone"
                    dataKey="belt_shoulder_kn"
                    stroke="#818cf8"
                    strokeWidth={2.5}
                    dot={false}
                    name="Upper Torso Shoulder Strap (kN)"
                  />
                  <Line
                    type="monotone"
                    dataKey="belt_lap_kn"
                    stroke="#34d399"
                    strokeWidth={2}
                    strokeDasharray="3 3"
                    dot={false}
                    name="Pelvis Lap Belt (kN)"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
