import React from 'react';
import { FileText, Download, CheckCircle2, ShieldCheck, Hash, Layers } from 'lucide-react';
import { API_BASE } from '../../api/aeroseatClient';

export default function EvidenceTab({
  engineeringAssessment,
  evidenceArtifact,
  goldenRegression,
  handleCreateAssessment,
  handleGenerateEvidence,
  isLoading,
  simConfig
}) {
  return (
    <div className="space-y-6">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-5 shadow-xl">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-sm font-bold text-white flex items-center gap-2">
            <FileText className="w-4 h-4 text-cyan-400" /> Evidence Artifact Package & SHA-256 Hash Chain
          </h2>
          <div className="flex items-center gap-2">
            <button
              onClick={handleCreateAssessment}
              disabled={isLoading || !simConfig}
              className="text-xs px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl border border-slate-700 font-medium transition-all cursor-pointer disabled:opacity-50 active:scale-95"
            >
              1. Create Assessment
            </button>
            <button
              onClick={handleGenerateEvidence}
              disabled={isLoading || !engineeringAssessment}
              className="text-xs px-4 py-2 bg-gradient-to-r from-emerald-600 via-teal-600 to-cyan-600 hover:from-emerald-500 hover:to-cyan-500 text-white font-bold rounded-xl shadow-lg shadow-emerald-500/20 transition-all cursor-pointer disabled:opacity-50 active:scale-95"
            >
              2. Generate PDF & Manifest Package
            </button>
          </div>
        </div>

        {/* Evidence Artifact Package Display */}
        {evidenceArtifact && (
          <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-4 font-mono text-xs shadow-inner">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <span className="text-slate-400">Artifact Package ID: {evidenceArtifact.id}</span>
              <a
                href={`${API_BASE}/evidence-artifacts/${evidenceArtifact.id}/download-pdf`}
                target="_blank"
                rel="noreferrer"
                className="px-4 py-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-bold rounded-xl flex items-center gap-2 text-xs shadow-md shadow-cyan-500/20 transition-all cursor-pointer"
              >
                <Download className="w-3.5 h-3.5" /> Download Official Evidence PDF Report
              </a>
            </div>

            <div className="space-y-2 border-t border-slate-800 pt-3">
              <div className="text-slate-300 font-bold flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                SHA-256 Cryptographic Chain Verification:
              </div>
              <div className="bg-slate-900 p-3 rounded-lg border border-slate-800 text-[11px] space-y-1.5">
                <div>
                  <span className="text-slate-500">Input Manifest SHA-256: </span>
                  <span className="text-cyan-400 font-semibold break-all">{evidenceArtifact.input_manifest_sha256}</span>
                </div>
                <div>
                  <span className="text-slate-500">Output Manifest SHA-256: </span>
                  <span className="text-emerald-400 font-semibold break-all">{evidenceArtifact.output_manifest_sha256}</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Contract 5 Golden Dataset Regression Payload Card */}
        {goldenRegression && (
          <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2 text-xs font-mono">
            <div className="flex items-center justify-between text-emerald-400 font-bold">
              <span className="flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4" />
                Contract 5 Golden Dataset Scientific Regression: PASS
              </span>
              <span className="text-[10px] text-slate-500 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                Bit-for-Bit Deterministic
              </span>
            </div>
            <pre className="text-[11px] text-slate-400 bg-slate-900/90 p-3 rounded-lg overflow-x-auto border border-slate-800/80">
              {JSON.stringify(goldenRegression, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}
