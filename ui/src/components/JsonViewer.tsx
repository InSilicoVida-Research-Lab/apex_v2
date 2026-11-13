import React, { useState } from 'react';
import { ExtractedDocument } from '../types';
import { Copy, Check, Download, FileSpreadsheet, Code2 } from 'lucide-react';

interface JsonViewerProps {
  document: ExtractedDocument;
  docId: string;
}

export const JsonViewer: React.FC<JsonViewerProps> = ({ document, docId }) => {
  const [copied, setCopied] = useState(false);

  const jsonStr = JSON.stringify(document, null, 2);

  const handleCopy = () => {
    navigator.clipboard.writeText(jsonStr);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadJson = () => {
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = window.document.createElement('a');
    a.href = url;
    a.download = docId.endsWith('.json') ? docId : `${docId}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleDownloadCsv = () => {
    const params = document.model_parameters || [];
    const headers = [
      'parameter_id',
      'parameter_name',
      'symbol',
      'subclass',
      'value',
      'value_text',
      'unit',
      'compound',
      'species',
      'organ',
      'source_table',
      'source_page',
      'confidence',
      'source_quote',
    ];

    const rows = params.map((p) => {
      const q = p.quantitative_data || {};
      const ctx = p.context || {};
      const prov = p.provenance || {};

      const escape = (val: any) => {
        if (val === null || val === undefined) return '""';
        const str = String(val).replace(/"/g, '""');
        return `"${str}"`;
      };

      return [
        escape(p.parameter_id),
        escape(p.parameter_name_standardized || p.parameter_name_original || ''),
        escape(p.symbol_original || ''),
        escape(p.parameter_subclass || p.parameter_class || ''),
        escape(q.value),
        escape(q.value_text),
        escape(q.unit_standardized || q.unit_original || ''),
        escape(ctx.compound),
        escape(ctx.species),
        escape(ctx.organ),
        escape(prov.source_table),
        escape(prov.source_page),
        escape(prov.confidence),
        escape(prov.source_quote),
      ].join(',');
    });

    const csvContent = [headers.join(','), ...rows].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = window.document.createElement('a');
    a.href = url;
    a.download = `${docId.replace('.json', '')}_parameters.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="h-[calc(100vh-82px)] flex flex-col bg-slate-50 p-6 space-y-4">
      {/* Action Toolbar */}
      <div className="flex items-center justify-between bg-white px-4 py-3 rounded-xl border border-sky-100 shadow-xs">
        <div className="flex items-center gap-2">
          <Code2 className="w-4 h-4 text-indigo-600" />
          <span className="text-xs font-semibold text-slate-800">
            Raw Document Payload ({docId})
          </span>
          <span className="text-[10px] font-mono bg-sky-100 text-sky-800 px-2 py-0.5 rounded font-medium border border-sky-200">
            {(jsonStr.length / 1024).toFixed(1)} KB
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleCopy}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white hover:bg-sky-50 text-slate-700 font-medium text-xs transition border border-sky-200"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5 text-slate-500" />}
            <span>{copied ? 'Copied' : 'Copy JSON'}</span>
          </button>

          <button
            onClick={handleDownloadJson}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white hover:bg-sky-50 text-slate-700 font-medium text-xs transition border border-sky-200"
          >
            <Download className="w-3.5 h-3.5 text-sky-600" />
            <span>Download JSON</span>
          </button>

          <button
            onClick={handleDownloadCsv}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-medium text-xs transition shadow-xs"
          >
            <FileSpreadsheet className="w-3.5 h-3.5" />
            <span>Export Parameters CSV</span>
          </button>
        </div>
      </div>

      {/* Code Viewer */}
      <div className="flex-1 bg-white border border-sky-100 rounded-xl overflow-hidden p-4 shadow-xs">
        <pre className="h-full overflow-y-auto font-mono text-xs text-slate-800 selection:bg-sky-200 leading-relaxed">
          {jsonStr}
        </pre>
      </div>
    </div>
  );
};

