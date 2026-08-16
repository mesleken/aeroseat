import React from 'react';
import { Activity, Lock, Hash, Sparkles, AlertCircle } from 'lucide-react';

export default function AppHeader({ simConfig, solverJob, handleGoldenRegression, statusMessage, isLoading }) {
  const configHashStr = typeof simConfig?.configuration_hash === 'string' && simConfig.configuration_hash.length >= 10
    ? simConfig.configuration_hash.substring(0, 10) + "..."
    : "3f9a72d8e0...";

  const fingerprintStr = typeof solverJob?.execution_fingerprint === 'string' && solverJob.execution_fingerprint.length >= 10
    ? solverJob.execution_fingerprint.substring(0, 10) + "..."
    : "8b14c9ef21...";

  return (
    <header className="border-b border-slate-800 bg-slate-900/90 backdrop-blur-md px-6 py-3.5 flex flex-wrap items-center justify-between sticky top-0 z-50 gap-4">
      {/* Brand & System Title */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-600 via-blue-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
          <Activity className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="text-base font-bold tracking-tight text-white flex items-center gap-2">
            AeroSeat Certification OS
            <span className="bg-cyan-950/80 text-cyan-400 border border-cyan-800/60 text-[10px] font-mono px-2.5 py-0.5 rounded-full font-medium shadow-sm">
              v1.0.0 (Master Plan)
            </span>
          </h1>
          <p className="text-xs text-slate-400">
            14 CFR § 25.562 / SAE AS8049E / SAE ARP5765B Virtual Sled Dynamic Crash Assessment
          </p>
        </div>
      </div>

      {/* Cryptographic Hash Chain Badge & Status */}
      <div className="flex items-center gap-4 flex-wrap">
        {statusMessage && (
          <div className="hidden xl:flex items-center gap-2 text-xs font-mono bg-slate-950/90 px-3.5 py-1.5 rounded-lg border border-slate-800 text-slate-300">
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse"></span>
            <span className="truncate max-w-[260px]">{statusMessage}</span>
          </div>
        )}

        <div className="hidden lg:flex items-center gap-3 text-xs font-mono bg-slate-950/80 px-4 py-2 rounded-xl border border-slate-800 shadow-inner">
          <div className="flex items-center gap-2 text-slate-300">
            <Lock className="w-3.5 h-3.5 text-cyan-400" />
            <span className="text-slate-500">Config:</span>
            <span className="text-cyan-400 font-semibold truncate max-w-[110px]" title={simConfig?.configuration_hash || ""}>
              {configHashStr}
            </span>
          </div>
          <div className="w-px h-3.5 bg-slate-800" />
          <div className="flex items-center gap-2 text-slate-300">
            <Hash className="w-3.5 h-3.5 text-emerald-400" />
            <span className="text-slate-500">Fingerprint:</span>
            <span className="text-emerald-400 font-semibold truncate max-w-[110px]" title={solverJob?.execution_fingerprint || ""}>
              {fingerprintStr}
            </span>
          </div>
        </div>

        {/* Action Controls */}
        <button
          onClick={handleGoldenRegression}
          disabled={isLoading}
          className="text-xs font-medium px-3.5 py-2 rounded-xl border border-slate-700 bg-slate-800/90 hover:bg-slate-700 text-slate-200 flex items-center gap-2 transition-all shadow-sm active:scale-95 disabled:opacity-50 cursor-pointer"
        >
          <Sparkles className="w-3.5 h-3.5 text-amber-400" />
          Contract 5 Regression Check
        </button>
      </div>
    </header>
  );
}
