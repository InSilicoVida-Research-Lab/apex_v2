import React, { useState, useEffect, useCallback } from 'react';
import { 
  fetchDocuments, 
  fetchDocument, 
  fetchMarkdown, 
  fetchVerification, 
  fetchTanAssessment, 
  updateParameter 
} from './api';
import { 
  DocumentSummary, 
  ExtractedDocument, 
  VerificationReport, 
  TanPBPKAssessment 
} from './types';
import { Header } from './components/Header';
import { SplitScreenExplorer } from './components/SplitScreenExplorer';
import { TanScorecard } from './components/TanScorecard';
import { VerificationDashboard } from './components/VerificationDashboard';
import { JsonViewer } from './components/JsonViewer';
import { LoginView } from './components/LoginView';
import { UploadModal } from './components/UploadModal';
import { Loader2, AlertCircle } from 'lucide-react';

export const App: React.FC = () => {
  const [showLogin, setShowLogin] = useState<boolean>(false);
  const [showUploadModal, setShowUploadModal] = useState<boolean>(false);
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [selectedDocId, setSelectedDocId] = useState<string>('');
  const [activeTab, setActiveTab] = useState<'explorer' | 'tan' | 'verification' | 'json'>('explorer');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const [document, setDocument] = useState<ExtractedDocument | null>(null);
  const [markdown, setMarkdown] = useState<string>('');
  const [hasMarkdown, setHasMarkdown] = useState<boolean>(false);
  const [verification, setVerification] = useState<VerificationReport | null>(null);
  const [tanAssessment, setTanAssessment] = useState<TanPBPKAssessment | null>(null);

  const [isLoadingDocs, setIsLoadingDocs] = useState<boolean>(true);
  const [isLoadingDoc, setIsLoadingDoc] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Load document list
  const loadDocuments = useCallback(async () => {
    setIsLoadingDocs(true);
    try {
      const docs = await fetchDocuments();
      setDocuments(docs);
      if (docs.length > 0) {
        // Prefer Loccisano 2013 if available, else first
        const loccisano = docs.find((d) => d.id.toLowerCase().includes('loccisano'));
        setSelectedDocId((prev) => prev || (loccisano ? loccisano.id : docs[0].id));
      }
    } catch (err: any) {
      setError(`Failed to connect to APEX Backend API: ${err.message}`);
    } finally {
      setIsLoadingDocs(false);
    }
  }, []);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  // Load selected document details
  const loadSelectedDocument = useCallback(async (docId: string) => {
    if (!docId) return;
    setIsLoadingDoc(true);
    setError(null);
    try {
      const [docData, mdData, verifData, tanData] = await Promise.all([
        fetchDocument(docId),
        fetchMarkdown(docId).catch(() => ({ markdown: '', available: false })),
        fetchVerification(docId).catch(() => null),
        fetchTanAssessment(docId).catch(() => null),
      ]);

      setDocument(docData);
      setMarkdown(mdData.markdown);
      setHasMarkdown(mdData.available);
      setVerification(verifData);
      setTanAssessment(tanData || docData.tan_assessment || null);
    } catch (err: any) {
      setError(`Failed to load document ${docId}: ${err.message}`);
    } finally {
      setIsLoadingDoc(false);
    }
  }, []);

  useEffect(() => {
    if (selectedDocId) {
      loadSelectedDocument(selectedDocId);
    }
  }, [selectedDocId, loadSelectedDocument]);

  // Update parameter handler
  const handleUpdateParameter = async (paramId: string, updates: any) => {
    if (!selectedDocId) return;
    await updateParameter(selectedDocId, paramId, updates);
    // Refresh document and verification
    await loadSelectedDocument(selectedDocId);
  };

  const handleInspectParamFromVerification = (paramIndex: number) => {
    setActiveTab('explorer');
  };

  const handleUploadSuccess = async (newDocId: string) => {
    await loadDocuments();
    setSelectedDocId(newDocId);
    setActiveTab('explorer');
  };

  if (showLogin) {
    return <LoginView onLoginSuccess={() => setShowLogin(false)} />;
  }

  if (isLoadingDocs) {
    return (
      <div className="h-full flex flex-col items-center justify-center bg-slate-50 text-slate-600">
        <Loader2 className="w-8 h-8 animate-spin text-sky-600 mb-3" />
        <p className="text-sm font-medium">Connecting to APEX PBPK Engine...</p>
      </div>
    );
  }

  const currentSummary = documents.find((d) => d.id === selectedDocId);

  return (
    <div className="h-full flex flex-col bg-slate-50 text-slate-900">
      <Header
        documents={documents}
        selectedDocId={selectedDocId}
        onSelectDoc={setSelectedDocId}
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        isLoading={isLoadingDoc}
        onRefresh={() => loadSelectedDocument(selectedDocId)}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        onToggleAuth={() => setShowLogin(true)}
        onOpenUpload={() => setShowUploadModal(true)}
      />

      {error && (
        <div className="bg-rose-50 border-b border-rose-200 text-rose-800 px-4 py-2 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
          <span>{error}</span>
        </div>
      )}

      <main className="flex-1 overflow-hidden">
        {isLoadingDoc ? (
          <div className="h-full flex flex-col items-center justify-center text-slate-500 space-y-2">
            <Loader2 className="w-6 h-6 animate-spin text-sky-600" />
            <p className="text-xs">Loading PBPK document & verification report...</p>
          </div>
        ) : !document ? (
          <div className="h-full flex items-center justify-center text-slate-400 text-xs">
            No document selected or failed to load.
          </div>
        ) : activeTab === 'explorer' ? (
          <SplitScreenExplorer
            document={document}
            docId={selectedDocId}
            markdown={markdown}
            hasMarkdown={hasMarkdown}
            hasPdf={Boolean(currentSummary?.has_pdf)}
            flags={verification?.flags || []}
            searchQuery={searchQuery}
            onUpdateParameter={handleUpdateParameter}
          />
        ) : activeTab === 'tan' ? (
          tanAssessment ? (
            <TanScorecard assessment={tanAssessment} />
          ) : (
            <div className="h-full flex items-center justify-center text-slate-500 text-xs">
              Tan PBPK assessment not available for this record.
            </div>
          )
        ) : activeTab === 'verification' ? (
          verification ? (
            <VerificationDashboard
              report={verification}
              document={document}
              onUpdateParameter={handleUpdateParameter}
              onInspectParam={handleInspectParamFromVerification}
            />
          ) : (
            <div className="h-full flex items-center justify-center text-slate-500 text-xs">
              Verification report not available.
            </div>
          )
        ) : (
          <JsonViewer document={document} docId={selectedDocId} />
        )}
      </main>

      {/* Upload Modal */}
      <UploadModal
        isOpen={showUploadModal}
        onClose={() => setShowUploadModal(false)}
        onUploadSuccess={handleUploadSuccess}
      />
    </div>
  );
};
export default App;

