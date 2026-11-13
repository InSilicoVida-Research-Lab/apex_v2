import React, { useState, useMemo } from 'react';
import { TanPBPKAssessment, TanQuestionnaireItem } from '../types';
import { 
  CheckCircle2, 
  HelpCircle, 
  AlertCircle, 
  XCircle, 
  ChevronDown, 
  ChevronUp, 
  Quote, 
  ShieldCheck, 
  Layers, 
  Sparkles,
  Search,
  Filter
} from 'lucide-react';

interface TanScorecardProps {
  assessment: TanPBPKAssessment;
}

export const TanScorecard: React.FC<TanScorecardProps> = ({ assessment }) => {
  const [search, setSearch] = useState('');
  const [responseFilter, setResponseFilter] = useState<string>('all');
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set(['TAN_1.1']));

  const items = assessment.items || [];

  const counts = useMemo(() => {
    let yes = 0, partially = 0, no = 0, cannot = 0;
    items.forEach((item) => {
      const resp = String(item.response || '').toLowerCase();
      if (resp === 'yes') yes++;
      else if (resp === 'partially') partially++;
      else if (resp === 'no') no++;
      else cannot++;
    });
    return { yes, partially, no, cannot, total: items.length };
  }, [items]);

  const completenessPct = counts.total > 0 ? Math.round(((counts.yes + counts.partially) / counts.total) * 100) : 0;

  // Toggle item expansion
  const toggleExpand = (id: string) => {
    setExpandedItems((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const expandAll = () => {
    setExpandedItems(new Set(items.map((i) => i.item_id)));
  };

  const collapseAll = () => {
    setExpandedItems(new Set());
  };

  // Group items by Section
  const groupedSections = useMemo(() => {
    const groups: { [key: string]: TanQuestionnaireItem[] } = {};
    items.forEach((item) => {
      const resp = String(item.response || '').toLowerCase();
      if (responseFilter !== 'all' && resp !== responseFilter) return;

      if (search.trim()) {
        const q = search.toLowerCase();
        const matches =
          item.item_id.toLowerCase().includes(q) ||
          item.question.toLowerCase().includes(q) ||
          item.details.toLowerCase().includes(q) ||
          (item.evidence || []).some((e) => (e.source_quote || '').toLowerCase().includes(q));
        if (!matches) return;
      }

      const sec = item.section || 'General';
      if (!groups[sec]) groups[sec] = [];
      groups[sec].push(item);
    });
    return groups;
  }, [items, search, responseFilter]);

  const renderResponseBadge = (response: string) => {
    const r = String(response || '').toLowerCase();
    switch (r) {
      case 'yes':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
            <CheckCircle2 className="w-3 h-3" />
            YES
          </span>
        );
      case 'partially':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-50 text-amber-700 border border-amber-200">
            <AlertCircle className="w-3 h-3" />
            PARTIALLY
          </span>
        );
      case 'no':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-rose-50 text-rose-700 border border-rose-200">
            <XCircle className="w-3 h-3" />
            NO
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-slate-100 text-slate-600 border border-slate-200">
            <HelpCircle className="w-3 h-3" />
            I CANNOT ANSWER
          </span>
        );
    }
  };

  return (
    <div className="h-[calc(100vh-82px)] overflow-y-auto bg-slate-50 p-6 space-y-6">
      {/* ----------------- EXECUTIVE SUMMARY & FIT FOR PURPOSE ----------------- */}
      <div className="bg-white border border-sky-100 rounded-2xl p-5 shadow-xs">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 mb-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-mono uppercase tracking-widest text-sky-700 font-semibold">
                WHO / OECD Harmonized Evaluation
              </span>
              <span className="text-[10px] bg-sky-100 text-sky-800 px-2 py-0.5 rounded font-mono border border-sky-200">
                {assessment.template_version || 'Refined-Tan-PBPK-v1'}
              </span>
            </div>
            <h2 className="text-lg font-bold text-slate-900 tracking-tight">
              {assessment.template_name || 'Refined Tan et al. PBPK Reporting Assessment'}
            </h2>
          </div>

          <div className="flex items-center gap-2">
            <div className="text-right mr-2">
              <span className="text-[10px] uppercase font-mono text-slate-500 block font-medium">Overall Evidence Rate</span>
              <span className="text-xl font-bold font-mono text-emerald-600">
                {counts.yes + counts.partially}/{counts.total} ({completenessPct}%)
              </span>
            </div>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="w-full bg-slate-100 rounded-full h-2.5 border border-slate-200 overflow-hidden flex mb-4">
          <div style={{ width: `${(counts.yes / counts.total) * 100}%` }} className="bg-emerald-500 h-full" title={`Yes: ${counts.yes}`} />
          <div style={{ width: `${(counts.partially / counts.total) * 100}%` }} className="bg-amber-400 h-full" title={`Partially: ${counts.partially}`} />
          <div style={{ width: `${(counts.no / counts.total) * 100}%` }} className="bg-rose-500 h-full" title={`No: ${counts.no}`} />
          <div style={{ width: `${(counts.cannot / counts.total) * 100}%` }} className="bg-slate-300 h-full" title={`Cannot answer: ${counts.cannot}`} />
        </div>

        {/* Stats Chips */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
          <div className="p-3 rounded-xl bg-sky-50/50 border border-sky-100 flex items-center justify-between">
            <span className="text-slate-600 font-medium">Fully Supported (Yes)</span>
            <span className="text-emerald-600 font-bold font-mono text-base">{counts.yes}</span>
          </div>
          <div className="p-3 rounded-xl bg-sky-50/50 border border-sky-100 flex items-center justify-between">
            <span className="text-slate-600 font-medium">Partial Evidence</span>
            <span className="text-amber-600 font-bold font-mono text-base">{counts.partially}</span>
          </div>
          <div className="p-3 rounded-xl bg-sky-50/50 border border-sky-100 flex items-center justify-between">
            <span className="text-slate-600 font-medium">Unanswered / Gaps</span>
            <span className="text-slate-500 font-bold font-mono text-base">{counts.cannot}</span>
          </div>
          <div className="p-3 rounded-xl bg-sky-50/50 border border-sky-100 flex items-center justify-between">
            <span className="text-slate-600 font-medium">Explicit Negatives (No)</span>
            <span className="text-rose-600 font-bold font-mono text-base">{counts.no}</span>
          </div>
        </div>

        {/* Overall Fit-for-Purpose statement */}
        {assessment.overall_fit_for_purpose && (
          <div className="mt-4 p-3 rounded-xl bg-sky-50/80 border border-sky-200 text-xs text-slate-700 flex items-start gap-2">
            <Sparkles className="w-4 h-4 text-sky-600 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold text-slate-900">Fit-for-Purpose Assessment: </span>
              <span>{assessment.overall_fit_for_purpose}</span>
            </div>
          </div>
        )}
      </div>

      {/* ----------------- SEARCH & FILTERS BAR ----------------- */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-white p-3 rounded-xl border border-sky-100 shadow-xs">
        <div className="flex items-center gap-2 w-full sm:w-auto">
          <div className="relative flex-1 sm:w-64">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search Tan questions, quotes..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-sky-50/50 border border-sky-200 text-slate-800 text-xs rounded-lg pl-8 pr-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-sky-500 placeholder:text-slate-400 font-sans"
            />
          </div>

          <div className="flex rounded-lg bg-sky-50/60 p-0.5 border border-sky-200 text-xs">
            {['all', 'yes', 'partially', 'i_cannot_answer'].map((f) => (
              <button
                key={f}
                onClick={() => setResponseFilter(f)}
                className={`px-2.5 py-1 rounded-md text-[11px] font-medium capitalize transition ${
                  responseFilter === f ? 'bg-sky-600 text-white shadow-xs' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {f.replace(/_/g, ' ')}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs">
          <button
            onClick={expandAll}
            className="px-2.5 py-1 rounded bg-white hover:bg-sky-50 text-slate-700 border border-sky-200 font-medium transition text-[11px]"
          >
            Expand All
          </button>
          <button
            onClick={collapseAll}
            className="px-2.5 py-1 rounded bg-white hover:bg-sky-50 text-slate-700 border border-sky-200 font-medium transition text-[11px]"
          >
            Collapse All
          </button>
        </div>
      </div>

      {/* ----------------- GROUPED TAN QUESTIONNAIRE SECTIONS ----------------- */}
      <div className="space-y-6">
        {Object.keys(groupedSections).length === 0 ? (
          <div className="text-center py-12 text-slate-400 text-sm">
            No Tan questionnaire items match your search.
          </div>
        ) : (
          Object.entries(groupedSections).map(([sectionTitle, secItems]) => (
            <div key={sectionTitle} className="bg-white border border-sky-100 rounded-xl overflow-hidden shadow-xs">
              <div className="bg-sky-50/70 px-4 py-2.5 border-b border-sky-100 flex items-center justify-between">
                <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider font-mono flex items-center gap-2">
                  <Layers className="w-3.5 h-3.5 text-sky-600" />
                  {sectionTitle}
                </h3>
                <span className="text-[11px] font-mono text-slate-500 font-medium">
                  {secItems.length} {secItems.length === 1 ? 'item' : 'items'}
                </span>
              </div>

              <div className="divide-y divide-sky-100/70">
                {secItems.map((item) => {
                  const isExpanded = expandedItems.has(item.item_id);
                  const evidenceList = item.evidence || [];

                  return (
                    <div key={item.item_id} className="p-4 transition hover:bg-sky-50/40">
                      <div
                        onClick={() => toggleExpand(item.item_id)}
                        className="cursor-pointer flex items-start justify-between gap-4"
                      >
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1.5">
                            <span className="font-mono font-bold text-xs text-sky-800 bg-sky-100 border border-sky-200 px-2 py-0.5 rounded">
                              {item.item_id}
                            </span>
                            {renderResponseBadge(item.response)}
                            {item.confidence && (
                              <span
                                className={`text-[10px] font-bold font-mono uppercase px-2 py-0.5 rounded border ${
                                  item.confidence === 'high'
                                    ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                                    : item.confidence === 'medium'
                                    ? 'bg-amber-50 text-amber-700 border-amber-200'
                                    : 'bg-slate-100 text-slate-600 border-slate-200'
                                }`}
                              >
                                {item.confidence} confidence
                              </span>
                            )}
                          </div>
                          <h4 className="text-sm font-semibold text-slate-900 leading-snug">
                            {item.question}
                          </h4>
                          <p className="text-xs text-slate-600 mt-1 line-clamp-2">
                            {item.details}
                          </p>
                        </div>

                        <button className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-sky-100 transition shrink-0 mt-1">
                          {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                        </button>
                      </div>

                      {/* Expandable Evidence Drawer */}
                      {isExpanded && (
                        <div className="mt-4 pt-3 border-t border-sky-100 space-y-3 animate-in fade-in duration-100">
                          {/* Confidence explanation */}
                          {item.confidence_basis && (
                            <div className="text-[11px] text-slate-500 flex items-center gap-1.5 font-mono">
                              <ShieldCheck className="w-3.5 h-3.5 text-sky-600" />
                              <span>Basis: {item.confidence_basis}</span>
                            </div>
                          )}

                          {/* Evidence Quotes */}
                          {evidenceList.length > 0 ? (
                            <div className="space-y-2">
                              <span className="text-[10px] font-mono uppercase tracking-wider text-slate-500 font-bold block">
                                Auditable Evidence Snippets ({evidenceList.length})
                              </span>
                              {evidenceList.map((ev, ei) => (
                                <div
                                  key={ei}
                                  className="p-3 rounded-lg bg-sky-50/50 border border-sky-100 text-xs flex items-start gap-2.5"
                                >
                                  <Quote className="w-3.5 h-3.5 text-sky-600 shrink-0 mt-0.5" />
                                  <div className="flex-1 min-w-0">
                                    {ev.source_quote && (
                                      <p className="text-slate-800 italic mb-1.5">
                                        &ldquo;{ev.source_quote}&rdquo;
                                      </p>
                                    )}
                                    <div className="flex items-center gap-3 text-[10px] font-mono text-slate-500">
                                      {ev.source_page && (
                                        <span className="bg-sky-100 px-1.5 py-0.5 rounded text-sky-800 font-medium border border-sky-200">
                                          Page {ev.source_page}
                                        </span>
                                      )}
                                      {ev.source_location && (
                                        <span>Location: {ev.source_location}</span>
                                      )}
                                      {ev.source_section && (
                                        <span>Section: {ev.source_section}</span>
                                      )}
                                    </div>
                                  </div>
                                </div>
                              ))}
                            </div>
                          ) : (
                            <div className="text-[11px] text-slate-400 italic">
                              No explicit verbatim evidence quotes captured for this item.
                            </div>
                          )}

                          {/* Structured Details if present */}
                          {item.structured_details && Object.keys(item.structured_details).length > 0 && (
                            <div className="mt-2">
                              <span className="text-[10px] font-mono uppercase tracking-wider text-slate-500 font-bold block mb-1">
                                Structured Model Parameters
                              </span>
                              <pre className="p-2.5 rounded bg-slate-50 border border-slate-200 text-[11px] font-mono text-slate-700 overflow-x-auto">
                                {JSON.stringify(item.structured_details, null, 2)}
                              </pre>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

