import React from 'react';
import { 
  FileCheck2, 
  CheckCircle2, 
  XCircle, 
  AlertTriangle, 
  Layers, 
  FileSearch,
  ArrowRight
} from 'lucide-react';

export default function QCStatsCards({ stats, onOpenFlaggedModal, onSelectFilter }) {
  if (!stats) return null;

  const {
    total_rows = 0,
    total_ng_found = 0,
    approved_count = 0,
    non_genuine_count = 0,
    suspension_count = 0,
    not_found_count = 0,
    manual_review_count = 0
  } = stats;

  const approvedPct = total_ng_found > 0 ? Math.round((approved_count / total_ng_found) * 100) : 0;
  const nonGenPct = total_ng_found > 0 ? Math.round((non_genuine_count / total_ng_found) * 100) : 0;
  const manualPct = total_ng_found > 0 ? Math.round((manual_review_count / total_ng_found) * 100) : 0;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      
      {/* 1. Total NG Found */}
      <div 
        onClick={() => onSelectFilter && onSelectFilter('ALL')}
        className="cursor-pointer group relative overflow-hidden rounded-2xl bg-gradient-to-b from-slate-900 to-slate-950 p-5 border border-slate-800 hover:border-slate-700 transition shadow-lg"
      >
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            'NG to Verify' Target
          </span>
          <div className="p-2 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <FileSearch className="h-5 w-5" />
          </div>
        </div>
        <div className="mt-3 flex items-baseline gap-2">
          <span className="text-3xl font-extrabold text-white tracking-tight">
            {total_ng_found}
          </span>
          <span className="text-xs text-slate-400 font-mono">
            of {total_rows} total rows
          </span>
        </div>
        <div className="mt-2 text-xs text-slate-400 flex items-center gap-1 group-hover:text-indigo-400 transition">
          <span>Targeted for rule validation</span>
        </div>
      </div>

      {/* 2. Classified Approved */}
      <div 
        onClick={() => onSelectFilter && onSelectFilter('Approved')}
        className="cursor-pointer group relative overflow-hidden rounded-2xl bg-gradient-to-b from-slate-900 to-slate-950 p-5 border border-emerald-900/40 hover:border-emerald-500/40 transition shadow-lg"
      >
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-wider text-emerald-400">
            Approved
          </span>
          <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="h-5 w-5" />
          </div>
        </div>
        <div className="mt-3 flex items-baseline gap-2">
          <span className="text-3xl font-extrabold text-emerald-400 tracking-tight">
            {approved_count}
          </span>
          <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            {approvedPct}%
          </span>
        </div>
        <div className="mt-2 text-xs text-slate-400 flex items-center gap-1">
          <span>Multi-ticket & verified pairs</span>
        </div>
      </div>

      {/* 3. Classified Non-Genuine */}
      <div 
        onClick={() => onSelectFilter && onSelectFilter('Non-Genuine')}
        className="cursor-pointer group relative overflow-hidden rounded-2xl bg-gradient-to-b from-slate-900 to-slate-950 p-5 border border-rose-900/40 hover:border-rose-500/40 transition shadow-lg"
      >
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-wider text-rose-400">
            Non-Genuine
          </span>
          <div className="p-2 rounded-xl bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <XCircle className="h-5 w-5" />
          </div>
        </div>
        <div className="mt-3 flex items-baseline gap-2">
          <span className="text-3xl font-extrabold text-rose-400 tracking-tight">
            {non_genuine_count}
          </span>
          <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20">
            {nonGenPct}%
          </span>
        </div>
        <div className="mt-2 text-xs text-slate-400 flex items-center gap-1">
          <span>Single ticket or paired only</span>
        </div>
      </div>

      {/* 4. Flagged for Manual Review */}
      <div 
        onClick={onOpenFlaggedModal}
        className={`cursor-pointer group relative overflow-hidden rounded-2xl p-5 border transition shadow-lg ${
          manual_review_count > 0 
            ? 'bg-gradient-to-b from-slate-900 to-amber-950/20 border-amber-500/40 hover:border-amber-500' 
            : 'bg-gradient-to-b from-slate-900 to-slate-950 border-slate-800'
        }`}
      >
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-wider text-amber-400">
            Manual Review
          </span>
          <div className="p-2 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <AlertTriangle className="h-5 w-5" />
          </div>
        </div>
        <div className="mt-3 flex items-baseline gap-2">
          <span className="text-3xl font-extrabold text-amber-400 tracking-tight">
            {manual_review_count}
          </span>
          {manual_review_count > 0 && (
            <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30">
              Needs QA
            </span>
          )}
        </div>
        <div className="mt-2 text-xs text-amber-300/80 flex items-center gap-1 group-hover:text-amber-300 transition">
          <span>{not_found_count} not in ref / missing data</span>
          <ArrowRight className="h-3 w-3 ml-auto group-hover:translate-x-0.5 transition" />
        </div>
      </div>

    </div>
  );
}
