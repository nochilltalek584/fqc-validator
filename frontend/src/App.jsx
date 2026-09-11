import React, { useState, useEffect } from 'react';
import api from './api';
import Navbar from './components/Navbar';
import ValidatorView from './views/ValidatorView';
import AuditDashboardView from './views/AuditDashboardView';
import RuleGuideView from './views/RuleGuideView';
import FlaggedReviewModal from './components/FlaggedReviewModal';
import ErrorBoundary from './components/ErrorBoundary';

export default function App() {
  const [activeTab, setActiveTab] = useState('validator');
  const [mahavirFile, setMahavirFile] = useState(null);
  const [referenceFile, setReferenceFile] = useState(null);
  const [stats, setStats] = useState(null);
  const [isFlaggedModalOpen, setIsFlaggedModalOpen] = useState(false);
  const [backendStatus, setBackendStatus] = useState(false);

  // Check Backend Health once on application load
  const checkHealth = async () => {
    try {
      const res = await api.get('/health');
      if (res.data?.status === 'healthy') {
        setBackendStatus(true);
      } else {
        setBackendStatus(false);
      }
    } catch {
      setBackendStatus(false);
    }
  };

  useEffect(() => {
    checkHealth();
  }, []);

  const handleDownloadSample = async () => {
    try {
      const res = await api.get('/sample_files', {
        responseType: 'blob'
      });
      const blob = new Blob([res.data], { type: 'application/zip' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'sample_test_files.zip';
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error(err);
      alert('Could not download sample files. Make sure the backend server is running.');
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col selection:bg-indigo-500 selection:text-white font-sans antialiased">
      
      {/* Top Navbar */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        backendStatus={backendStatus}
        onRefreshHealth={checkHealth}
        onDownloadSample={handleDownloadSample}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 pt-6">
        <ErrorBoundary>
          {activeTab === 'validator' && (
            <ValidatorView
              mahavirFile={mahavirFile}
              setMahavirFile={setMahavirFile}
              referenceFile={referenceFile}
              setReferenceFile={setReferenceFile}
              stats={stats}
              setStats={setStats}
              onNavigateDashboard={() => setActiveTab('dashboard')}
              onOpenFlaggedModal={() => setIsFlaggedModalOpen(true)}
            />
          )}

          {activeTab === 'dashboard' && (
            <AuditDashboardView
              stats={stats}
              onOpenFlaggedModal={() => setIsFlaggedModalOpen(true)}
            />
          )}

          {activeTab === 'guide' && (
            <RuleGuideView />
          )}
        </ErrorBoundary>
      </main>

      {/* Flagged Manual Review Modal */}
      <FlaggedReviewModal
        isOpen={isFlaggedModalOpen}
        onClose={() => setIsFlaggedModalOpen(false)}
        records={stats?.records || []}
      />

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950 py-6 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>FQC "NG to Verify" Rule Engine &copy; 2026</span>
          <span className="text-slate-400 font-mono">Preserving data integrity &middot; openpyxl &middot; React 19</span>
        </div>
      </footer>

    </div>
  );
}
