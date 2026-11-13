import React, { useState, useMemo, useRef, useEffect } from 'react';
import { ExtractedDocument, ExtractedParameter, ParameterFlag } from '../types';
import { 
  FileText, 
  Table as TableIcon, 
  ExternalLink, 
  Search, 
  Filter, 
  Edit3, 
  AlertTriangle, 
  CheckCircle, 
  Quote, 
  Layers, 
  Eye,
  Info,
  SlidersHorizontal,
  ChevronRight,
  ChevronLeft,
  ZoomIn,
  ZoomOut,
  Loader2
} from 'lucide-react';
import { ParameterEditModal } from './ParameterEditModal';
import { getPageImageUrl, fetchPdfInfo } from '../api';

interface SplitScreenExplorerProps {
  document: ExtractedDocument;
  docId: string;
  markdown: string;
  hasMarkdown: boolean;
  hasPdf: boolean;
  flags: ParameterFlag[];
  searchQuery: string;
  onUpdateParameter: (paramId: string, updates: any) => Promise<void>;
}

export const SplitScreenExplorer: React.FC<SplitScreenExplorerProps> = ({
  document,
  docId,
  markdown,
  hasMarkdown,
  hasPdf,
  flags,
  searchQuery,
  onUpdateParameter,
}) => {
  const [docViewMode, setDocViewMode] = useState<'pdf' | 'markdown'>(
    hasPdf ? 'pdf' : hasMarkdown ? 'markdown' : 'pdf'
  );
  const [activeSubclassFilter, setActiveSubclassFilter] = useState<string>('all');
  const [selectedParamId, setSelectedParamId] = useState<string | null>(null);
  const [editingParam, setEditingParam] = useState<ExtractedParameter | null>(null);
  const [targetPage, setTargetPage] = useState<number>(1);
  const [currentPdfPage, setCurrentPdfPage] = useState<number>(1);
  const [totalPdfPages, setTotalPdfPages] = useState<number>(1);
  const [pdfZoom, setPdfZoom] = useState<number>(1.0);
  const [isPageLoading, setIsPageLoading] = useState<boolean>(false);
  const [highlightQuote, setHighlightQuote] = useState<string>('');

  const mdContainerRef = useRef<HTMLDivElement>(null);
  const params = document.model_parameters || [];

  // Fetch total PDF page count
  useEffect(() => {
    if (hasPdf) {
      fetchPdfInfo(docId).then((info) => {
        if (info.available && info.page_count > 0) {
          setTotalPdfPages(info.page_count);
        }
      });
    }
  }, [docId, hasPdf]);

  // Index flags by param_index
  const flagsByIndex = useMemo(() => {
    const map = new Map<number, ParameterFlag[]>();
    flags.forEach((f) => {
      const existing = map.get(f.param_index) || [];
      existing.push(f);
      map.set(f.param_index, existing);
    });
    return map;
  }, [flags]);

  // Extract unique subclasses
  const availableSubclasses = useMemo(() => {
    const scs = new Set<string>();
    params.forEach((p) => {
      if (p.parameter_subclass) scs.add(p.parameter_subclass);
      else if (p.parameter_class) scs.add(p.parameter_class);
    });
    return Array.from(scs).sort();
  }, [params]);

  // Filtered parameters
  const filteredParams = useMemo(() => {
    return params.filter((p, index) => {
      // Subclass filter
      if (activeSubclassFilter !== 'all') {
        const sc = p.parameter_subclass || p.parameter_class || '';
        if (sc !== activeSubclassFilter) return false;
      }

      // Search query
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const name = (p.parameter_name_standardized || p.parameter_name_original || '').toLowerCase();
        const sym = (p.symbol_standardized || p.symbol_original || '').toLowerCase();
        const cmpd = (p.context?.compound || '').toLowerCase();
        const quote = (p.provenance?.source_quote || '').toLowerCase();
        const tbl = (p.provenance?.source_table || '').toLowerCase();
        const matches = name.includes(q) || sym.includes(q) || cmpd.includes(q) || quote.includes(q) || tbl.includes(q);
        if (!matches) return false;
      }

      return true;
    });
  }, [params, activeSubclassFilter, searchQuery]);

  // Select initial parameter
  useEffect(() => {
    if (!selectedParamId && filteredParams.length > 0) {
      setSelectedParamId(filteredParams[0].parameter_id);
    }
  }, [filteredParams, selectedParamId]);

  const selectedParam = useMemo(() => {
    return params.find((p) => p.parameter_id === selectedParamId) || filteredParams[0] || null;
  }, [params, selectedParamId, filteredParams]);

  // Focus and jump to provenance
  const handleInspectProvenance = (p: ExtractedParameter) => {
    setSelectedParamId(p.parameter_id);
    const page = p.provenance?.source_page;
    if (page && page > 0) {
      setTargetPage(page);
      setCurrentPdfPage(page);
      setIsPageLoading(true);
    }
    const quote = p.provenance?.source_quote || '';
    setHighlightQuote(quote);

    // If in markdown mode, scroll to text
    if (docViewMode === 'markdown' && quote && mdContainerRef.current) {
      const normalized = quote.slice(0, 30).toLowerCase();
      const elements = mdContainerRef.current.querySelectorAll('p, td, th, li');
      for (const el of Array.from(elements)) {
        if (el.textContent?.toLowerCase().includes(normalized)) {
          el.scrollIntoView({ behavior: 'smooth', block: 'center' });
          (el as HTMLElement).style.backgroundColor = 'rgba(2, 132, 199, 0.35)';
          setTimeout(() => {
            (el as HTMLElement).style.backgroundColor = '';
          }, 3000);
          break;
        }
      }
    }
  };

  const selectedParamIndex = selectedParam ? params.findIndex((p) => p.parameter_id === selectedParam.parameter_id) : -1;
  const selectedParamFlags = selectedParamIndex >= 0 ? flagsByIndex.get(selectedParamIndex) || [] : [];

  return (
    <div className="h-[calc(100vh-82px)] flex flex-col lg:flex-row overflow-hidden bg-slate-50">
      {/* ----------------- LEFT PANE: SOURCE DOCUMENT ----------------- */}
      <div className="w-full lg:w-1/2 h-1/2 lg:h-full border-b lg:border-b-0 lg:border-r border-sky-100 flex flex-col bg-white">
        {/* Document Pane Toolbar */}
        <div className="px-4 py-2 bg-sky-50/60 border-b border-sky-100 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-slate-700 flex items-center gap-1.5">
              <FileText className="w-3.5 h-3.5 text-sky-600" />
              Source Evidence
            </span>
            {targetPage > 0 && (
              <span className="text-[11px] font-mono bg-sky-100 text-sky-800 px-2 py-0.5 rounded border border-sky-200 font-medium">
                Target: Page {targetPage}
              </span>
            )}
          </div>

          <div className="flex items-center gap-2">
            {hasPdf && hasMarkdown && (
              <div className="flex rounded-lg bg-sky-100/70 p-0.5 border border-sky-200 text-[11px]">
                <button
                  onClick={() => setDocViewMode('pdf')}
                  className={`px-2.5 py-1 rounded-md font-medium transition ${
                    docViewMode === 'pdf' ? 'bg-sky-600 text-white shadow-xs' : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  PDF Document
                </button>
                <button
                  onClick={() => setDocViewMode('markdown')}
                  className={`px-2.5 py-1 rounded-md font-medium transition ${
                    docViewMode === 'markdown' ? 'bg-sky-600 text-white shadow-xs' : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  Extracted Markdown
                </button>
              </div>
            )}
            {hasPdf && (
              <a
                href={`/api/documents/${encodeURIComponent(docId)}/pdf#page=${targetPage}`}
                target="_blank"
                rel="noreferrer"
                className="p-1.5 rounded-lg bg-white hover:bg-sky-50 text-slate-600 hover:text-sky-700 border border-sky-200 transition"
                title="Open PDF in new tab"
              >
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            )}
          </div>
        </div>

        {/* Document Content View */}
        <div className="flex-1 overflow-hidden relative flex flex-col">
          {docViewMode === 'pdf' && hasPdf ? (
            <div className="w-full h-full flex flex-col bg-slate-100">
              {/* PDF Sub-toolbar */}
              <div className="bg-white border-b border-sky-100 px-3 py-1.5 flex items-center justify-between text-xs font-mono shadow-2xs">
                {/* Page Navigation */}
                <div className="flex items-center gap-1.5">
                  <button
                    onClick={() => {
                      if (currentPdfPage > 1) {
                        setCurrentPdfPage((p) => p - 1);
                        setIsPageLoading(true);
                      }
                    }}
                    disabled={currentPdfPage <= 1}
                    className="p-1 rounded hover:bg-sky-50 text-slate-600 disabled:opacity-40 transition"
                    title="Previous Page"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </button>

                  <span className="text-slate-800 font-medium px-1">
                    Page <strong>{currentPdfPage}</strong> of {totalPdfPages}
                  </span>

                  <button
                    onClick={() => {
                      if (currentPdfPage < totalPdfPages) {
                        setCurrentPdfPage((p) => p + 1);
                        setIsPageLoading(true);
                      }
                    }}
                    disabled={currentPdfPage >= totalPdfPages}
                    className="p-1 rounded hover:bg-sky-50 text-slate-600 disabled:opacity-40 transition"
                    title="Next Page"
                  >
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>

                {/* Jump to Param Source & Zoom Controls */}
                <div className="flex items-center gap-2">
                  {targetPage > 0 && targetPage !== currentPdfPage && targetPage <= totalPdfPages && (
                    <button
                      onClick={() => {
                        setCurrentPdfPage(targetPage);
                        setIsPageLoading(true);
                      }}
                      className="px-2 py-0.5 rounded bg-sky-100 hover:bg-sky-200 text-sky-800 text-[11px] font-semibold border border-sky-300 transition"
                    >
                      Jump to Param Page {targetPage}
                    </button>
                  )}

                  <div className="flex items-center gap-1 bg-slate-50 px-1.5 py-0.5 rounded border border-slate-200">
                    <button
                      onClick={() => setPdfZoom((z) => Math.max(0.6, Number((z - 0.2).toFixed(1))))}
                      className="p-0.5 hover:text-sky-600 transition"
                      title="Zoom Out"
                    >
                      <ZoomOut className="w-3.5 h-3.5 text-slate-500" />
                    </button>
                    <span className="text-[11px] font-semibold text-slate-700 w-10 text-center">
                      {Math.round(pdfZoom * 100)}%
                    </span>
                    <button
                      onClick={() => setPdfZoom((z) => Math.min(2.5, Number((z + 0.2).toFixed(1))))}
                      className="p-0.5 hover:text-sky-600 transition"
                      title="Zoom In"
                    >
                      <ZoomIn className="w-3.5 h-3.5 text-slate-500" />
                    </button>
                  </div>

                  <a
                    href={`/api/documents/${encodeURIComponent(docId)}/pdf#page=${currentPdfPage}`}
                    target="_blank"
                    rel="noreferrer"
                    className="p-1 rounded hover:bg-sky-50 text-slate-500 hover:text-sky-600 transition flex items-center gap-1 text-[11px]"
                    title="Open raw PDF in new browser tab"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                </div>
              </div>

              {/* PDF Canvas Viewport */}
              <div className="flex-1 overflow-auto p-4 flex flex-col items-center justify-start bg-slate-200/50">
                <div 
                  className="relative shadow-xl rounded-sm bg-white border border-slate-300 transition-all"
                  style={{ width: `${pdfZoom * 800}px`, maxWidth: 'none' }}
                >
                  <img
                    key={`${docId}-${currentPdfPage}`}
                    src={getPageImageUrl(docId, currentPdfPage, pdfZoom > 1.2 ? 200 : 150)}
                    alt={`Page ${currentPdfPage} of ${totalPdfPages}`}
                    className="w-full h-auto block"
                    onLoad={() => setIsPageLoading(false)}
                  />
                  {isPageLoading && (
                    <div className="absolute inset-0 bg-white/70 backdrop-blur-2xs flex flex-col items-center justify-center text-xs text-sky-800 font-medium z-10">
                      <Loader2 className="w-6 h-6 animate-spin text-sky-600 mb-2" />
                      <span>Loading page {currentPdfPage}...</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ) : hasMarkdown ? (
            <div
              ref={mdContainerRef}
              className="w-full h-full p-6 overflow-y-auto font-mono text-xs text-slate-800 leading-relaxed space-y-4 whitespace-pre-wrap select-text selection:bg-sky-200 bg-white"
            >
              {markdown}
            </div>
          ) : (
            <div className="h-full flex items-center justify-center text-slate-400 text-xs">
              No document view available for this record.
            </div>
          )}
        </div>

        {/* Provenance quote callout bar */}
        {highlightQuote && (
          <div className="p-3 bg-sky-50 border-t border-sky-200 flex items-start gap-2 text-xs">
            <Quote className="w-4 h-4 text-sky-600 shrink-0 mt-0.5" />
            <div className="flex-1 min-w-0">
              <span className="text-[10px] text-sky-700 font-bold uppercase tracking-wider block">
                Source Verbatim Quote
              </span>
              <p className="text-slate-800 italic line-clamp-2 text-[11px]">&ldquo;{highlightQuote}&rdquo;</p>
            </div>
          </div>
        )}
      </div>

      {/* ----------------- RIGHT PANE: PARAMETERS & PROVENANCE ----------------- */}
      <div className="w-full lg:w-1/2 h-1/2 lg:h-full flex flex-col bg-white overflow-hidden">
        {/* Filter Chips Bar */}
        <div className="px-4 py-2 border-b border-sky-100 bg-sky-50/40 flex items-center gap-1.5 overflow-x-auto text-xs no-scrollbar">
          <button
            onClick={() => setActiveSubclassFilter('all')}
            className={`px-2.5 py-1 rounded-md text-[11px] font-medium whitespace-nowrap transition ${
              activeSubclassFilter === 'all'
                ? 'bg-sky-600 text-white shadow-xs'
                : 'bg-white text-slate-600 border border-slate-200 hover:bg-sky-50 hover:text-sky-700'
            }`}
          >
            All ({params.length})
          </button>
          {availableSubclasses.map((sc) => {
            const count = params.filter((p) => (p.parameter_subclass || p.parameter_class) === sc).length;
            return (
              <button
                key={sc}
                onClick={() => setActiveSubclassFilter(sc)}
                className={`px-2.5 py-1 rounded-md text-[11px] font-medium whitespace-nowrap transition ${
                  activeSubclassFilter === sc
                    ? 'bg-sky-600 text-white shadow-xs'
                    : 'bg-white text-slate-600 border border-slate-200 hover:bg-sky-50 hover:text-sky-700'
                }`}
              >
                {sc.replace(/_/g, ' ')} ({count})
              </button>
            );
          })}
        </div>

        {/* Parameters Data Table */}
        <div className="flex-1 overflow-y-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead className="bg-sky-50/80 text-slate-600 sticky top-0 z-10 text-[11px] font-mono uppercase tracking-wider border-b border-sky-100">
              <tr>
                <th className="py-2.5 px-3">Parameter / Symbol</th>
                <th className="py-2.5 px-3">Value</th>
                <th className="py-2.5 px-3">Unit</th>
                <th className="py-2.5 px-3">Context</th>
                <th className="py-2.5 px-3">Provenance</th>
                <th className="py-2.5 px-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-sky-100/70 font-sans">
              {filteredParams.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-center py-12 text-slate-400 text-xs">
                    No parameters found matching the filter criteria.
                  </td>
                </tr>
              ) : (
                filteredParams.map((p, idx) => {
                  const isSelected = p.parameter_id === selectedParamId;
                  const pFlags = flagsByIndex.get(params.indexOf(p)) || [];
                  const hasErrors = pFlags.some((f) => f.severity === 'error');
                  const hasWarnings = pFlags.some((f) => f.severity === 'warning');
                  const val = p.quantitative_data?.value;
                  const valText = p.quantitative_data?.value_text;
                  const isRange = p.quantitative_data?.start_value !== null && p.quantitative_data?.start_value !== undefined;

                  return (
                    <tr
                      key={p.parameter_id || idx}
                      onClick={() => handleInspectProvenance(p)}
                      className={`cursor-pointer transition group ${
                        isSelected
                          ? 'bg-sky-50 border-l-2 border-sky-600'
                          : 'hover:bg-sky-50/60 border-l-2 border-transparent'
                      }`}
                    >
                      {/* Name & Symbol */}
                      <td className="py-2 px-3 max-w-[200px]">
                        <div className="flex items-center gap-1.5">
                          {hasErrors ? (
                            <span title="Validation Error"><AlertTriangle className="w-3.5 h-3.5 text-rose-500 shrink-0" /></span>
                          ) : hasWarnings ? (
                            <span title="Validation Warning"><Info className="w-3.5 h-3.5 text-amber-500 shrink-0" /></span>
                          ) : (
                            <CheckCircle className="w-3 h-3 text-emerald-500 shrink-0" />
                          )}
                          <span className="font-medium text-slate-900 truncate block">
                            {p.parameter_name_standardized || p.parameter_name_original || '<Unnamed>'}
                          </span>
                        </div>
                        <div className="text-[10px] text-slate-500 font-mono truncate ml-5">
                          {p.symbol_original || p.symbol_standardized || p.parameter_subclass || ''}
                        </div>
                      </td>

                      {/* Value */}
                      <td className="py-2 px-3 font-mono text-[11px] whitespace-nowrap">
                        {isRange ? (
                          <span className="text-sky-700 font-semibold">
                            {p.quantitative_data?.start_value} &ndash; {p.quantitative_data?.end_value}
                          </span>
                        ) : val !== null && val !== undefined ? (
                          <span className="text-slate-900 font-semibold">{val}</span>
                        ) : (
                          <span className="text-slate-500">{valText || 'null'}</span>
                        )}
                      </td>

                      {/* Unit */}
                      <td className="py-2 px-3 font-mono text-[11px] text-slate-600 whitespace-nowrap">
                        {p.quantitative_data?.unit_standardized || p.quantitative_data?.unit_original || (
                          <span className="text-slate-300">-</span>
                        )}
                      </td>

                      {/* Context */}
                      <td className="py-2 px-3 text-[11px] text-slate-600">
                        <div className="truncate max-w-[140px]">
                          {p.context?.compound && (
                            <span className="text-sky-700 font-medium">{p.context.compound}</span>
                          )}
                          {p.context?.species && (
                            <span className="text-slate-500 ml-1">({p.context.species})</span>
                          )}
                        </div>
                        {p.context?.organ && (
                          <span className="text-[10px] text-slate-500 block truncate">{p.context.organ}</span>
                        )}
                      </td>

                      {/* Provenance */}
                      <td className="py-2 px-3 text-[11px] text-slate-600">
                        <div className="truncate max-w-[130px] font-mono text-[10px]">
                          {p.provenance?.source_table || (p.provenance?.source_page ? `Page ${p.provenance.source_page}` : 'Narrative')}
                        </div>
                        {p.provenance?.confidence && (
                          <span
                            className={`inline-block text-[9px] uppercase px-1.5 py-0.2 rounded font-bold ${
                              p.provenance.confidence === 'high'
                                ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                                : p.provenance.confidence === 'medium'
                                ? 'bg-amber-50 text-amber-700 border border-amber-200'
                                : 'bg-slate-100 text-slate-600 border border-slate-200'
                            }`}
                          >
                            {p.provenance.confidence}
                          </span>
                        )}
                      </td>

                      {/* Actions */}
                      <td className="py-2 px-3 text-right whitespace-nowrap">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setEditingParam(p);
                          }}
                          className="p-1 rounded hover:bg-sky-100 text-slate-500 hover:text-sky-700 transition"
                          title="Edit parameter value"
                        >
                          <Edit3 className="w-3.5 h-3.5" />
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Selected Parameter Details Footer Drawer */}
        {selectedParam && (
          <div className="p-3.5 bg-sky-50/40 border-t border-sky-100 text-xs">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-slate-900 text-sm">
                  {selectedParam.parameter_name_standardized || selectedParam.parameter_name_original}
                </span>
                <span className="text-[10px] font-mono bg-sky-100 text-sky-800 px-2 py-0.5 rounded font-medium border border-sky-200">
                  {selectedParam.parameter_id}
                </span>
              </div>
              <button
                onClick={() => setEditingParam(selectedParam)}
                className="flex items-center gap-1 px-2.5 py-1 rounded bg-white hover:bg-sky-50 text-slate-700 font-medium text-xs transition border border-sky-200 shadow-xs"
              >
                <Edit3 className="w-3 h-3 text-sky-600" />
                <span>Override</span>
              </button>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-[11px] mb-2 font-mono">
              <div className="p-2 rounded-lg bg-white border border-sky-100 shadow-xs">
                <span className="text-slate-400 block text-[9px] uppercase font-sans font-medium">Value & Unit</span>
                <span className="text-sky-700 font-semibold">
                  {selectedParam.quantitative_data?.value !== null && selectedParam.quantitative_data?.value !== undefined
                    ? `${selectedParam.quantitative_data.value} ${selectedParam.quantitative_data.unit_standardized || ''}`
                    : selectedParam.quantitative_data?.value_text || 'None'}
                </span>
              </div>

              <div className="p-2 rounded-lg bg-white border border-sky-100 shadow-xs">
                <span className="text-slate-400 block text-[9px] uppercase font-sans font-medium">Context</span>
                <span className="text-slate-800">
                  {selectedParam.context?.compound || 'N/A'} &bull; {selectedParam.context?.species || 'N/A'}
                </span>
              </div>

              <div className="p-2 rounded-lg bg-white border border-sky-100 shadow-xs">
                <span className="text-slate-400 block text-[9px] uppercase font-sans font-medium">Source Table / Page</span>
                <span className="text-slate-800">
                  {selectedParam.provenance?.source_table || `Page ${selectedParam.provenance?.source_page || 'N/A'}`}
                </span>
              </div>

              <div className="p-2 rounded-lg bg-white border border-sky-100 shadow-xs">
                <span className="text-slate-400 block text-[9px] uppercase font-sans font-medium">Status / Confidence</span>
                <span className="text-slate-800">
                  {selectedParam.provenance?.status || 'literature'} ({selectedParam.provenance?.confidence || 'normal'})
                </span>
              </div>
            </div>

            {/* Validation Flags for this parameter */}
            {selectedParamFlags.length > 0 && (
              <div className="p-2.5 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-[11px] space-y-1">
                {selectedParamFlags.map((flag, fi) => (
                  <div key={fi} className="flex items-start gap-1.5">
                    <AlertTriangle className="w-3.5 h-3.5 text-rose-600 shrink-0 mt-0.5" />
                    <div>
                      <span className="font-bold uppercase tracking-wider text-[10px] text-rose-700">{flag.rule}: </span>
                      <span>{flag.message}</span>
                      {flag.suggested_fix && (
                        <span className="text-rose-700 block italic text-[10px] mt-0.5">
                          Fix: {flag.suggested_fix}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Edit Modal */}
      {editingParam && (
        <ParameterEditModal
          parameter={editingParam}
          onClose={() => setEditingParam(null)}
          onSave={onUpdateParameter}
        />
      )}
    </div>
  );
};
