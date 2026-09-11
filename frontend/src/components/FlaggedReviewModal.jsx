import React from 'react';
import { X, AlertTriangle, HelpCircle, FileSpreadsheet, ArrowUpRight } from 'lucide-react';

export default function FlaggedReviewModal({ isOpen, onClose, records = [] }) {
  if (!isOpen) return null;

  const flagged = records.filter((r) => r.classification === 'Manual Review');

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-3xl rounded-2xl bg-slate-900 border border-slate-800 shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
        
        {/* Modal Header */}
        <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20">
              <AlertTriangle className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">
                Records Requiring Manual Review ({flagged.length})
              </h3>
              <p className="text-xs text-slate-400">
                These records could not be automatically validated due to missing or unmapped data.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-5 overflow-y-auto space-y-4">
          {flagged.length === 0 ? (
            <div className="text-center py-10 text-slate-400">
              <p className="text-sm font-medium text-emerald-400">
                No flagged records! All "NG to Verify" entries were successfully processed.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {flagged.map((rec, i) => (
                <div 
                  key={i} 
                  className="p-4 rounded-xl bg-slate-950/80 border border-amber-500/20 space-y-2 hover:border-amber-500/40 transition"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-amber-500/10 text-amber-300 border border-amber-500/20">
                        {rec.sheet_name ? `${rec.sheet_name} • Row #${rec.row_idx}` : `Row #${rec.row_idx}`}
                      </span>
                      <span className="text-sm font-bold text-slate-100 font-mono">
                        {rec.serial || 'Missing Serial Number'}
                      </span>
                      {rec.ticket && (
                        <span className="text-xs font-mono text-slate-400">
                          (Ticket: {rec.ticket})
                        </span>
                      )}
                    </div>
                    <span className="text-[11px] font-semibold uppercase tracking-wider text-amber-400">
                      {rec.status === 'NOT_FOUND_IN_REF' ? 'Not Found in Ref' : 'Missing Info'}
                    </span>
                  </div>

                  <p className="text-xs text-slate-300">
                    <strong className="text-slate-400">Reason: </strong> {rec.reason}
                  </p>

                  <div className="text-[11px] text-slate-400 pt-1 border-t border-slate-900 flex items-center justify-between">
                    <span>Part: {rec.part || '—'}</span>
                    <span className="text-amber-300 font-medium">Action: Preserved original remark in output file</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="p-4 border-t border-slate-800 bg-slate-950/60 flex items-center justify-between">
          <p className="text-xs text-slate-400">
            Tip: These records are also exported in the <em>'Manual Review Required'</em> sheet of the QC workbook.
          </p>
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold transition"
          >
            Close
          </button>
        </div>

      </div>
    </div>
  );
}
