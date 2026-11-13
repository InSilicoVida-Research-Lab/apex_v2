import React from 'react';
import { DocumentSummary } from '../types';
import { 
  FileText, 
  Layers, 
  CheckCircle2, 
  ShieldAlert, 
  Code2, 
  RefreshCw, 
  ExternalLink,
  ChevronDown,
  Sparkles,
  Search,
  Upload
} from 'lucide-react';

interface HeaderProps {
  documents: DocumentSummary[];
  selectedDocId: string;
  onSelectDoc: (id: string) => void;
  activeTab: 'explorer' | 'tan' | 'verification' | 'json';
  onSelectTab: (tab: 'explorer' | 'tan' | 'verification' | 'json') => void;
  isLoading: boolean;
  onRefresh: () => void;
  searchQuery: string;
  onSearchChange: (q: string) => void;
  onToggleAuth?: () => void;
  onOpenUpload?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  documents,
  selectedDocId,
  onSelectDoc,
  activeTab,
  onSelectTab,
  isLoading,
  onRefresh,
  searchQuery,
  onSearchChange,
  onToggleAuth,
  onOpenUpload,
}) => {
  const currentDoc = documents.find((d) => d.id === selectedDocId);

  return (
    <header className="bg-white border-b border-sky-100 text-slate-800 sticky top-0 z-50 shadow-xs">
      {/* Top Navbar */}
      <div className="max-w-[1920px] mx-auto px-4 py-2.5 flex items-center justify-between gap-4">
        {/* Brand & Document Selector */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2.5 pr-3 border-r border-slate-200">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-sky-500 to-blue-600 flex items-center justify-center font-bold text-white shadow-md shadow-sky-500/20">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            <div>
              <span className="font-bold tracking-tight text-slate-900 flex items-center gap-1.5 text-base">
                APEX PBPK <span className="text-[10px] px-1.5 py-0.2 rounded bg-sky-100 text-sky-700 font-semibold border border-sky-200">v2</span>
              </span>
              <p className="text-[10px] text-slate-500 font-mono leading-none">Automated Extraction & Audit</p>
            </div>
          </div>

          {/* Paper Selector Dropdown */}
          <div className="relative group">
            <select
              value={selectedDocId}
              onChange={(e) => onSelectDoc(e.target.value)}
              className="appearance-none bg-sky-50/70 border border-sky-200 hover:border-sky-300 text-slate-800 text-xs rounded-lg px-3 py-1.5 pr-8 font-medium cursor-pointer focus:outline-none focus:ring-1 focus:ring-sky-500 max-w-xs md:max-w-md truncate"
            >
              {documents.map((doc) => (
                <option key={doc.id} value={doc.id}>
                  {doc.title || doc.id} ({doc.parameter_count} params)
                </option>
              ))}
            </select>
            <ChevronDown className="w-3.5 h-3.5 text-slate-500 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
          </div>

          {/* Document Status Pills */}
          {currentDoc && (
            <div className="hidden lg:flex items-center gap-2 text-xs">
              <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 font-mono text-[11px] border border-slate-200">
                {currentDoc.parameter_count} parameters
              </span>
              {currentDoc.tan_score && (
                <span className="px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 font-mono text-[11px] border border-emerald-200 flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                  Tan: {currentDoc.tan_score.supported}/{currentDoc.tan_score.total}
                </span>
              )}
              {currentDoc.compounds.length > 0 && (
                <span className="px-2 py-0.5 rounded-full bg-sky-50 text-sky-700 text-[11px] border border-sky-200">
                  {currentDoc.compounds.slice(0, 2).join(', ')}{currentDoc.compounds.length > 2 ? ` +${currentDoc.compounds.length - 2}` : ''}
                </span>
              )}
            </div>
          )}
        </div>

        {/* Global Search & Action Buttons */}
        <div className="flex items-center gap-2.5">
          <div className="relative w-48 md:w-64">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search parameters, quotes..."
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              className="w-full bg-sky-50/50 border border-sky-200 text-slate-800 text-xs rounded-lg pl-8 pr-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-sky-500 focus:bg-white placeholder:text-slate-400 font-sans"
            />
          </div>

          <button
            onClick={onRefresh}
            disabled={isLoading}
            className="p-1.5 rounded-lg bg-white hover:bg-sky-50 text-slate-600 hover:text-sky-700 border border-sky-200 transition"
            title="Reload document"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-sky-600' : ''}`} />
          </button>

          {onOpenUpload && (
            <button
              onClick={onOpenUpload}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-medium text-xs shadow-xs transition"
              title="Upload new PBPK paper (PDF, JSON, or Markdown)"
            >
              <Upload className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Upload Paper</span>
            </button>
          )}

          {onToggleAuth && (
            <button
              onClick={onToggleAuth}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-white hover:bg-sky-50 text-slate-700 border border-sky-200 transition text-xs font-medium"
              title="Switch user / Sign in view"
            >
              <div className="w-4 h-4 rounded-full bg-gradient-to-tr from-sky-500 to-blue-600 flex items-center justify-center text-[10px] text-white font-bold">
                C
              </div>
              <span className="hidden md:inline text-[11px]">Curator</span>
            </button>
          )}
        </div>
      </div>

      {/* Navigation Tabs Bar */}
      <div className="max-w-[1920px] mx-auto px-4 flex items-center justify-between border-t border-sky-100 bg-white text-xs">
        <nav className="flex space-x-1">
          <button
            onClick={() => onSelectTab('explorer')}
            className={`flex items-center gap-2 px-3 py-2 border-b-2 font-medium transition ${
              activeTab === 'explorer'
                ? 'border-sky-600 text-sky-700 bg-sky-50/80'
                : 'border-transparent text-slate-600 hover:text-slate-900 hover:border-slate-300'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            <span>Parameters & Provenance</span>
          </button>

          <button
            onClick={() => onSelectTab('tan')}
            className={`flex items-center gap-2 px-3 py-2 border-b-2 font-medium transition ${
              activeTab === 'tan'
                ? 'border-sky-600 text-sky-700 bg-sky-50/80'
                : 'border-transparent text-slate-600 hover:text-slate-900 hover:border-slate-300'
            }`}
          >
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
            <span>Tan PBPK Scorecard</span>
          </button>

          <button
            onClick={() => onSelectTab('verification')}
            className={`flex items-center gap-2 px-3 py-2 border-b-2 font-medium transition ${
              activeTab === 'verification'
                ? 'border-sky-600 text-sky-700 bg-sky-50/80'
                : 'border-transparent text-slate-600 hover:text-slate-900 hover:border-slate-300'
            }`}
          >
            <ShieldAlert className="w-3.5 h-3.5 text-amber-500" />
            <span>Rule Verification & Audit</span>
          </button>

          <button
            onClick={() => onSelectTab('json')}
            className={`flex items-center gap-2 px-3 py-2 border-b-2 font-medium transition ${
              activeTab === 'json'
                ? 'border-sky-600 text-sky-700 bg-sky-50/80'
                : 'border-transparent text-slate-600 hover:text-slate-900 hover:border-slate-300'
            }`}
          >
            <Code2 className="w-3.5 h-3.5 text-indigo-600" />
            <span>JSON & Exports</span>
          </button>
        </nav>

        {currentDoc && currentDoc.has_pdf && (
          <div className="hidden sm:flex items-center gap-2 py-1">
            <a
              href={`/api/documents/${encodeURIComponent(selectedDocId)}/pdf`}
              target="_blank"
              rel="noreferrer"
              className="text-[11px] text-slate-500 hover:text-sky-600 flex items-center gap-1 font-mono transition"
            >
              <span>Raw PDF</span>
              <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        )}
      </div>
    </header>
  );
};

