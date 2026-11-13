import React, { useState } from 'react';
import { ExtractedParameter } from '../types';
import { X, Save, Check } from 'lucide-react';

interface ParameterEditModalProps {
  parameter: ExtractedParameter;
  onClose: () => void;
  onSave: (paramId: string, updates: any) => Promise<void>;
}

export const ParameterEditModal: React.FC<ParameterEditModalProps> = ({
  parameter,
  onClose,
  onSave,
}) => {
  const [val, setVal] = useState<string>(
    parameter.quantitative_data?.value !== undefined && parameter.quantitative_data?.value !== null
      ? String(parameter.quantitative_data.value)
      : ''
  );
  const [valText, setValText] = useState<string>(parameter.quantitative_data?.value_text || '');
  const [unit, setUnit] = useState<string>(
    parameter.quantitative_data?.unit_standardized || parameter.quantitative_data?.unit || ''
  );
  const [paramName, setParamName] = useState<string>(
    parameter.parameter_name_standardized || parameter.parameter_name_original || ''
  );
  const [compound, setCompound] = useState<string>(parameter.context?.compound || '');
  const [species, setSpecies] = useState<string>(parameter.context?.species || '');
  const [notes, setNotes] = useState<string>(parameter.provenance?.curator_notes || '');
  const [isSaving, setIsSaving] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    try {
      const parsedVal = val.trim() === '' ? null : parseFloat(val);
      await onSave(parameter.parameter_id, {
        value: parsedVal,
        value_text: valText.trim() || undefined,
        unit: unit.trim() || undefined,
        parameter_name: paramName.trim() || undefined,
        compound: compound.trim() || undefined,
        species: species.trim() || undefined,
        notes: notes.trim() || undefined,
        status: 'reviewed_by_curator',
      });
      onClose();
    } catch (err) {
      alert(`Save failed: ${err}`);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4">
      <div className="bg-white border border-sky-100 rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-sky-100 bg-sky-50/70">
          <div>
            <h3 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
              Edit Parameter
              <span className="text-[10px] font-mono bg-sky-100 text-sky-800 font-semibold px-2 py-0.5 rounded">
                {parameter.parameter_id}
              </span>
            </h3>
            <p className="text-xs text-slate-500 truncate max-w-xs">
              {parameter.parameter_name_original || parameter.symbol_original}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-sky-100/60 transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-5 space-y-4 text-xs">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-slate-600 mb-1 font-medium">Standardized Name</label>
              <input
                type="text"
                value={paramName}
                onChange={(e) => setParamName(e.target.value)}
                className="w-full bg-sky-50/30 border border-slate-200 rounded-lg px-3 py-1.5 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500 focus:bg-white transition font-sans"
              />
            </div>
            <div>
              <label className="block text-slate-600 mb-1 font-medium">Unit</label>
              <input
                type="text"
                value={unit}
                onChange={(e) => setUnit(e.target.value)}
                placeholder="e.g. L/kg, h^-1, dimensionless"
                className="w-full bg-sky-50/30 border border-slate-200 rounded-lg px-3 py-1.5 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500 focus:bg-white transition font-mono text-[11px]"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-slate-600 mb-1 font-medium">Numeric Value (float)</label>
              <input
                type="number"
                step="any"
                value={val}
                onChange={(e) => setVal(e.target.value)}
                className="w-full bg-sky-50/30 border border-slate-200 rounded-lg px-3 py-1.5 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500 focus:bg-white transition font-mono text-[11px]"
              />
            </div>
            <div>
              <label className="block text-slate-600 mb-1 font-medium">Verbatim Value Text</label>
              <input
                type="text"
                value={valText}
                onChange={(e) => setValText(e.target.value)}
                placeholder="e.g. 56.9 - 70"
                className="w-full bg-sky-50/30 border border-slate-200 rounded-lg px-3 py-1.5 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500 focus:bg-white transition font-mono text-[11px]"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-slate-600 mb-1 font-medium">Compound</label>
              <input
                type="text"
                value={compound}
                onChange={(e) => setCompound(e.target.value)}
                className="w-full bg-sky-50/30 border border-slate-200 rounded-lg px-3 py-1.5 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500 focus:bg-white transition"
              />
            </div>
            <div>
              <label className="block text-slate-600 mb-1 font-medium">Species</label>
              <input
                type="text"
                value={species}
                onChange={(e) => setSpecies(e.target.value)}
                className="w-full bg-sky-50/30 border border-slate-200 rounded-lg px-3 py-1.5 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500 focus:bg-white transition"
              />
            </div>
          </div>

          <div>
            <label className="block text-slate-600 mb-1 font-medium">Curator Notes / Reason for change</label>
            <textarea
              rows={2}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Explain rationale for this override..."
              className="w-full bg-sky-50/30 border border-slate-200 rounded-lg px-3 py-1.5 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500 focus:bg-white transition resize-none"
            />
          </div>

          <div className="flex items-center justify-end gap-2 pt-3 border-t border-sky-100">
            <button
              type="button"
              onClick={onClose}
              className="px-3.5 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 font-medium transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSaving}
              className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-medium shadow-xs transition disabled:opacity-50"
            >
              <Save className="w-3.5 h-3.5" />
              <span>{isSaving ? 'Saving...' : 'Save Override'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

