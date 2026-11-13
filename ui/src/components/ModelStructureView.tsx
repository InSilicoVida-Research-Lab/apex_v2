import React from 'react';
import { ExtractedDocument } from '../types';
import { 
  Network, 
  ArrowRight, 
  ArrowLeftRight, 
  Cpu, 
  Layers, 
  Zap, 
  Clock, 
  CheckCircle,
  FileCode,
  Droplet
} from 'lucide-react';

interface ModelStructureViewProps {
  document: ExtractedDocument;
}

export const ModelStructureView: React.FC<ModelStructureViewProps> = ({ document }) => {
  const structure = document.model_structure || {};
  const software = document.software || {};
  const dosing = document.dosing || [];
  const compartments = structure.compartments || [];
  const connections = structure.connections || [];
  const classification = document.model_classification || {};

  return (
    <div className="h-[calc(100vh-82px)] overflow-y-auto bg-slate-50 p-6 space-y-6">
      {/* ----------------- STRUCTURE & CLASSIFICATION SUMMARY ----------------- */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-4 rounded-xl bg-white border border-sky-100 shadow-xs">
          <span className="text-[10px] uppercase font-mono tracking-wider text-slate-500 block mb-1 font-medium">
            Model Classification
          </span>
          <h3 className="text-lg font-bold text-slate-900 capitalize">
            {classification.model_type || structure.model_type || 'PBPK Model'}
          </h3>
          {classification.evidence_quote && (
            <p className="text-xs text-slate-600 italic mt-2 line-clamp-3">
              &ldquo;{classification.evidence_quote}&rdquo;
            </p>
          )}
        </div>

        <div className="p-4 rounded-xl bg-white border border-sky-100 shadow-xs">
          <span className="text-[10px] uppercase font-mono tracking-wider text-slate-500 block mb-1 font-medium">
            Equations & Derivations
          </span>
          <h3 className="text-lg font-bold text-sky-700 capitalize">
            {structure.equations_provided || 'Model Diagram & ODEs'}
          </h3>
          <p className="text-xs text-slate-600 mt-2">
            Compartmental mass balance differential equations with perfusion-limited kinetics.
          </p>
        </div>

        <div className="p-4 rounded-xl bg-white border border-sky-100 shadow-xs">
          <span className="text-[10px] uppercase font-mono tracking-wider text-slate-500 block mb-1 font-medium">
            Software & Implementation
          </span>
          <h3 className="text-lg font-bold text-emerald-600">
            {software.name || 'Not Explicitly Reported'} {software.version ? `v${software.version}` : ''}
          </h3>
          <div className="text-xs text-slate-600 mt-2 space-y-1 font-mono text-[11px]">
            {software.solver && <div>Solver: {software.solver}</div>}
            {software.optimization_method && <div>Optimizer: {software.optimization_method}</div>}
          </div>
        </div>
      </div>

      {/* ----------------- COMPARTMENTS GRID ----------------- */}
      <div className="bg-white border border-sky-100 rounded-xl p-5 shadow-xs">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <Layers className="w-4 h-4 text-sky-600" />
            Extracted Model Compartments ({compartments.length})
          </h3>
          <span className="text-xs font-mono text-slate-500">Mass-Balance Tissues</span>
        </div>

        {compartments.length === 0 ? (
          <div className="p-8 text-center text-slate-400 text-xs">
            No explicit compartments array listed in extraction metadata.
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-2.5">
            {compartments.map((comp, idx) => (
              <div
                key={idx}
                className="p-3 rounded-lg bg-sky-50/60 border border-sky-200/80 hover:border-sky-400 transition group flex items-center gap-2"
              >
                <div className="w-2 h-2 rounded-full bg-sky-600 group-hover:scale-125 transition" />
                <span className="text-xs font-medium text-slate-800 truncate capitalize">
                  {comp}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ----------------- COMPARTMENT CONNECTIONS ----------------- */}
      <div className="bg-white border border-sky-100 rounded-xl p-5 shadow-xs">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <Network className="w-4 h-4 text-sky-600" />
            Compartment Connections & Blood Flows ({connections.length})
          </h3>
          <span className="text-xs font-mono text-slate-500">Perfusion & Clearance Routes</span>
        </div>

        {connections.length === 0 ? (
          <div className="p-8 text-center text-slate-400 text-xs">
            Perfusion connections are derived from arterial/venous circulatory loop in the mathematical model.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {connections.map((conn, idx) => (
              <div
                key={idx}
                className="p-3 rounded-lg bg-sky-50/50 border border-sky-100 flex items-center justify-between text-xs"
              >
                <span className="font-semibold text-slate-900">{conn.source}</span>
                {conn.direction === 'bidirectional' ? (
                  <ArrowLeftRight className="w-3.5 h-3.5 text-sky-600" />
                ) : (
                  <ArrowRight className="w-3.5 h-3.5 text-sky-600" />
                )}
                <span className="font-semibold text-slate-900">{conn.target}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ----------------- DOSING & EXPOSURE PROTOCOLS ----------------- */}
      {dosing.length > 0 && (
        <div className="bg-white border border-sky-100 rounded-xl p-5 shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Droplet className="w-4 h-4 text-emerald-600" />
              Dosing Protocols & Administration Routes ({dosing.length})
            </h3>
          </div>

          <div className="space-y-2">
            {dosing.map((d, idx) => (
              <div key={idx} className="p-3 rounded-lg bg-sky-50/40 border border-sky-100 text-xs">
                <div className="flex items-center justify-between mb-1">
                  <span className="font-bold text-slate-900">
                    Route: {d.route || 'Oral / Intravenous'} &bull; Compound: {d.compound || 'Test Compound'}
                  </span>
                  {d.dose_level && (
                    <span className="font-mono text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                      {d.dose_level} {d.dose_unit || 'mg/kg'}
                    </span>
                  )}
                </div>
                {d.source_quote && (
                  <p className="text-slate-600 italic text-[11px]">&ldquo;{d.source_quote}&rdquo;</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

