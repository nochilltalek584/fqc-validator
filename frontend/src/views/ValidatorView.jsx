import React, { useState, useEffect } from 'react';
import api from '../api';
import {
  Play,
  Download,
  FileSpreadsheet,
  Archive,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  ArrowRight,
  ShieldCheck,
  FileCheck2,
  Sparkles,
  Database,
  Zap,
  Settings2,
  UploadCloud,
  Trash2,
  X,
  Layers,
  Info
} from 'lucide-react';
import FileDropzone from '../components/FileDropzone';
import QCStatsCards from '../components/QCStatsCards';

export default function ValidatorView({
  mahavirFile,
  setMahavirFile,
  referenceFile,
  setReferenceFile,
  stats,
  setStats,
  onNavigateDashboard,
  onOpenFlaggedModal
}) {
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState(null);
  const [error, setError] = useState(null);
  const [progressMsg, setProgressMsg] = useState('');
  const [executionTime, setExecutionTime] = useState(null);

  // Master Reference DB State
  const [refMode, setRefMode] = useState('preindexed'); // 'preindexed' | 'custom'
  const [refDbMeta, setRefDbMeta] = useState(null);
  const [dbLoading, setDbLoading] = useState(false);
  const [isDbModalOpen, setIsDbModalOpen] = useState(false);
  const [indexFile, setIndexFile] = useState(null);
  const [indexing, setIndexing] = useState(false);
  const [indexMessage, setIndexMessage] = useState(null);

  // Fetch Master Reference DB Status
  const fetchDbStatus = async () => {
    setDbLoading(true);
    try {
      const res = await api.get('/reference_db/status');
      setRefDbMeta(res.data);
      if (!res.data.is_indexed && refMode === 'preindexed') {
        // If DB not indexed yet, keep user notified
      }
    } catch (err) {
      console.warn('Could not fetch Master Reference DB status:', err);
    } finally {
      setDbLoading(false);
    }
  };

  useEffect(() => {
    fetchDbStatus();
  }, []);

  const handleValidate = async () => {
    if (!mahavirFile) {
      setError("Please select a Mahavir File to validate.");
      return;
    }

    if (refMode === 'custom' && !referenceFile) {
      setError("Please upload a Reference File or switch to the Pre-Indexed Master Database.");
      return;
    }

    if (refMode === 'preindexed' && (!refDbMeta || !refDbMeta.is_indexed)) {
      setError("Master Reference Database is not yet initialized. Please upload/index a Master Reference file or switch to Custom Upload mode.");
      return;
    }

    setError(null);
    setLoading(true);
    setExecutionTime(null);
    const startTime = performance.now();

    setProgressMsg('Reading Mahavir file...');
    const timer1 = setTimeout(() => setProgressMsg('Querying DuckDB Reference Engine...'), 400);
    const timer2 = setTimeout(() => setProgressMsg('Evaluating "NG to Verify" rules...'), 900);

    try {
      const formData = new FormData();
      formData.append("mahavir", mahavirFile);
      if (refMode === 'custom' && referenceFile) {
        formData.append("reference", referenceFile);
      }

      const res = await api.post("/validate", formData, {
        timeout: 300000
      });

      const elapsed = ((performance.now() - startTime) / 1000).toFixed(2);
      setExecutionTime(elapsed);

      if (res.data && res.data.stats) {
        setStats(res.data.stats);
      }
    } catch (err) {
      console.error('Validation error:', err);
      let msg = "An error occurred during validation.";
      if (err.code === 'ECONNABORTED') {
        msg = "Request timed out. The file might be extremely large or the backend server is busy.";
      } else if (err.response?.data?.error) {
        msg = err.response.data.error;
      } else if (err.message) {
        msg = err.message;
      }
      setError(msg);
    } finally {
      clearTimeout(timer1);
      clearTimeout(timer2);
      setLoading(false);
      setProgressMsg('');
    }
  };

  const handleDownload = async (type) => {
    if (!mahavirFile) return;

    setDownloading(type);
    try {
      const formData = new FormData();
      formData.append("mahavir", mahavirFile);
      if (refMode === 'custom' && referenceFile) {
        formData.append("reference", referenceFile);
      }
      formData.append("type", type);

      const res = await api.post("/download_file", formData, {
        responseType: "blob"
      });

      let filename = "processed_mahavir.xlsx";
      let mimeType = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";

      if (type === "qc") {
        filename = "qc_validation_summary.xlsx";
      } else if (type === "zip") {
        filename = "fqc_validated_package.zip";
        mimeType = "application/zip";
      }

      const blob = new Blob([res.data], { type: mimeType });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error(err);
      alert("Download failed. Please check backend server.");
    } finally {
      setDownloading(null);
    }
  };

  const handleIndexMasterDb = async () => {
    if (!indexFile) return;
    setIndexing(true);
    setIndexMessage(null);
    try {
      const formData = new FormData();
      formData.append("file", indexFile);
      const res = await api.post("/reference_db/index", formData);
      setIndexMessage({ type: 'success', text: res.data.message });
      setIndexFile(null);
      await fetchDbStatus();
    } catch (err) {
      const msg = err.response?.data?.error || err.message || "Indexing failed.";
      setIndexMessage({ type: 'error', text: msg });
    } finally {
      setIndexing(false);
    }
  };

  const handleSeedSampleDb = async () => {
    setIndexing(true);
    setIndexMessage(null);
    try {
      const res = await api.post("/reference_db/seed_sample");
      setIndexMessage({ type: 'success', text: res.data.message });
      await fetchDbStatus();
    } catch (err) {
      setIndexMessage({ type: 'error', text: err.response?.data?.error || "Seeding failed." });
    } finally {
      setIndexing(false);
    }
  };

  const handleClearDb = async () => {
    if (!window.confirm("Are you sure you want to clear the Master Reference Database?")) return;
    try {
      await api.delete("/reference_db/clear");
      setIndexMessage({ type: 'info', text: "Master Reference Database has been cleared." });
      await fetchDbStatus();
    } catch (err) {
      alert("Failed to clear database.");
    }
  };

  return (
    <div className="space-y-8 max-w-5xl mx-auto pb-12">

      {/* Header Banner */}
      <div className="text-center space-y-3 pt-4">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-xs font-semibold">
          <Sparkles className="h-3.5 w-3.5 text-indigo-400" />
          <span>High-Speed Vectorized FQC Engine</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
          Mahavir File FQC Validator
        </h1>
        <p className="text-slate-400 text-sm sm:text-base max-w-2xl mx-auto leading-relaxed">
          Validate <strong className="text-slate-200">'NG to Verify'</strong> records against multi-ticket and Suspension Rod pairing rules with 100% data preservation and sub-second DuckDB columnar lookups.
        </p>
      </div>

      {/* Master Reference Database Control & Mode Switcher */}
      <div className="rounded-2xl bg-gradient-to-r from-slate-900 via-indigo-950/30 to-slate-900 border border-indigo-500/30 p-4 sm:p-5 shadow-xl space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          
          {/* Status & Stats */}
          <div className="flex items-center gap-3.5">
            <div className={`p-2.5 rounded-xl border ${
              refDbMeta?.is_indexed
                ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                : 'bg-amber-500/10 border-amber-500/30 text-amber-400'
            }`}>
              <Database className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-bold text-white">Master Reference Database</h3>
                {refDbMeta?.is_indexed ? (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" /> Ready & Pre-Indexed
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">
                    Not Initialized
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                {refDbMeta?.is_indexed ? (
                  <span>
                    <strong className="text-slate-200">{refDbMeta.total_records?.toLocaleString()}</strong> records indexed ({refDbMeta.file_size_mb} MB) • Source: <span className="text-indigo-300 font-mono">{refDbMeta.source_filename}</span>
                  </span>
                ) : (
                  <span>Upload a Master Reference dataset or seed sample data for instant validation.</span>
                )}
              </p>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
            <button
              onClick={() => setIsDbModalOpen(true)}
              className="px-3.5 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-750 text-slate-200 border border-slate-700 hover:border-indigo-500/40 transition flex items-center gap-1.5 cursor-pointer shadow-sm"
            >
              <Settings2 className="h-3.5 w-3.5 text-indigo-400" />
              <span>Manage Master DB</span>
            </button>
          </div>

        </div>

        {/* Mode Selector Tabs */}
        <div className="pt-3 border-t border-slate-800/80 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="text-xs text-slate-400 font-medium">
            Validation Lookup Mode:
          </div>

          <div className="inline-flex p-1 rounded-xl bg-slate-950/80 border border-slate-800">
            <button
              onClick={() => setRefMode('preindexed')}
              className={`px-4 py-1.5 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 cursor-pointer ${
                refMode === 'preindexed'
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Zap className="h-3.5 w-3.5 text-amber-300 fill-amber-300" />
              <span>Use Pre-Indexed Master DB (Instant)</span>
            </button>

            <button
              onClick={() => setRefMode('custom')}
              className={`px-4 py-1.5 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 cursor-pointer ${
                refMode === 'custom'
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <UploadCloud className="h-3.5 w-3.5" />
              <span>Upload Custom Reference File</span>
            </button>
          </div>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-sm flex items-start gap-3">
          <AlertCircle className="h-5 w-5 text-rose-400 shrink-0 mt-0.5" />
          <div>
            <strong className="font-semibold">Validation Error:</strong> {error}
          </div>
        </div>
      )}

      {/* File Dropzone Section */}
      <div className="rounded-3xl bg-slate-900/80 border border-slate-800/80 p-6 sm:p-8 shadow-2xl backdrop-blur-xl space-y-6">
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div className="flex items-center gap-2.5">
            <div className="h-7 w-7 rounded-lg bg-indigo-500/20 flex items-center justify-center text-indigo-400">
              <ShieldCheck className="h-4 w-4" />
            </div>
            <h2 className="text-base font-bold text-slate-100">
              {refMode === 'preindexed' ? 'Upload Mahavir Target File' : 'Upload Source & Reference Spreadsheets'}
            </h2>
          </div>
          <span className="text-xs text-slate-400">Excel format (.xlsx, .xls)</span>
        </div>

        {refMode === 'preindexed' ? (
          /* Single Dropzone + Master DB Info Badge */
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-stretch">
            <div className="md:col-span-2">
              <FileDropzone
                label="Mahavir File (Target for Validation)"
                sublabel="Spreadsheet containing 'NG to Verify' rows to evaluate and update"
                file={mahavirFile}
                onFileSelect={setMahavirFile}
                onFileRemove={() => { setMahavirFile(null); setStats(null); }}
                accentColor="indigo"
                badgeText="Target Spreadsheet"
              />
            </div>

            {/* Side Card: Master DB Active Info */}
            <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-5 flex flex-col justify-between space-y-4">
              <div className="space-y-3">
                <div className="flex items-center gap-2 text-indigo-400 font-bold text-xs uppercase tracking-wider">
                  <Zap className="h-4 w-4 fill-indigo-400" />
                  <span>Instant Validation Active</span>
                </div>
                <h3 className="text-sm font-bold text-white">Pre-Indexed DuckDB Engine</h3>
                <p className="text-xs text-slate-300 leading-relaxed">
                  The engine will evaluate your Mahavir file directly against the persistent Master Database ({refDbMeta?.total_records?.toLocaleString() || 0} indexed records) with zero upload latency.
                </p>
                <div className="p-2.5 rounded-xl bg-slate-900 border border-slate-800/80 font-mono text-[11px] text-slate-400 space-y-1">
                  <div>Lookups: <span className="text-slate-200">Indexed Hash Table</span></div>
                  <div>Speed: <span className="text-emerald-400 font-semibold">&lt; 1.5 seconds</span></div>
                  <div>Preservation: <span className="text-slate-200">100% Data Preserved</span></div>
                </div>
              </div>

              <div className="text-[11px] text-slate-500">
                Need a one-off reference sheet? Switch to Custom Upload above.
              </div>
            </div>
          </div>
        ) : (
          /* Dual Dropzones */
          <div className="flex flex-col md:flex-row gap-6">
            <FileDropzone
              label="Mahavir File"
              sublabel="Main file containing 'NG to Verify' FQC remarks"
              file={mahavirFile}
              onFileSelect={setMahavirFile}
              onFileRemove={() => { setMahavirFile(null); setStats(null); }}
              accentColor="indigo"
              badgeText="Main Target"
            />

            <FileDropzone
              label="Custom Reference File"
              sublabel="Ad-hoc file containing Serial Numbers & Ticket Numbers"
              file={referenceFile}
              onFileSelect={setReferenceFile}
              onFileRemove={() => { setReferenceFile(null); setStats(null); }}
              accentColor="emerald"
              badgeText="Ad-Hoc Reference"
            />
          </div>
        )}

        {/* Process Action Bar */}
        <div className="pt-2 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="text-xs text-slate-400 text-center sm:text-left">
            {!mahavirFile ? (
              <span>Upload your Mahavir file above to begin validation</span>
            ) : (refMode === 'custom' && !referenceFile) ? (
              <span className="text-amber-400">Please select a Reference File or switch to Pre-Indexed Master DB</span>
            ) : (
              <span className="text-emerald-400 flex items-center gap-1.5 font-medium">
                <CheckCircle2 className="h-4 w-4" /> Ready to validate. Click below to execute rules.
              </span>
            )}
          </div>

          <button
            onClick={handleValidate}
            disabled={!mahavirFile || (refMode === 'custom' && !referenceFile) || loading}
            className="w-full sm:w-auto px-8 py-3.5 rounded-xl font-bold text-sm text-white bg-gradient-to-r from-indigo-500 via-indigo-600 to-purple-600 hover:from-indigo-600 hover:to-purple-700 active:scale-[0.98] shadow-lg shadow-indigo-500/25 disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none transition flex items-center justify-center gap-2 cursor-pointer"
          >
            {loading ? (
              <>
                <RefreshCw className="h-4 w-4 animate-spin text-indigo-200" />
                <span>{progressMsg || 'Executing Rules & Analyzing...'}</span>
              </>
            ) : (
              <>
                <Play className="h-4 w-4 fill-white" />
                <span>Validate & Process Records</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Results Section */}
      {stats && (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-300">

          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <div className="flex items-center gap-2.5">
                <h2 className="text-lg font-bold text-white flex items-center gap-2">
                  <FileCheck2 className="h-5 w-5 text-emerald-400" />
                  Validation Completed
                </h2>
                {executionTime && (
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-mono font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                    <Zap className="h-3 w-3 text-amber-300 fill-amber-300" /> {executionTime}s
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Audited {stats.total_ng_found} records with 'NG to Verify' remarks across {stats.total_rows?.toLocaleString()} total rows
                {stats.processed_sheets?.length > 1 && (
                  <span className="text-indigo-300 font-medium"> ({stats.processed_sheets.length} Sheets: {stats.processed_sheets.join(', ')})</span>
                )}.
              </p>
            </div>

            <button
              onClick={onNavigateDashboard}
              className="flex items-center gap-1.5 text-xs font-semibold text-indigo-400 hover:text-indigo-300 transition cursor-pointer"
            >
              <span>View Full QC Audit & Charts</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </button>
          </div>

          {/* Stats Cards */}
          <QCStatsCards
            stats={stats}
            onOpenFlaggedModal={onOpenFlaggedModal}
            onSelectFilter={onNavigateDashboard}
          />

          {/* Download Action Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">

            {/* Download 1: Processed Mahavir */}
            <button
              onClick={() => handleDownload('mahavir')}
              disabled={downloading !== null}
              className="group p-4 rounded-2xl bg-slate-900/90 border border-slate-800 hover:border-indigo-500/50 hover:bg-slate-850 transition text-left flex flex-col justify-between shadow-lg cursor-pointer"
            >
              <div className="flex items-center justify-between w-full">
                <div className="p-2.5 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 group-hover:scale-110 transition-transform">
                  <FileSpreadsheet className="h-5 w-5" />
                </div>
                <Download className="h-4 w-4 text-slate-400 group-hover:text-indigo-400 transition" />
              </div>
              <div className="mt-4">
                <h4 className="text-sm font-bold text-white group-hover:text-indigo-300 transition">
                  Updated Mahavir File
                </h4>
                <p className="text-xs text-slate-400 mt-1">
                  100% data preserved with updated FQC remarks (.xlsx)
                </p>
              </div>
            </button>

            {/* Download 2: Dedicated QC Report */}
            <button
              onClick={() => handleDownload('qc')}
              disabled={downloading !== null}
              className="group p-4 rounded-2xl bg-slate-900/90 border border-slate-800 hover:border-emerald-500/50 hover:bg-slate-850 transition text-left flex flex-col justify-between shadow-lg cursor-pointer"
            >
              <div className="flex items-center justify-between w-full">
                <div className="p-2.5 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 group-hover:scale-110 transition-transform">
                  <FileCheck2 className="h-5 w-5" />
                </div>
                <Download className="h-4 w-4 text-slate-400 group-hover:text-emerald-400 transition" />
              </div>
              <div className="mt-4">
                <h4 className="text-sm font-bold text-white group-hover:text-emerald-300 transition">
                  QC Validation Report
                </h4>
                <p className="text-xs text-slate-400 mt-1">
                  Executive summary, audit log & manual review sheet (.xlsx)
                </p>
              </div>
            </button>

            {/* Download 3: Full ZIP Archive */}
            <button
              onClick={() => handleDownload('zip')}
              disabled={downloading !== null}
              className="group p-4 rounded-2xl bg-gradient-to-br from-indigo-950/40 via-slate-900 to-purple-950/40 border border-indigo-500/30 hover:border-indigo-500 transition text-left flex flex-col justify-between shadow-xl cursor-pointer"
            >
              <div className="flex items-center justify-between w-full">
                <div className="p-2.5 rounded-xl bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 group-hover:scale-110 transition-transform">
                  <Archive className="h-5 w-5" />
                </div>
                <Download className="h-4 w-4 text-indigo-400 group-hover:translate-y-0.5 transition" />
              </div>
              <div className="mt-4">
                <h4 className="text-sm font-bold text-white group-hover:text-indigo-300 transition">
                  Complete Bundle (.ZIP)
                </h4>
                <p className="text-xs text-indigo-200/70 mt-1">
                  Both Excel workbooks + raw JSON audit metadata
                </p>
              </div>
            </button>

          </div>

        </div>
      )}

      {/* Master Reference Database Management Modal */}
      {isDbModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-in fade-in duration-200">
          <div className="relative w-full max-w-lg rounded-3xl bg-slate-900 border border-slate-800 p-6 sm:p-8 shadow-2xl space-y-6">
            
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-xl bg-indigo-500/20 text-indigo-400">
                  <Database className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">Master Reference Database</h3>
                  <p className="text-xs text-slate-400">Upload and pre-index large datasets for instant lookups</p>
                </div>
              </div>
              <button
                onClick={() => { setIsDbModalOpen(false); setIndexMessage(null); }}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition cursor-pointer"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* Current Metadata Card */}
            <div className="p-4 rounded-2xl bg-slate-950/70 border border-slate-800/80 space-y-2 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-slate-400 font-medium">Status:</span>
                <span className={`font-bold ${refDbMeta?.is_indexed ? 'text-emerald-400' : 'text-amber-400'}`}>
                  {refDbMeta?.is_indexed ? '● Active & Indexed' : '○ Not Initialized'}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-400 font-medium">Total Reference Records:</span>
                <span className="font-mono text-slate-200 font-semibold">{refDbMeta?.total_records?.toLocaleString() || 0}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-400 font-medium">Unique Machine Serials:</span>
                <span className="font-mono text-slate-200 font-semibold">{refDbMeta?.unique_serials?.toLocaleString() || 0}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-400 font-medium">Indexed Dataset Source:</span>
                <span className="font-mono text-indigo-300 truncate max-w-[200px]">{refDbMeta?.source_filename || 'None'}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-400 font-medium">Database File Size:</span>
                <span className="font-mono text-slate-200">{refDbMeta?.file_size_mb || 0} MB</span>
              </div>
            </div>

            {/* Feedback Message */}
            {indexMessage && (
              <div className={`p-3.5 rounded-xl border text-xs flex items-start gap-2.5 ${
                indexMessage.type === 'success'
                  ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                  : indexMessage.type === 'error'
                  ? 'bg-rose-500/10 border-rose-500/30 text-rose-300'
                  : 'bg-indigo-500/10 border-indigo-500/30 text-indigo-300'
              }`}>
                {indexMessage.type === 'success' ? (
                  <CheckCircle2 className="h-4 w-4 shrink-0 mt-0.5 text-emerald-400" />
                ) : (
                  <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                )}
                <span>{indexMessage.text}</span>
              </div>
            )}

            {/* Ingestion Dropzone */}
            <div className="space-y-3">
              <label className="block text-xs font-semibold text-slate-300">
                Upload New Reference Dataset (.xlsx, .csv, .parquet, .tsv)
              </label>
              
              <div className="relative border-2 border-dashed border-slate-700 hover:border-indigo-500/60 rounded-2xl p-4 text-center transition bg-slate-950/40">
                <input
                  type="file"
                  accept=".xlsx,.xls,.csv,.tsv,.parquet,.txt"
                  onChange={(e) => setIndexFile(e.target.files[0])}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                />
                <div className="flex flex-col items-center justify-center gap-1.5 py-2">
                  <UploadCloud className="h-6 w-6 text-indigo-400" />
                  <p className="text-xs font-semibold text-slate-200">
                    {indexFile ? indexFile.name : "Click or drag file to replace master database"}
                  </p>
                  <p className="text-[11px] text-slate-500">
                    Supports up to multi-GB .parquet, .csv, or .xlsx files
                  </p>
                </div>
              </div>
            </div>

            {/* Modal Actions */}
            <div className="flex items-center justify-between gap-3 pt-2">
              <button
                onClick={handleSeedSampleDb}
                disabled={indexing}
                className="px-3 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-750 text-slate-300 border border-slate-700 transition cursor-pointer disabled:opacity-50"
              >
                Reset to Sample Data
              </button>

              <div className="flex items-center gap-2">
                <button
                  onClick={handleIndexMasterDb}
                  disabled={!indexFile || indexing}
                  className="px-5 py-2 rounded-xl text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition flex items-center gap-1.5 cursor-pointer shadow-md shadow-indigo-600/30"
                >
                  {indexing ? (
                    <>
                      <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                      <span>Indexing Dataset...</span>
                    </>
                  ) : (
                    <span>Index Dataset</span>
                  )}
                </button>
              </div>
            </div>

          </div>
        </div>
      )}

    </div>
  );
}

