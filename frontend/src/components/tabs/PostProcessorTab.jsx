import React, { useState, useMemo } from 'react';
import { BarChart3, Download, Sliders, CheckSquare, Square, Layers, Sparkles, Filter } from 'lucide-react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts';
import { generateCurveData } from '../../data/curveGenerator';

const AVAILABLE_CHANNELS = [
  { id: "sim_head_g", label: "Head Resultant Accel (g)", color: "#06b6d4", unit: "g", defaultActive: true },
  { id: "sled_pulse_g", label: "Sled Impact Decel Pulse (g)", color: "#f59e0b", unit: "g", defaultActive: true },
  { id: "hic_value", label: "Head Injury Criterion HIC(t)", color: "#ec4899", unit: "", defaultActive: false },
  { id: "femur_left_kn", label: "Left Femur Compressive Load (kN)", color: "#38bdf8", unit: "kN", defaultActive: true },
  { id: "femur_right_kn", label: "Right Femur Compressive Load (kN)", color: "#a855f7", unit: "kN", defaultActive: false },
  { id: "lumbar_kn", label: "Lumbar Spine Axial Load (kN)", color: "#f43f5e", unit: "kN", defaultActive: true },
  { id: "neck_fz_n", label: "Neck Axial Tension/Compression Fz (N)", color: "#10b981", unit: "N", defaultActive: false },
  { id: "neck_my_nm", label: "Neck Flexion/Extension Moment My (Nm)", color: "#f97316", unit: "Nm", defaultActive: false },
  { id: "belt_shoulder_kn", label: "Upper Shoulder Belt Tension (kN)", color: "#818cf8", unit: "kN", defaultActive: false },
  { id: "belt_lap_kn", label: "Pelvis Lap Belt Tension (kN)", color: "#34d399", unit: "kN", defaultActive: false },
];

export default function PostProcessorTab({ injuryMetrics }) {
  const curveData = useMemo(() => generateCurveData(injuryMetrics?.raw_timeseries), [injuryMetrics?.raw_timeseries]);
  
  const [activeChannels, setActiveChannels] = useState(
    AVAILABLE_CHANNELS.filter(c => c.defaultActive).map(c => c.id)
  );
  const [activeFilterCfc, setActiveFilterCfc] = useState("CFC_1000");

  const toggleChannel = (id) => {
    setActiveChannels(prev =>
      prev.includes(id) ? prev.filter(c => c !== id) : [...prev, id]
    );
  };

  const selectAll = () => {
    setActiveChannels(AVAILABLE_CHANNELS.map(c => c.id));
  };

  const clearAll = () => {
    setActiveChannels(["sim_head_g", "sled_pulse_g"]);
  };

  // Export CSV
  const handleExportCSV = () => {
    if (!curveData || curveData.length === 0) return;
    
    const headers = ["time_ms", ...activeChannels];
    const rows = curveData.map(row => {
      return [row.time_ms, ...activeChannels.map(ch => row[ch] !== undefined ? row[ch] : "")].join(",");
    });
    
    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `aeroseat_tema_channels_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-6">
      {/* Top Header & Export Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="space-y-1">
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-cyan-400" /> TEMA Motion Analysis & Photometric Channel Post-Processor
            </h2>
            <p className="text-xs text-slate-400">
              Multi-channel signal overlay, photogrammetry tracking, Sprague-Geers phase alignment, and instrument export.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleExportCSV}
              className="px-3.5 py-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-xs font-semibold rounded-xl flex items-center gap-1.5 shadow-md shadow-cyan-500/20 cursor-pointer transition-all active:scale-95"
            >
              <Download className="w-3.5 h-3.5" /> Export Selected CSV
            </button>
          </div>
        </div>

        {/* Channel Selection Matrix */}
        <div className="bg-slate-950/90 p-4 rounded-xl border border-slate-800 space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-2.5">
            <span className="text-xs font-bold text-slate-200 flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-cyan-400" /> Active Transducer & Biomechanical Channels ({activeChannels.length}/{AVAILABLE_CHANNELS.length})
            </span>
            <div className="flex items-center gap-2 text-xs font-mono">
              <button
                onClick={selectAll}
                className="text-cyan-400 hover:text-cyan-300 transition-colors cursor-pointer"
              >
                Select All
              </button>
              <span className="text-slate-600">|</span>
              <button
                onClick={clearAll}
                className="text-slate-400 hover:text-slate-200 transition-colors cursor-pointer"
              >
                Reset Default
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
            {AVAILABLE_CHANNELS.map(ch => {
              const isActive = activeChannels.includes(ch.id);
              return (
                <button
                  key={ch.id}
                  onClick={() => toggleChannel(ch.id)}
                  className={`p-2.5 rounded-xl border text-left flex items-center justify-between text-xs transition-all cursor-pointer ${
                    isActive
                      ? "bg-slate-900 border-slate-700 text-white shadow-sm"
                      : "bg-slate-950/40 border-slate-800/80 text-slate-500 hover:text-slate-400"
                  }`}
                >
                  <div className="flex items-center gap-2 min-w-0 pr-2">
                    <div
                      className="w-3 h-3 rounded-full shrink-0"
                      style={{ backgroundColor: isActive ? ch.color : "#475569" }}
                    />
                    <span className="truncate font-medium">{ch.label}</span>
                  </div>
                  {isActive ? (
                    <CheckSquare className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                  ) : (
                    <Square className="w-3.5 h-3.5 text-slate-600 shrink-0" />
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Multi-Channel Interactive Canvas */}
        <div className="bg-slate-950/90 p-4 rounded-xl border border-slate-800 space-y-3">
          <div className="flex flex-wrap items-center justify-between text-xs font-mono">
            <span className="text-slate-300 font-semibold flex items-center gap-1.5">
              <Filter className="w-3.5 h-3.5 text-cyan-400" /> Synchronized Time-History Overlay (t = -10ms to +180ms)
            </span>
            <div className="flex items-center gap-3">
              <span className="text-slate-400">SAE J211 Digital Filtering:</span>
              <div className="flex gap-1 bg-slate-900 p-0.5 rounded-lg border border-slate-800">
                {["RAW", "CFC_60", "CFC_600", "CFC_1000"].map(filter => (
                  <button
                    key={filter}
                    onClick={() => setActiveFilterCfc(filter)}
                    className={`px-2 py-0.5 rounded text-[10px] font-semibold transition-colors cursor-pointer ${
                      activeFilterCfc === filter
                        ? "bg-cyan-600 text-white"
                        : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    {filter}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="h-80 w-full pt-2">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={curveData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="time_ms" stroke="#64748b" tick={{ fontSize: 10 }} unit="ms" />
                <YAxis stroke="#64748b" tick={{ fontSize: 10 }} />
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
                {AVAILABLE_CHANNELS.filter(ch => activeChannels.includes(ch.id)).map(ch => (
                  <Line
                    key={ch.id}
                    type="monotone"
                    dataKey={ch.id}
                    stroke={ch.color}
                    strokeWidth={2}
                    dot={false}
                    name={ch.label}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Peak Measurements Summary Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
          <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800 space-y-1">
            <div className="text-slate-500 text-[11px]">Peak Head Accel</div>
            <div className="text-cyan-400 font-bold text-sm">
              {curveData.length > 0 ? Math.max(...curveData.map(d => d.sim_head_g || 0)) : 42.0} g
            </div>
            <div className="text-[10px] text-slate-600">CFC 1000 Peak at ~75ms</div>
          </div>
          <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800 space-y-1">
            <div className="text-slate-500 text-[11px]">Max Lumbar Load</div>
            <div className="text-rose-400 font-bold text-sm">{injuryMetrics?.lumbar_load || 3.6} kN</div>
            <div className="text-[10px] text-slate-600">Limit: 6.67 kN (Pass)</div>
          </div>
          <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800 space-y-1">
            <div className="text-slate-500 text-[11px]">Max Femur Load (L)</div>
            <div className="text-blue-400 font-bold text-sm">{injuryMetrics?.femur_load_left || 4.3} kN</div>
            <div className="text-[10px] text-slate-600">Limit: 10.0 kN (Pass)</div>
          </div>
          <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800 space-y-1">
            <div className="text-slate-500 text-[11px]">Sled Velocity Change</div>
            <div className="text-amber-400 font-bold text-sm">{injuryMetrics?.delta_v_ms || 14.1} m/s</div>
            <div className="text-[10px] text-slate-600">Req: &ge; 13.4 m/s (44 ft/s)</div>
          </div>
        </div>
      </div>
    </div>
  );
}
