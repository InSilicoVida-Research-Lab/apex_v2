import React, { useState, useMemo } from 'react';
import { VerificationReport, ParameterFlag, ExtractedDocument } from '../types';
import { 
  ShieldAlert, 
  CheckCircle, 
  AlertTriangle, 
  Info, 
  Zap, 
  Clock, 
  SlidersHorizontal,
  Search,
  ExternalLink,
  Wrench
} from 'lucide-react';

interface VerificationDashboardProps {
  report: VerificationReport;
  document: ExtractedDocument;
  onUpdateParameter: (paramId: string, updates: any) => Promise<void>;
  onInspectParam: (paramIndex: number) => void;
}

export const VerificationDashboard: React.FC<VerificationDashboardProps> = ({
  report,
  document,
  onUpdateParameter,
  onInspectParam,
}) => {
  const [selectedRule, setSelectedRule] = useState<string>('all');
  const [severityFilter, setSeverityFilter] = useState<'all' | 'error' | 'warning'>('all');
  const [search, setSearch] = useState<string>('');

  const params = document.model_parameters || [];
  const flags = report.flags || [];

  // Group flags by rule name
  const ruleCounts = useMemo(() => {
    const map = new Map<string, number>();
    flags.forEach((f) => {
      map.set(f.rule, (map.get(f.rule) || 0) + 1);
    });
    return map;
  }, [flags]);

  const filteredFlags = useMemo(() => {
    return flags.filter((f) => {
      if (selectedRule !== 'all' && f.rule !== selectedRule) return false;
      if (severityFilter !== 'all' && f.severity !== severityFilter) return false;
      if (search.trim()) {
        const q = search.toLowerCase();
        const matches =
          f.param_name.toLowerCase().includes(q) ||
          f.rule.toLowerCase().includes(q) ||
          f.message.toLowerCase().includes(q) ||
          (f.suggested_fix || '').toLowerCase().includes(q);
        if (!matches) return false;
      }
      return true;
    });
  }, [flags, selectedRule, severityFilter, search]);

  const handleApplyFix = async (flag: ParameterFlag) => {
    const targetParam = params[flag.param_index];
    if (!targetParam) return;

    // Check if suggested fix has numeric value
    if (flag.rule === 'CELL_VALUE_MISMATCH' && flag.suggested_fix) {
      const match = flag.suggested_fix.match(/([\d.]+)/);
      if (match) {
        const fixedVal = parseFloat(match[1]);
        await onUpdateParameter(targetParam.parameter_id, {
          value: fixedVal,
          notes: `Adopted cell value ${fixedVal} from Rule Engine suggestion.`,
        });
        alert(`Adopted value ${fixedVal} for ${targetParam.parameter_name_original}`);
      }
    } else {
      onInspectParam(flag.param_index);
    }
  };

  return (
    <div className="h-[calc(100vh-82px)] overflow-y-auto bg-slate-50 p-6 space-y-6">
      {/* ----------------- METRICS HEADER ----------------- */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <div className="p-4 rounded-xl bg-white border border-sky-100 shadow-xs">
          <div className="flex items-center gap-1.5 text-slate-500 text-xs mb-1 font-medium">
            <SlidersHorizontal className="w-3.5 h-3.5 text-sky-600" />
            <span>Parameters Evaluated</span>
          </div>
          <span className="text-2xl font-bold font-mono text-slate-900">{report.total_parameters}</span>
        </div>

        <div className="p-4 rounded-xl bg-white border border-sky-100 shadow-xs">
          <div className="flex items-center gap-1.5 text-slate-500 text-xs mb-1 font-medium">
            <CheckCircle className="w-3.5 h-3.5 text-emerald-600" />
            <span>Clean Parameters</span>
          </div>
          <span className="text-2xl font-bold font-mono text-emerald-600">
            {report.total_parameters - report.parameters_with_flags}
          </span>
        </div>

        <div className="p-4 rounded-xl bg-white border border-sky-100 shadow-xs">
          <div className="flex items-center gap-1.5 text-slate-500 text-xs mb-1 font-medium">
            <AlertTriangle className="w-3.5 h-3.5 text-rose-500" />
            <span>Validation Errors</span>
          </div>
          <span className="text-2xl font-bold font-mono text-rose-600">{report.error_count}</span>
        </div>

        <div className="p-4 rounded-xl bg-white border border-sky-100 shadow-xs">
          <div className="flex items-center gap-1.5 text-slate-500 text-xs mb-1 font-medium">
            <Info className="w-3.5 h-3.5 text-amber-500" />
            <span>Warnings</span>
          </div>
          <span className="text-2xl font-bold font-mono text-amber-600">{report.warning_count}</span>
        </div>

        <div className="p-4 rounded-xl bg-white border border-sky-100 shadow-xs">
          <div className="flex items-center gap-1.5 text-slate-500 text-xs mb-1 font-medium">
            <Clock className="w-3.5 h-3.5 text-sky-600" />
            <span>Execution Time</span>
          </div>
          <span className="text-2xl font-bold font-mono text-sky-700">
            {report.elapsed_ms.toFixed(1)} ms
          </span>
        </div>
      </div>

      {/* Summary statement */}
      {report.summary && (
        <div className="p-3.5 rounded-xl bg-sky-50/70 border border-sky-200 text-xs text-slate-700 font-mono">
          <span className="text-sky-800 font-bold uppercase tracking-wider block text-[10px] mb-0.5">
            Rule Engine Audit Summary
          </span>
          {report.summary}
        </div>
      )}

      {/* ----------------- FILTER BY RULE & SEVERITY ----------------- */}
      <div className="flex flex-col md:flex-row items-center justify-between gap-3 bg-white p-3 rounded-xl border border-sky-100 shadow-xs text-xs">
        <div className="flex items-center gap-2 w-full md:w-auto">
          <div className="relative flex-1 md:w-64">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search flags or rules..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-sky-50/50 border border-sky-200 text-slate-800 text-xs rounded-lg pl-8 pr-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-sky-500 placeholder:text-slate-400"
            />
          </div>

          <div className="flex rounded-lg bg-sky-50/60 p-0.5 border border-sky-200">
            {(['all', 'error', 'warning'] as const).map((sev) => (
              <button
                key={sev}
                onClick={() => setSeverityFilter(sev)}
                className={`px-2.5 py-1 rounded-md text-[11px] font-medium capitalize transition ${
                  severityFilter === sev ? 'bg-sky-600 text-white shadow-xs' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {sev}
              </button>
            ))}
          </div>
        </div>

        {/* Rule chips */}
        <div className="flex items-center gap-1.5 overflow-x-auto w-full md:w-auto no-scrollbar">
          <button
            onClick={() => setSelectedRule('all')}
            className={`px-2.5 py-1 rounded-md text-[11px] font-mono whitespace-nowrap transition ${
              selectedRule === 'all'
                ? 'bg-sky-600 text-white font-bold shadow-xs'
                : 'bg-white text-slate-600 border border-slate-200 hover:bg-sky-50'
            }`}
          >
            All Rules ({flags.length})
          </button>
          {Array.from(ruleCounts.entries()).map(([rule, count]) => (
            <button
              key={rule}
              onClick={() => setSelectedRule(rule)}
              className={`px-2.5 py-1 rounded-md text-[11px] font-mono whitespace-nowrap transition ${
                selectedRule === rule
                  ? 'bg-sky-600 text-white font-bold shadow-xs'
                  : 'bg-white text-slate-600 border border-slate-200 hover:bg-sky-50'
              }`}
            >
              {rule} ({count})
            </button>
          ))}
        </div>
      </div>

      {/* ----------------- FLAGS LIST ----------------- */}
      <div className="space-y-3">
        {filteredFlags.length === 0 ? (
          <div className="text-center py-16 bg-white border border-sky-100 rounded-xl shadow-xs">
            <CheckCircle className="w-10 h-10 text-emerald-500 mx-auto mb-2 opacity-80" />
            <h3 className="text-sm font-semibold text-slate-800">No Validation Flags</h3>
            <p className="text-xs text-slate-500 mt-1">All extracted parameters passed the active rule checks.</p>
          </div>
        ) : (
          filteredFlags.map((flag, idx) => {
            const targetParam = params[flag.param_index];
            const isError = flag.severity === 'error';

            return (
              <div
                key={idx}
                className={`p-4 rounded-xl border text-xs transition shadow-xs ${
                  isError
                    ? 'bg-white border-rose-200 hover:border-rose-400'
                    : 'bg-white border-amber-200 hover:border-amber-400'
                }`}
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2">
                    <span
                      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold font-mono uppercase ${
                        isError ? 'bg-rose-50 text-rose-700 border border-rose-200' : 'bg-amber-50 text-amber-700 border border-amber-200'
                      }`}
                    >
                      {isError ? <AlertTriangle className="w-3 h-3" /> : <Info className="w-3 h-3" />}
                      {flag.severity}
                    </span>
                    <span className="font-mono text-xs font-bold text-sky-800 bg-sky-50 px-2 py-0.5 rounded border border-sky-200">
                      {flag.rule}
                    </span>
                    <span className="text-slate-500 text-xs">
                      Parameter Index #{flag.param_index}
                    </span>
                  </div>

                  <button
                    onClick={() => onInspectParam(flag.param_index)}
                    className="flex items-center gap-1 text-[11px] text-sky-700 hover:text-sky-900 font-medium transition self-start sm:self-auto"
                  >
                    <span>Inspect Parameter</span>
                    <ExternalLink className="w-3 h-3" />
                  </button>
                </div>

                <div className="mb-2">
                  <h4 className="font-semibold text-slate-900 text-sm mb-1">
                    {flag.param_name}
                  </h4>
                  <p className="text-slate-600 text-xs leading-relaxed">
                    {flag.message}
                  </p>
                </div>

                {flag.suggested_fix && (
                  <div className="mt-2.5 p-2.5 rounded-lg bg-sky-50/60 border border-sky-100 flex items-center justify-between gap-3">
                    <div className="text-[11px] text-slate-600 flex items-center gap-1.5">
                      <Wrench className="w-3.5 h-3.5 text-sky-600 shrink-0" />
                      <span>Suggested Fix: <strong className="text-slate-900">{flag.suggested_fix}</strong></span>
                    </div>

                    <button
                      onClick={() => handleApplyFix(flag)}
                      className="px-2.5 py-1 rounded bg-sky-600 hover:bg-sky-500 text-white font-medium text-[11px] whitespace-nowrap transition shadow-xs"
                    >
                      Apply / Edit
                    </button>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

