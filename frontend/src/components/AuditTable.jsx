import React, { useState, useMemo } from 'react';
import {
  Search,
  Filter,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Layers,
  FileSpreadsheet,
  Info,
  Cpu,
  Ticket
} from 'lucide-react';

export default function AuditTable({ records = [], filter, onFilterChange }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [expandedRow, setExpandedRow] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 15;

  const filteredRecords = useMemo(() => {
    return records.filter((rec) => {
      // 1. Classification filter
      if (filter === 'Approved' && rec.classification !== 'Approved') return false;
      if (filter === 'Non-Genuine' && rec.classification !== 'Non-Genuine') return false;
      if (filter === 'Manual Review' && rec.classification !== 'Manual Review') return false;
      if (filter === 'Suspension' && !rec.is_suspension) return false;

      // 2. Search term
      if (searchTerm.trim()) {
        const term = searchTerm.toLowerCase();
        const sheet = String(rec.sheet_name || '').toLowerCase();
        const serial = String(rec.serial || '').toLowerCase();
        const ticket = String(rec.ticket || '').toLowerCase();
        const part = String(rec.part || '').toLowerCase();
        const reason = String(rec.reason || '').toLowerCase();
        return sheet.includes(term) || serial.includes(term) || ticket.includes(term) || part.includes(term) || reason.includes(term);
      }

      return true;
    });
  }, [records, filter, searchTerm]);

  const totalPages = Math.ceil(filteredRecords.length / pageSize) || 1;
  const paginatedRecords = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredRecords.slice(start, start + pageSize);
  }, [filteredRecords, currentPage]);

  const getStatusBadge = (classification) => {
    if (classification === 'Approved') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          <CheckCircle2 className="h-3.5 w-3.5" /> Approved
        </span>
      );
    }
    if (classification === 'Non-Genuine') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
          <XCircle className="h-3.5 w-3.5" /> Non-Genuine
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
        <AlertTriangle className="h-3.5 w-3.5" /> Manual Review
      </span>
    );
  };

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/60 overflow-hidden shadow-xl">

      {/* Header controls: Search & Filters */}
      <div className="p-4 sm:p-5 border-b border-slate-800 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">

        {/* Search Bar */}
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search sheet, serial no, ticket, part, or reason..."
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              setCurrentPage(1);
            }}
            className="w-full pl-10 pr-4 py-2 rounded-xl bg-slate-950 border border-slate-800 text-slate-100 placeholder-slate-500 text-sm focus:outline-none focus:border-indigo-500 transition"
          />
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
          {[
            { key: 'ALL', label: `All (${records.length})` },
            { key: 'Approved', label: 'Approved' },
            { key: 'Non-Genuine', label: 'Non-Genuine' },
            { key: 'Suspension', label: 'Suspension Rods' },
            { key: 'Manual Review', label: 'Needs Review' },
          ].map(({ key, label }) => (
            <button
              key={key}
              onClick={() => {
                onFilterChange(key);
                setCurrentPage(1);
              }}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition cursor-pointer ${
                filter === key
                  ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/25'
                  : 'bg-slate-800/80 hover:bg-slate-800 text-slate-400 hover:text-slate-200'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

      </div>

      {/* Table Content */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm text-slate-300">
          <thead className="bg-slate-950/70 text-slate-400 text-xs uppercase tracking-wider border-b border-slate-800">
            <tr>
              <th className="py-3.5 px-4 text-center font-semibold">Row</th>
              <th className="py-3.5 px-4 font-semibold">Machine Serial No.</th>
              <th className="py-3.5 px-4 font-semibold">Ticket No.</th>
              <th className="py-3.5 px-4 font-semibold">Part Description</th>
              <th className="py-3.5 px-4 font-semibold">Original FQC</th>
              <th className="py-3.5 px-4 font-semibold">Validated FQC</th>
              <th className="py-3.5 px-4 font-semibold">Ref Match Tickets</th>
              <th className="py-3.5 px-4 text-right font-semibold">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {paginatedRecords.length === 0 ? (
              <tr>
                <td colSpan={8} className="py-12 text-center text-slate-400">
                  <div className="flex flex-col items-center justify-center gap-2">
                    <FileSpreadsheet className="h-8 w-8 text-slate-600" />
                    <p className="font-medium text-slate-300">No records matching your search or filter</p>
                    <p className="text-xs text-slate-500">Try changing your keywords or resetting filters</p>
                  </div>
                </td>
              </tr>
            ) : (
              paginatedRecords.map((rec) => {
                const recKey = rec.sheet_name ? `${rec.sheet_name}_${rec.row_idx}` : `${rec.row_idx}`;
                const isExpanded = expandedRow === recKey;
                return (
                  <React.Fragment key={recKey}>
                    <tr
                      onClick={() => setExpandedRow(isExpanded ? null : recKey)}
                      className={`hover:bg-slate-800/40 cursor-pointer transition ${isExpanded ? 'bg-slate-800/30' : ''
                        }`}
                    >
                      <td className="py-3 px-4 text-center font-mono text-xs text-slate-400">
                        <div className="flex items-center justify-center gap-1">
                          {rec.sheet_name && (
                            <span 
                              className="px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700/60 text-[10px] text-indigo-300 font-mono font-bold"
                              title={`Sheet: ${rec.sheet_name}`}
                            >
                              {rec.sheet_name}
                            </span>
                          )}
                          <span>#{rec.row_idx}</span>
                        </div>
                      </td>

                      <td className="py-3 px-4 font-mono font-semibold text-slate-100">
                        {rec.serial || <span className="text-amber-400 italic">Missing</span>}
                      </td>

                      <td className="py-3 px-4 font-mono text-slate-300">
                        {rec.ticket || <span className="text-slate-500">—</span>}
                      </td>

                      <td className="py-3 px-4 text-slate-200">
                        <div className="flex items-center gap-1.5">
                          <span className="truncate max-w-[180px]" title={rec.part}>
                            {rec.part || '—'}
                          </span>
                          {rec.is_suspension && (
                            <span className="shrink-0 px-1.5 py-0.5 rounded text-[10px] font-bold bg-purple-500/20 text-purple-300 border border-purple-500/30">
                              Pair
                            </span>
                          )}
                        </div>
                      </td>

                      <td className="py-3 px-4 text-slate-400 line-through decoration-slate-600">
                        {rec.original_fqc || '—'}
                      </td>

                      <td className="py-3 px-4">
                        {getStatusBadge(rec.classification)}
                      </td>

                      <td className="py-3 px-4">
                        {rec.ref_tickets && rec.ref_tickets.length > 0 ? (
                          <div className="flex flex-wrap gap-1">
                            {rec.ref_tickets.map((t, idx) => (
                              <span
                                key={`${t}_${idx}`}
                                className={`font-mono text-xs px-2 py-0.5 rounded ${t === rec.ticket
                                    ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30'
                                    : 'bg-slate-800 text-slate-300'
                                  }`}
                              >
                                {t}
                              </span>
                            ))}
                          </div>
                        ) : (
                          <span className="text-slate-500 italic">None found</span>
                        )}
                      </td>

                      <td className="py-3 px-4 text-right">
                        <button className="p-1 rounded text-slate-400 hover:text-white">
                          {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                        </button>
                      </td>
                    </tr>

                    {/* Expandable row with full audit explanation */}
                    {isExpanded && (
                      <tr className="bg-slate-950/90 border-b border-slate-800/80">
                        <td colSpan={8} className="p-4 sm:p-6">
                          <div className={`rounded-2xl border bg-gradient-to-b from-slate-900/95 via-slate-900/90 to-slate-950/95 backdrop-blur-md p-5 sm:p-6 space-y-5 shadow-2xl transition-all ${
                            rec.classification === 'Approved'
                              ? 'border-emerald-500/30 shadow-emerald-950/20'
                              : rec.classification === 'Non-Genuine'
                              ? 'border-rose-500/30 shadow-rose-950/20'
                              : 'border-amber-500/30 shadow-amber-950/20'
                          }`}>
                            
                            {/* Top Header: Decision Badge & Metadata */}
                            <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-slate-800/80">
                              <div className="flex flex-wrap items-center gap-2.5">
                                {rec.classification === 'Approved' ? (
                                  <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 shadow-sm">
                                    <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                                    VERIFIED & APPROVED
                                  </span>
                                ) : rec.classification === 'Non-Genuine' ? (
                                  <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold bg-rose-500/15 text-rose-300 border border-rose-500/30 shadow-sm">
                                    <XCircle className="h-4 w-4 text-rose-400" />
                                    CLASSIFIED NON-GENUINE
                                  </span>
                                ) : (
                                  <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold bg-amber-500/15 text-amber-300 border border-amber-500/30 shadow-sm">
                                    <AlertTriangle className="h-4 w-4 text-amber-400" />
                                    MANUAL AUDIT REQUIRED
                                  </span>
                                )}

                                {rec.is_suspension ? (
                                  <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold bg-purple-500/15 text-purple-300 border border-purple-500/30">
                                    <Layers className="h-3.5 w-3.5 text-purple-400" />
                                    Suspension Rod Pair Policy
                                  </span>
                                ) : (
                                  <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold bg-indigo-500/15 text-indigo-300 border border-indigo-500/30">
                                    <Cpu className="h-3.5 w-3.5 text-indigo-400" />
                                    Standard Component Rule
                                  </span>
                                )}
                              </div>

                              <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
                                <span className="px-2.5 py-1 rounded-lg bg-slate-800/80 border border-slate-700/60 text-slate-300 font-semibold">
                                  {rec.sheet_name ? `Sheet ${rec.sheet_name} • Row #${rec.row_idx}` : `Excel Row #${rec.row_idx}`}
                                </span>
                              </div>
                            </div>

                            {/* 4-Card Evidence & Context Grid */}
                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                              {/* Card 1: Machine Serial */}
                              <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-1">
                                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                                  Machine Serial
                                </span>
                                <div className="font-mono text-xs font-bold text-slate-200 truncate select-all" title={rec.serial}>
                                  {rec.serial || 'Not Available'}
                                </div>
                              </div>

                              {/* Card 2: Claim Ticket */}
                              <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-1">
                                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                                  Evaluating Ticket
                                </span>
                                <div className="font-mono text-xs font-bold text-indigo-300 truncate select-all" title={rec.ticket}>
                                  {rec.ticket || 'No Ticket'}
                                </div>
                              </div>

                              {/* Card 3: Part Evaluated */}
                              <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-1">
                                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                                  Component / Part
                                </span>
                                <div className="text-xs font-semibold text-slate-200 truncate" title={rec.part}>
                                  {rec.part || 'Unspecified Part'}
                                </div>
                              </div>

                              {/* Card 4: Historical Match Count */}
                              <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-1">
                                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                                  Reference Matches
                                </span>
                                <div className="flex items-center gap-1.5 text-xs font-bold">
                                  <span className={`font-mono ${
                                    (rec.ref_tickets?.length || 0) >= 2 ? 'text-emerald-400' : 'text-slate-200'
                                  }`}>
                                    {rec.ref_tickets?.length || 0} Total Ticket(s)
                                  </span>
                                  {(rec.ref_tickets?.length || 0) >= 2 ? (
                                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-semibold">
                                      ≥ 2 Met
                                    </span>
                                  ) : (
                                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-rose-500/20 text-rose-300 font-semibold">
                                      &lt; 2 Target
                                    </span>
                                  )}
                                </div>
                              </div>
                            </div>

                            {/* Audit Rationale Callout Box */}
                            <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800/90 space-y-2">
                              <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-300">
                                <Info className="h-4 w-4 text-indigo-400" />
                                Decision Trace & Rationale
                              </div>
                              <p className="text-xs sm:text-sm text-slate-200 leading-relaxed">
                                {rec.reason}
                              </p>
                            </div>

                            {/* Policy Guidance Alert for Suspension Rods */}
                            {rec.is_suspension && (
                              <div className="p-3.5 rounded-xl bg-purple-950/30 border border-purple-800/40 text-xs text-purple-200 flex items-start gap-2.5">
                                <Layers className="h-4 w-4 text-purple-400 shrink-0 mt-0.5" />
                                <div>
                                  <strong className="text-purple-300">Pairing Policy Applied: </strong>
                                  Front and Rear suspension rods sharing ticket <span className="font-mono text-purple-100 font-semibold">'{rec.ticket}'</span> are treated as 1 single repair event. Validation requires at least <strong>2 additional distinct suspension tickets</strong> in Reference history to classify as Approved.
                                </div>
                              </div>
                            )}

                            {/* Associated Reference Tickets Chips Bar */}
                            {rec.ref_tickets?.length > 0 && (
                              <div className="pt-2 border-t border-slate-800/60 space-y-2">
                                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                                  Associated Reference Tickets for Serial '{rec.serial}':
                                </span>
                                <div className="flex flex-wrap gap-1.5">
                                  {rec.ref_tickets.map((t, idx) => {
                                    const isCurrent = t === rec.ticket;
                                    return (
                                      <span
                                        key={`${t}_${idx}`}
                                        className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-mono font-medium border transition-colors ${
                                          isCurrent
                                            ? 'bg-indigo-500/20 text-indigo-200 border-indigo-500/40 font-bold shadow-sm'
                                            : 'bg-slate-800/80 text-slate-300 border-slate-700 hover:bg-slate-800'
                                        }`}
                                      >
                                        <Ticket className="h-3 w-3 text-slate-400" />
                                        {t}
                                        {isCurrent && (
                                          <span className="text-[9px] uppercase px-1 py-0.2 rounded bg-indigo-500/30 text-indigo-200 font-sans font-bold">
                                            Claim
                                          </span>
                                        )}
                                      </span>
                                    );
                                  })}
                                </div>
                              </div>
                            )}
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      {filteredRecords.length > pageSize && (
        <div className="p-4 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400 bg-slate-950/50">
          <span>
            Showing {(currentPage - 1) * pageSize + 1} to {Math.min(currentPage * pageSize, filteredRecords.length)} of {filteredRecords.length} records
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 disabled:opacity-50 disabled:cursor-not-allowed transition"
            >
              Previous
            </button>
            <span className="font-mono font-medium text-slate-200">
              Page {currentPage} of {totalPages}
            </span>
            <button
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 disabled:opacity-50 disabled:cursor-not-allowed transition"
            >
              Next
            </button>
          </div>
        </div>
      )}

    </div>
  );
}
