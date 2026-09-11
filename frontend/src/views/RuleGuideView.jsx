import React, { useState } from 'react';
import api from '../api';
import { 
  BookOpen, 
  CheckCircle2, 
  XCircle, 
  Layers, 
  Play, 
  Sparkles, 
  ShieldCheck, 
  HelpCircle,
  ArrowRight,
  Info
} from 'lucide-react';

export default function RuleGuideView() {
  // Sandbox State
  const [serial, setSerial] = useState('MS004');
  const [ticket, setTicket] = useState('T4001');
  const [part, setPart] = useState('Front Suspension Rod');
  const [refTicketsStr, setRefTicketsStr] = useState('T4001, T4002, T4003');
  const [simResult, setSimResult] = useState(null);
  const [simLoading, setSimLoading] = useState(false);

  const handleSimulate = async () => {
    setSimLoading(true);
    try {
      const ticketsArray = refTicketsStr
        .split(',')
        .map((t) => t.trim())
        .filter(Boolean);

      const res = await api.post('/simulate_rule', {
        serial,
        ticket,
        part,
        ref_tickets: ticketsArray
      });

      setSimResult(res.data);
    } catch (err) {
      console.error(err);
      alert('Failed to simulate rule.');
    } finally {
      setSimLoading(false);
    }
  };

  return (
    <div className="space-y-12 max-w-5xl mx-auto pb-16">
      
      {/* Header */}
      <div className="text-center space-y-3 pt-4">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-xs font-semibold">
          <BookOpen className="h-3.5 w-3.5 text-indigo-400" />
          <span>FQC Logic Reference & Sandbox</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
          Validation Rules Guide & Interactive Simulator
        </h1>
        <p className="text-slate-400 text-sm max-w-2xl mx-auto">
          Understand how the rule engine determines whether each <strong className="text-slate-200">'NG to Verify'</strong> record is classified as <strong>Approved</strong> or <strong>Non-Genuine</strong>.
        </p>
      </div>

      {/* Rules Matrix Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        {/* Rule 1 Card */}
        <div className="rounded-2xl bg-slate-900/80 border border-slate-800 p-6 space-y-4 flex flex-col justify-between shadow-xl">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                Rule 1
              </span>
              <CheckCircle2 className="h-5 w-5 text-emerald-400" />
            </div>
            <h3 className="text-base font-bold text-white">Multiple Tickets (Same Part)</h3>
            <p className="text-xs text-slate-300 leading-relaxed">
              If the same <strong>Machine Serial Number</strong> has <strong>two or more different Ticket Numbers for the same part/category</strong> in Reference Data:
            </p>
            <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-800 font-mono text-xs text-slate-300 space-y-1">
              <div>MS001 &rarr; T1001 (Drain Pump)</div>
              <div>MS001 &rarr; T1002 (Drain Pump)</div>
              <div className="text-emerald-400 font-bold pt-1 border-t border-slate-800">&rArr; Classified: Approved</div>
            </div>
          </div>
          <div className="text-[11px] text-slate-400">
            Requires &ge; 2 distinct tickets logged for the evaluated part.
          </div>
        </div>

        {/* Rule 2 Card */}
        <div className="rounded-2xl bg-slate-900/80 border border-slate-800 p-6 space-y-4 flex flex-col justify-between shadow-xl">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-rose-500/10 text-rose-400 border border-rose-500/20">
                Rule 2
              </span>
              <XCircle className="h-5 w-5 text-rose-400" />
            </div>
            <h3 className="text-base font-bold text-white">Single Ticket / Diff Parts</h3>
            <p className="text-xs text-slate-300 leading-relaxed">
              If the machine only has <strong>one ticket for that part</strong> (even if multiple tickets exist for other parts):
            </p>
            <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-800 font-mono text-xs text-slate-300 space-y-1">
              <div>MS010 &rarr; T1010 (Inlet Valve)</div>
              <div>MS010 &rarr; T1011 (Drain Pump)</div>
              <div className="text-rose-400 font-bold pt-1 border-t border-slate-800">&rArr; Classified: Non-Genuine</div>
            </div>
          </div>
          <div className="text-[11px] text-slate-400">
            Different parts on the same machine do not approve each other.
          </div>
        </div>

        {/* Special Rule Card: Suspension Rod */}
        <div className="rounded-2xl bg-gradient-to-b from-slate-900 to-purple-950/20 border border-purple-500/30 p-6 space-y-4 flex flex-col justify-between shadow-xl">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-purple-500/20 text-purple-300 border border-purple-500/30">
                Special Rule
              </span>
              <Layers className="h-5 w-5 text-purple-400" />
            </div>
            <h3 className="text-base font-bold text-white">Suspension Rod Pairing</h3>
            <p className="text-xs text-slate-300 leading-relaxed">
              Front & Rear rods sharing the same ticket count as <strong>ONE ticket</strong>. To be Approved, must have <strong>&ge; 2 additional suspension tickets</strong>.
            </p>
            <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-800 font-mono text-xs text-slate-300 space-y-1">
              <div>Front Rod (T4001) + Rear Rod (T4001)</div>
              <div className="text-slate-400">+ T4002 + T4003 (2 extra)</div>
              <div className="text-emerald-400 font-bold pt-1 border-t border-slate-800">&rArr; Classified: Approved</div>
            </div>
          </div>
          <div className="text-[11px] text-purple-300/80">
            All suspension variations (Front/Rear/Damper) group under one category.
          </div>
        </div>

      </div>

      {/* Interactive Sandbox Simulator */}
      <div className="rounded-3xl bg-slate-900/90 border border-slate-800 p-6 sm:p-8 shadow-2xl space-y-6">
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-indigo-500/20 text-indigo-400">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">Interactive Rule Sandbox</h2>
              <p className="text-xs text-slate-400">Test any combination of Serial Number, Part Name, and Reference Tickets in real time.</p>
            </div>
          </div>

          <button
            onClick={handleSimulate}
            disabled={simLoading}
            className="px-5 py-2.5 rounded-xl font-bold text-xs text-white bg-indigo-600 hover:bg-indigo-500 active:scale-95 transition flex items-center gap-2 cursor-pointer shadow-md shadow-indigo-600/30"
          >
            <Play className="h-3.5 w-3.5 fill-white" />
            <span>{simLoading ? 'Evaluating...' : 'Run Simulation'}</span>
          </button>
        </div>

        {/* Inputs */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5">
              Machine Serial No.
            </label>
            <input
              type="text"
              value={serial}
              onChange={(e) => setSerial(e.target.value)}
              className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-sm text-slate-100 font-mono focus:border-indigo-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5">
              Current Ticket No. (Mahavir)
            </label>
            <input
              type="text"
              value={ticket}
              onChange={(e) => setTicket(e.target.value)}
              className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-sm text-slate-100 font-mono focus:border-indigo-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5">
              Part Description
            </label>
            <input
              type="text"
              value={part}
              onChange={(e) => setPart(e.target.value)}
              placeholder="e.g. Front Suspension Rod or Drain Pump"
              className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-sm text-slate-100 focus:border-indigo-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5">
              Reference File Tickets (comma-separated)
            </label>
            <input
              type="text"
              value={refTicketsStr}
              onChange={(e) => setRefTicketsStr(e.target.value)}
              placeholder="T4001, T4002, T4003"
              className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-sm text-slate-100 font-mono focus:border-indigo-500 focus:outline-none"
            />
          </div>

        </div>

        {/* Quick Presets */}
        <div className="flex items-center gap-2 overflow-x-auto text-xs text-slate-400 pt-1">
          <span className="font-semibold text-slate-300">Quick Presets:</span>
          <button
            onClick={() => {
              setSerial('MS001');
              setTicket('T1001');
              setPart('Drain Pump');
              setRefTicketsStr('T1001, T1002');
            }}
            className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 transition"
          >
            Same Part (2 Tickets &rarr; Approved)
          </button>
          <button
            onClick={() => {
              setSerial('MS002');
              setTicket('T2001');
              setPart('Pulsator');
              setRefTicketsStr('T2001');
            }}
            className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 transition"
          >
            Single Ticket (1 Ticket &rarr; Non-Genuine)
          </button>
          <button
            onClick={() => {
              setSerial('MS003');
              setTicket('T3001');
              setPart('Front Suspension Rod');
              setRefTicketsStr('T3001');
            }}
            className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 transition"
          >
            Suspension Rod (Paired Only &rarr; Non-Genuine)
          </button>
          <button
            onClick={() => {
              setSerial('MS004');
              setTicket('T4001');
              setPart('Front Suspension Rod');
              setRefTicketsStr('T4001, T4002, T4003');
            }}
            className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 transition"
          >
            Suspension Rod (2 Extra &rarr; Approved)
          </button>
        </div>

        {/* Simulation Output Card */}
        {simResult && (
          <div className="p-5 rounded-2xl bg-slate-950 border border-slate-800 space-y-4 animate-in fade-in duration-200">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <span className="text-xs uppercase font-bold text-slate-400">Simulation Result</span>
              <div>
                {simResult.classification === 'Approved' ? (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                    <CheckCircle2 className="h-4 w-4" /> Approved
                  </span>
                ) : simResult.classification === 'Non-Genuine' ? (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-rose-500/20 text-rose-400 border border-rose-500/30">
                    <XCircle className="h-4 w-4" /> Non-Genuine
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30">
                    Manual Review
                  </span>
                )}
              </div>
            </div>

            <div className="space-y-2">
              <p className="text-sm font-semibold text-slate-200">
                {simResult.reason}
              </p>
              
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs text-slate-400 pt-2 font-mono">
                <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
                  <span className="text-slate-500 block text-[10px] uppercase">Part Type</span>
                  <span className="text-slate-200 font-bold">{simResult.is_suspension ? 'Suspension Rod (Pair)' : 'Normal Part'}</span>
                </div>
                <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
                  <span className="text-slate-500 block text-[10px] uppercase">Reference Tickets</span>
                  <span className="text-slate-200 font-bold">{simResult.ref_tickets?.join(', ') || 'None'}</span>
                </div>
                <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
                  <span className="text-slate-500 block text-[10px] uppercase">Decision Engine</span>
                  <span className="text-indigo-300 font-bold">{simResult.status}</span>
                </div>
              </div>
            </div>
          </div>
        )}

      </div>

    </div>
  );
}
