import React from 'react';
import { 
  CheckCircle2, 
  BarChart3, 
  BookOpen, 
  Download, 
  ShieldCheck, 
  Server,
  FileSpreadsheet
} from 'lucide-react';

export default function Navbar({ activeTab, setActiveTab, backendStatus, onRefreshHealth, onDownloadSample }) {
  return (
    <header className="sticky top-0 z-40 w-full border-b border-slate-800/80 bg-slate-950/85 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          
          {/* Logo & Brand */}
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/25">
              <ShieldCheck className="h-5 w-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-slate-100 text-lg tracking-tight">
                  FQC Validator
                </span>
                <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                  v1.0
                </span>
              </div>
              <p className="text-xs text-slate-400 font-medium hidden sm:block">
                Mahavir & Reference "NG to Verify" Rule Engine
              </p>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="flex items-center gap-1.5 bg-slate-900/90 p-1.5 rounded-xl border border-slate-800/80">
            <button
              onClick={() => setActiveTab('validator')}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs sm:text-sm font-medium transition-all ${
                activeTab === 'validator'
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30 font-semibold'
                  : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
              }`}
            >
              <CheckCircle2 className="h-4 w-4" />
              <span>Validate & Process</span>
            </button>

            <button
              onClick={() => setActiveTab('dashboard')}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs sm:text-sm font-medium transition-all ${
                activeTab === 'dashboard'
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30 font-semibold'
                  : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
              }`}
            >
              <BarChart3 className="h-4 w-4" />
              <span>QC Audit & Stats</span>
            </button>

            <button
              onClick={() => setActiveTab('guide')}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs sm:text-sm font-medium transition-all ${
                activeTab === 'guide'
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30 font-semibold'
                  : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
              }`}
            >
              <BookOpen className="h-4 w-4" />
              <span>Rule Guide & Sandbox</span>
            </button>
          </nav>

          {/* Action Tools & Status */}
          <div className="flex items-center gap-2.5">
            <button
              onClick={onDownloadSample}
              title="Download Sample Mahavir & Reference Excel Files"
              className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-800/80 hover:bg-slate-700/80 text-slate-200 border border-slate-700/60 transition shadow-sm hover:shadow"
            >
              <FileSpreadsheet className="h-3.5 w-3.5 text-emerald-400" />
              <span>Sample Data</span>
              <Download className="h-3 w-3 text-slate-400" />
            </button>

            <button
              onClick={onRefreshHealth}
              title="Click to check backend status"
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-900 hover:bg-slate-800 border border-slate-800 text-[11px] font-medium text-slate-300 transition cursor-pointer"
            >
              <span className={`h-2 w-2 rounded-full ${backendStatus ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`} />
              <span className="hidden lg:inline">{backendStatus ? 'Backend Online' : 'Connecting...'}</span>
            </button>
          </div>

        </div>
      </div>
    </header>
  );
}
