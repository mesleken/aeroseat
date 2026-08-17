import React from 'react';
import { useCertificationPipeline } from './hooks/useCertificationPipeline';
import AppHeader from './components/layout/AppHeader';
import TabNavigation from './components/layout/TabNavigation';
import ProjectsCadTab from './components/tabs/ProjectsCadTab';
import ScenarioQATab from './components/tabs/ScenarioQATab';
import SolverEngineTab from './components/tabs/SolverEngineTab';
import InjuryMetricsTab from './components/tabs/InjuryMetricsTab';
import PostProcessorTab from './components/tabs/PostProcessorTab';
import CorrelationTab from './components/tabs/CorrelationTab';
import EvidenceTab from './components/tabs/EvidenceTab';
import ThreeSeatViewer from './components/ThreeSeatViewer';
import CertReadinessPanel from './components/panels/CertReadinessPanel';
import { Eye } from 'lucide-react';

export default function App() {
  const pipeline = useCertificationPipeline();

  const renderActiveTab = () => {
    switch (pipeline.activeTab) {
      case "projects":
        return <ProjectsCadTab {...pipeline} />;
      case "scenario":
        return <ScenarioQATab {...pipeline} />;
      case "simulation":
        return <SolverEngineTab {...pipeline} />;
      case "metrics":
        return <InjuryMetricsTab {...pipeline} />;
      case "postprocessor":
        return <PostProcessorTab {...pipeline} />;
      case "correlation":
        return <CorrelationTab {...pipeline} />;
      case "evidence":
        return <EvidenceTab {...pipeline} />;
      default:
        return <ProjectsCadTab {...pipeline} />;
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-cyan-500 selection:text-slate-950">
      <AppHeader {...pipeline} />
      <TabNavigation activeTab={pipeline.activeTab} setActiveTab={pipeline.setActiveTab} />
      <main className="flex-1 p-6 grid grid-cols-1 lg:grid-cols-12 gap-6 overflow-y-auto max-w-[1920px] mx-auto w-full">
        {/* Left Column: Active Stage Tab Workflow (5 cols) */}
        <div className="lg:col-span-5 flex flex-col gap-6">
          {renderActiveTab()}
        </div>

        {/* Right Column: 3D Seat Viewer & Live Readiness Status Card (7 cols) */}
        <div className="lg:col-span-7 flex flex-col gap-6">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 flex flex-col gap-3 shadow-xl">
            <div className="flex items-center justify-between text-xs font-medium text-slate-300">
              <span className="flex items-center gap-1.5 font-semibold">
                <Eye className="w-4 h-4 text-cyan-400" /> Virtual Crash Sled & Mesh Display
              </span>
              <span className="text-[11px] text-slate-500 font-mono">14 CFR § 25.562 / SAE AS8049E</span>
            </div>
            <ThreeSeatViewer
              deformationProgress={pipeline.animProgress}
              animationData={pipeline.animationData}
              yawAngle={pipeline.yawAngle}
              pitchAngle={pipeline.pitchAngle}
              rollAngle={pipeline.rollAngle}
              dummyType={pipeline.dummyType}
              testType={pipeline.testType}
              modelRevision={pipeline.modelRevision}
              uploadedCadFile={pipeline.uploadedCadFile}
              dummyOffset={pipeline.dummyOffset}
              setDummyOffset={pipeline.setDummyOffset}
              seatOffset={pipeline.seatOffset}
              setSeatOffset={pipeline.setSeatOffset}
            />
          </div>

          <CertReadinessPanel {...pipeline} />
        </div>
      </main>
    </div>
  );
}
