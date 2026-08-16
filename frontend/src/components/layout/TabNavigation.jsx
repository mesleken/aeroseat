import React from 'react';
import { Layers, ShieldCheck, Cpu, Activity, RefreshCw, FileText, BarChart3 } from 'lucide-react';

const TABS = [
  { id: "projects", label: "1. Projects & CAD", icon: Layers },
  { id: "scenario", label: "2. Scenario & Model QA", icon: ShieldCheck },
  { id: "simulation", label: "3. Solver Engine", icon: Cpu },
  { id: "metrics", label: "4. Injury Metrics", icon: Activity },
  { id: "postprocessor", label: "5. TEMA Post-Processor", icon: BarChart3 },
  { id: "correlation", label: "6. ARP5765B Correlation", icon: RefreshCw },
  { id: "evidence", label: "7. Evidence & Hash Chain", icon: FileText },
];

export default function TabNavigation({ activeTab, setActiveTab }) {
  return (
    <div className="border-b border-slate-800 bg-slate-900/60 backdrop-blur-sm px-6 flex items-center gap-1 overflow-x-auto select-none">
      {TABS.map((tab) => {
        const Icon = tab.icon;
        const isActive = activeTab === tab.id;
        return (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-3.5 text-xs font-medium border-b-2 flex items-center gap-2 transition-all whitespace-nowrap cursor-pointer ${
              isActive
                ? "border-cyan-500 text-cyan-400 bg-cyan-950/30 font-semibold"
                : "border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700"
            }`}
          >
            <Icon className={`w-3.5 h-3.5 ${isActive ? "text-cyan-400" : "text-slate-400"}`} />
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}
