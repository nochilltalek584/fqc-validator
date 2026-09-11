import React, { useRef, useState } from 'react';
import { Upload, FileSpreadsheet, X, CheckCircle, AlertCircle } from 'lucide-react';

export default function FileDropzone({
  label,
  sublabel,
  file,
  onFileSelect,
  onFileRemove,
  accentColor = "indigo",
  badgeText = "Required"
}) {
  const [isDragOver, setIsDragOver] = useState(false);
  const inputRef = useRef(null);

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile.name.endsWith('.xlsx') || droppedFile.name.endsWith('.xls')) {
        onFileSelect(droppedFile);
      } else {
        alert("Please upload an Excel file (.xlsx or .xls)");
      }
    }
  };

  const formatSize = (bytes) => {
    if (!bytes) return '0 KB';
    const kb = bytes / 1024;
    if (kb < 1024) return `${kb.toFixed(1)} KB`;
    return `${(kb / 1024).toFixed(2)} MB`;
  };

  const borderColor = isDragOver
    ? accentColor === 'emerald' ? 'border-emerald-500 bg-emerald-950/20 shadow-emerald-500/20' : 'border-indigo-500 bg-indigo-950/20 shadow-indigo-500/20'
    : 'border-slate-800 hover:border-slate-700 bg-slate-900/60 hover:bg-slate-900/90';

  return (
    <div className="flex-1 flex flex-col min-w-[280px]">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-slate-200 text-sm">{label}</span>
          <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${
            accentColor === 'emerald' 
              ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' 
              : 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20'
          }`}>
            {badgeText}
          </span>
        </div>
        {file && (
          <span className="text-xs text-emerald-400 font-medium flex items-center gap-1">
            <CheckCircle className="h-3.5 w-3.5" /> Ready
          </span>
        )}
      </div>

      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !file && inputRef.current?.click()}
        className={`relative flex flex-col items-center justify-center p-6 rounded-2xl border-2 border-dashed transition-all duration-200 cursor-pointer min-h-[175px] shadow-sm ${borderColor}`}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".xlsx, .xls"
          className="hidden"
          onChange={(e) => {
            if (e.target.files && e.target.files[0]) {
              onFileSelect(e.target.files[0]);
            }
          }}
        />

        {file ? (
          <div className="w-full flex items-center justify-between p-3.5 rounded-xl bg-slate-800/80 border border-slate-700/60 shadow-inner">
            <div className="flex items-center gap-3 overflow-hidden">
              <div className={`p-2.5 rounded-lg shrink-0 ${
                accentColor === 'emerald' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-indigo-500/20 text-indigo-400'
              }`}>
                <FileSpreadsheet className="h-6 w-6" />
              </div>
              <div className="overflow-hidden text-left">
                <p className="text-sm font-semibold text-slate-100 truncate max-w-[220px]" title={file.name}>
                  {file.name}
                </p>
                <p className="text-xs text-slate-400 font-mono mt-0.5">
                  {formatSize(file.size)} • Excel Workbook
                </p>
              </div>
            </div>
            
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onFileRemove();
              }}
              className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-slate-700/80 transition"
              title="Remove File"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        ) : (
          <div className="text-center space-y-2 pointer-events-none">
            <div className={`mx-auto h-12 w-12 rounded-xl flex items-center justify-center transition-transform duration-200 ${
              isDragOver ? 'scale-110 bg-indigo-500/20 text-indigo-400' : 'bg-slate-800 text-slate-400'
            }`}>
              <Upload className="h-6 w-6" />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-200">
                Drag & drop or <span className="text-indigo-400 font-semibold underline underline-offset-2">browse</span>
              </p>
              <p className="text-xs text-slate-400 mt-1">
                {sublabel || "Upload .xlsx or .xls file"}
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
