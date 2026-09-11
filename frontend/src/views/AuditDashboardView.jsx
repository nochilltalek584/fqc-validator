import React, { useState, useMemo } from 'react';
import { 
  BarChart3, 
  PieChart as PieIcon, 
  AlertTriangle, 
  CheckCircle2, 
  XCircle, 
  Layers, 
  Download,
  Info
} from 'lucide-react';
import QCStatsCards from '../components/QCStatsCards';
import AuditTable from '../components/AuditTable';

export default function AuditDashboardView({ stats, onOpenFlaggedModal }) {
  const [selectedFilter, setSelectedFilter] = useState('ALL');
  const [hoveredSlice, setHoveredSlice] = useState(null);

  if (!stats) {
    return (
      <div className="text-center py-20 max-w-lg mx-auto space-y-4">
        <div className="h-16 w-16 mx-auto rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-500">
          <BarChart3 className="h-8 w-8" />
        </div>
        <h2 className="text-xl font-bold text-white">No Validation Data Yet</h2>
        <p className="text-sm text-slate-400">
          Please upload your Mahavir and Reference files in the <strong>Validate & Process</strong> tab to generate QC analytics and audit logs.
        </p>
      </div>
    );
  }

  const {
    total_rows = 0,
    total_ng_found = 0,
    approved_count = 0,
    non_genuine_count = 0,
    suspension_count = 0,
    not_found_count = 0,
    manual_review_count = 0,
    records = []
  } = stats;

  // Breakdown metrics
  const normalApproved = records.filter(r => !r.is_suspension && r.classification === 'Approved').length;
  const normalNonGen = records.filter(r => !r.is_suspension && r.classification === 'Non-Genuine').length;
  const suspApproved = records.filter(r => r.is_suspension && r.classification === 'Approved').length;
  const suspNonGen = records.filter(r => r.is_suspension && r.classification === 'Non-Genuine').length;

  const maxBarVal = Math.max(normalApproved, normalNonGen, suspApproved, suspNonGen, 1);

  // SVG Pie Chart Math
  const totalSlices = (approved_count + non_genuine_count + manual_review_count) || 1;
  const approvedAngle = (approved_count / totalSlices) * 360;
  const nonGenAngle = (non_genuine_count / totalSlices) * 360;
  const manualAngle = (manual_review_count / totalSlices) * 360;

  // Helper to calculate SVG donut arcs
  const getCoordinatesForPercent = (percent) => {
    const x = Math.cos(2 * Math.PI * percent);
    const y = Math.sin(2 * Math.PI * percent);
    return [x, y];
  };

  const approvedPct = Math.round((approved_count / totalSlices) * 100);
  const nonGenPct = Math.round((non_genuine_count / totalSlices) * 100);
  const manualPct = Math.round((manual_review_count / totalSlices) * 100);

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-16">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight flex items-center gap-2.5">
            <BarChart3 className="h-7 w-7 text-indigo-400" />
            Quality Control & Audit Dashboard
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Detailed validation analytics, rule decision traces, and flagged records inspector.
          </p>
        </div>

        {manual_review_count > 0 && (
          <button
            onClick={onOpenFlaggedModal}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold bg-amber-500/10 text-amber-300 border border-amber-500/30 hover:bg-amber-500/20 transition self-start sm:self-auto cursor-pointer"
          >
            <AlertTriangle className="h-4 w-4 text-amber-400" />
            <span>Review {manual_review_count} Flagged Records</span>
          </button>
        )}
      </div>

      {/* KPI Stats Cards */}
      <QCStatsCards 
        stats={stats} 
        onOpenFlaggedModal={onOpenFlaggedModal} 
        onSelectFilter={setSelectedFilter} 
      />

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Chart 1: Visual Pie & Distribution Breakdown */}
        <div className="rounded-2xl bg-slate-900/80 border border-slate-800 p-5 shadow-xl flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
              <PieIcon className="h-4 w-4 text-indigo-400" />
              Outcome Distribution
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Proportion of updated FQC remarks
            </p>
          </div>

          {/* Donut Chart Visualizer */}
          <div className="my-6 flex flex-col items-center justify-center">
            <div className="relative h-44 w-44 flex items-center justify-center">
              <svg viewBox="-1 -1 2 2" className="h-full w-full -rotate-90">
                {/* Approved Slice */}
                {approved_count > 0 && (
                  <circle
                    cx="0"
                    cy="0"
                    r="0.75"
                    fill="transparent"
                    stroke="#10B981"
                    strokeWidth="0.35"
                    strokeDasharray={`${(approved_count / totalSlices) * 4.71} 4.71`}
                    strokeDashoffset="0"
                    className="transition-all duration-300 hover:opacity-80"
                  />
                )}
                {/* Non-Genuine Slice */}
                {non_genuine_count > 0 && (
                  <circle
                    cx="0"
                    cy="0"
                    r="0.75"
                    fill="transparent"
                    stroke="#F43F5E"
                    strokeWidth="0.35"
                    strokeDasharray={`${(non_genuine_count / totalSlices) * 4.71} 4.71`}
                    strokeDashoffset={`-${(approved_count / totalSlices) * 4.71}`}
                    className="transition-all duration-300 hover:opacity-80"
                  />
                )}
                {/* Manual Review Slice */}
                {manual_review_count > 0 && (
                  <circle
                    cx="0"
                    cy="0"
                    r="0.75"
                    fill="transparent"
                    stroke="#F59E0B"
                    strokeWidth="0.35"
                    strokeDasharray={`${(manual_review_count / totalSlices) * 4.71} 4.71`}
                    strokeDashoffset={`-${((approved_count + non_genuine_count) / totalSlices) * 4.71}`}
                    className="transition-all duration-300 hover:opacity-80"
                  />
                )}
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                <span className="text-2xl font-extrabold text-white">{total_ng_found}</span>
                <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Processed</span>
              </div>
            </div>

            {/* Legend & Stats */}
            <div className="w-full grid grid-cols-3 gap-2 mt-4 text-center">
              <div className="p-2 rounded-xl bg-slate-950/60 border border-emerald-500/20">
                <span className="text-[11px] font-semibold text-emerald-400 flex items-center justify-center gap-1">
                  <span className="h-2 w-2 rounded-full bg-emerald-400" /> Approved
                </span>
                <span className="text-base font-bold text-white block mt-0.5">{approved_count}</span>
                <span className="text-[10px] text-slate-400">{approvedPct}%</span>
              </div>

              <div className="p-2 rounded-xl bg-slate-950/60 border border-rose-500/20">
                <span className="text-[11px] font-semibold text-rose-400 flex items-center justify-center gap-1">
                  <span className="h-2 w-2 rounded-full bg-rose-400" /> Non-Gen
                </span>
                <span className="text-base font-bold text-white block mt-0.5">{non_genuine_count}</span>
                <span className="text-[10px] text-slate-400">{nonGenPct}%</span>
              </div>

              <div className="p-2 rounded-xl bg-slate-950/60 border border-amber-500/20">
                <span className="text-[11px] font-semibold text-amber-400 flex items-center justify-center gap-1">
                  <span className="h-2 w-2 rounded-full bg-amber-400" /> Review
                </span>
                <span className="text-base font-bold text-white block mt-0.5">{manual_review_count}</span>
                <span className="text-[10px] text-slate-400">{manualPct}%</span>
              </div>
            </div>
          </div>
        </div>

        {/* Chart 2: Category Breakdown (Normal Parts vs Suspension Rods) */}
        <div className="lg:col-span-2 rounded-2xl bg-slate-900/80 border border-slate-800 p-5 shadow-xl flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
              <Layers className="h-4 w-4 text-purple-400" />
              Outcome by Category: Normal Parts vs Suspension Rods
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Comparison showing rule compliance across part categories
            </p>
          </div>

          {/* Visual Custom Bar Graph */}
          <div className="my-6 space-y-6">
            
            {/* Category 1: Normal Parts */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="font-bold text-slate-200">Normal Components (Drain Pump, Pulsator, PCB, etc.)</span>
                <span className="text-slate-400 font-mono">{normalApproved + normalNonGen} evaluated</span>
              </div>
              <div className="h-7 w-full bg-slate-950 rounded-xl overflow-hidden flex border border-slate-800">
                {normalApproved > 0 && (
                  <div 
                    style={{ width: `${(normalApproved / (normalApproved + normalNonGen || 1)) * 100}%` }}
                    className="bg-emerald-500 h-full flex items-center justify-center text-[11px] font-bold text-slate-950 px-2 transition-all"
                    title={`Approved: ${normalApproved}`}
                  >
                    Approved: {normalApproved}
                  </div>
                )}
                {normalNonGen > 0 && (
                  <div 
                    style={{ width: `${(normalNonGen / (normalApproved + normalNonGen || 1)) * 100}%` }}
                    className="bg-rose-500 h-full flex items-center justify-center text-[11px] font-bold text-white px-2 transition-all"
                    title={`Non-Genuine: ${normalNonGen}`}
                  >
                    Non-Gen: {normalNonGen}
                  </div>
                )}
              </div>
            </div>

            {/* Category 2: Suspension Rods */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="font-bold text-purple-300 flex items-center gap-1.5">
                  <span>Suspension Rod Pairs (Front & Rear)</span>
                  <span className="px-1.5 py-0.2 rounded text-[10px] bg-purple-500/20 text-purple-300 border border-purple-500/30">
                    Pair Rule
                  </span>
                </span>
                <span className="text-slate-400 font-mono">{suspApproved + suspNonGen} evaluated</span>
              </div>
              <div className="h-7 w-full bg-slate-950 rounded-xl overflow-hidden flex border border-slate-800">
                {suspApproved > 0 && (
                  <div 
                    style={{ width: `${(suspApproved / (suspApproved + suspNonGen || 1)) * 100}%` }}
                    className="bg-emerald-500 h-full flex items-center justify-center text-[11px] font-bold text-slate-950 px-2 transition-all"
                    title={`Approved (>= 2 extra tickets): ${suspApproved}`}
                  >
                    Approved: {suspApproved}
                  </div>
                )}
                {suspNonGen > 0 && (
                  <div 
                    style={{ width: `${(suspNonGen / (suspApproved + suspNonGen || 1)) * 100}%` }}
                    className="bg-rose-500 h-full flex items-center justify-center text-[11px] font-bold text-white px-2 transition-all"
                    title={`Non-Genuine (< 2 extra tickets): ${suspNonGen}`}
                  >
                    Non-Gen: {suspNonGen}
                  </div>
                )}
                {suspApproved === 0 && suspNonGen === 0 && (
                  <div className="w-full flex items-center justify-center text-xs text-slate-600">
                    No Suspension Rod records found in Mahavir file
                  </div>
                )}
              </div>
            </div>

          </div>

          <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 text-xs text-slate-300 flex items-center gap-2">
            <Info className="h-4 w-4 text-indigo-400 shrink-0" />
            <span>
              <strong>Suspension Rod Pairing:</strong> Front and Rear rods sharing the same ticket are grouped as 1 ticket and require &ge; 2 additional different tickets to classify as Approved.
            </span>
          </div>
        </div>

      </div>

      {/* Interactive Audit Table */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-bold text-white">
            Processed Records & Decision Logs ({records.length})
          </h3>
          <span className="text-xs text-slate-400">
            Click any row to view full audit explanation
          </span>
        </div>

        <AuditTable 
          records={records} 
          filter={selectedFilter} 
          onFilterChange={setSelectedFilter} 
        />
      </div>

    </div>
  );
}
