import React, { useState, useRef } from 'react';
import { 
  X, 
  UploadCloud, 
  FileText, 
  CheckCircle2, 
  AlertCircle, 
  Loader2, 
  FileSpreadsheet, 
  Check, 
  ArrowRight,
  ShieldCheck,
  FileType
} from 'lucide-react';
import { uploadDocument, UploadResponse } from '../api';

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUploadSuccess: (docId: string) => void;
}

export const UploadModal: React.FC<UploadModalProps> = ({
  isOpen,
  onClose,
  onUploadSuccess,
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [runTan, setRunTan] = useState<boolean>(true);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadProgressText, setUploadProgressText] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [successResult, setSuccessResult] = useState<UploadResponse | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const validateAndSetFile = (file: File) => {
    setError(null);
    setSuccessResult(null);
    const ext = file.name.split('.').pop()?.toLowerCase();
    if (!['pdf', 'json', 'md'].includes(ext || '')) {
      setError('Please select a supported file format: PDF (.pdf), JSON (.json), or Markdown (.md).');
      return;
    }
    setSelectedFile(file);
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const handleUpload = async () => {
    if (!selectedFile) return;
    setIsUploading(true);
    setError(null);
    setUploadProgressText('Uploading document to APEX workspace...');

    try {
      if (selectedFile.name.endsWith('.pdf')) {
        setUploadProgressText('Converting PDF pages and analyzing tables...');
      }
      const result = await uploadDocument(selectedFile, runTan);
      setSuccessResult(result);
      setUploadProgressText('Complete!');
    } catch (err: any) {
      setError(err.message || 'Upload failed');
    } finally {
      setIsUploading(false);
    }
  };

  const handleViewDocument = () => {
    if (successResult) {
      onUploadSuccess(successResult.doc_id);
      handleClose();
    }
  };

  const handleClose = () => {
    setSelectedFile(null);
    setIsUploading(false);
    setError(null);
    setSuccessResult(null);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4">
      <div className="bg-white border border-sky-100 rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-sky-100 bg-sky-50/70">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-sky-600 flex items-center justify-center text-white shadow-xs">
              <UploadCloud className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-900">Upload PBPK Paper / Dataset</h3>
              <p className="text-xs text-slate-500">Ingest PDF, JSON extracted dataset, or Markdown</p>
            </div>
          </div>
          <button
            onClick={handleClose}
            className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-sky-100/60 transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-5">
          {error && (
            <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center gap-2 animate-in fade-in">
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {successResult ? (
            /* Success State */
            <div className="p-5 rounded-xl bg-sky-50/60 border border-sky-200 text-center space-y-4 animate-in fade-in">
              <div className="w-12 h-12 rounded-full bg-emerald-100 text-emerald-600 mx-auto flex items-center justify-center shadow-xs">
                <CheckCircle2 className="w-6 h-6" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-slate-900 mb-1">Upload Successful!</h4>
                <p className="text-xs text-slate-600">{successResult.message}</p>
              </div>

              <div className="grid grid-cols-2 gap-2 text-left bg-white p-3 rounded-lg border border-sky-100 text-xs">
                <div>
                  <span className="text-[10px] uppercase font-mono text-slate-400 block">Document ID</span>
                  <span className="font-mono text-slate-700 truncate block">{successResult.doc_id}</span>
                </div>
                <div>
                  <span className="text-[10px] uppercase font-mono text-slate-400 block">Parameters</span>
                  <span className="font-semibold text-sky-700">{successResult.parameter_count || 0} extracted</span>
                </div>
                {successResult.pages && (
                  <div className="col-span-2 pt-1 border-t border-slate-100">
                    <span className="text-[10px] uppercase font-mono text-slate-400 block">Pages Analyzed</span>
                    <span className="text-slate-600">{successResult.pages} pages with structured Markdown</span>
                  </div>
                )}
              </div>

              <button
                onClick={handleViewDocument}
                className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-semibold text-xs tracking-wide transition shadow-xs"
              >
                <span>Open in Split-Screen Explorer</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          ) : (
            <>
              {/* Drag & Drop Zone */}
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition ${
                  isDragging
                    ? 'border-sky-500 bg-sky-50'
                    : selectedFile
                    ? 'border-sky-300 bg-sky-50/40'
                    : 'border-slate-200 hover:border-sky-300 bg-sky-50/20 hover:bg-sky-50/50'
                }`}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.json,.md"
                  onChange={handleFileInputChange}
                  className="hidden"
                />

                <div className="w-12 h-12 rounded-full bg-sky-100 text-sky-600 flex items-center justify-center mx-auto mb-3 shadow-2xs">
                  <UploadCloud className="w-6 h-6" />
                </div>

                <p className="text-xs font-semibold text-slate-800 mb-1">
                  Click to browse or drag & drop paper
                </p>
                <p className="text-[11px] text-slate-500 mb-3">
                  Supported formats: <strong>PDF</strong>, <strong>JSON</strong> (extracted dataset), or <strong>Markdown</strong>
                </p>

                <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded bg-white border border-slate-200 text-[10px] text-slate-600 font-mono shadow-2xs">
                  <span>.pdf</span>
                  <span>&bull;</span>
                  <span>.json</span>
                  <span>&bull;</span>
                  <span>.md</span>
                </div>
              </div>

              {/* Selected File Card */}
              {selectedFile && (
                <div className="p-3.5 rounded-xl bg-white border border-sky-200 shadow-2xs flex items-center justify-between">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-8 h-8 rounded-lg bg-sky-50 border border-sky-100 flex items-center justify-center text-sky-600 shrink-0">
                      <FileText className="w-4 h-4" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-xs font-bold text-slate-800 truncate">{selectedFile.name}</p>
                      <p className="text-[11px] text-slate-500 font-mono">{formatFileSize(selectedFile.size)}</p>
                    </div>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedFile(null);
                    }}
                    className="p-1 rounded text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              )}

              {/* Processing Options */}
              <div className="p-3.5 rounded-xl bg-sky-50/50 border border-sky-100 space-y-2.5">
                <span className="text-[10px] uppercase font-bold tracking-wider text-slate-500 block">
                  Automated Audit Options
                </span>
                
                <label className="flex items-start gap-2.5 cursor-pointer text-xs text-slate-700">
                  <input
                    type="checkbox"
                    checked={runTan}
                    onChange={(e) => setRunTan(e.target.checked)}
                    className="mt-0.5 rounded border-slate-300 text-sky-600 focus:ring-sky-500 cursor-pointer"
                  />
                  <div>
                    <span className="font-medium text-slate-900 block">Run Tan (2021) Regulatory Checklist</span>
                    <span className="text-[11px] text-slate-500 block">
                      Automatically evaluate all 36 WHO/OECD criteria with auditable quote anchoring.
                    </span>
                  </div>
                </label>
              </div>

              {/* Upload Status / Progress */}
              {isUploading && (
                <div className="p-3.5 rounded-xl bg-sky-50 border border-sky-200 text-xs text-sky-800 flex items-center gap-3">
                  <Loader2 className="w-4 h-4 animate-spin text-sky-600 shrink-0" />
                  <span className="font-medium">{uploadProgressText}</span>
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex items-center justify-end gap-2.5 pt-2 border-t border-sky-100">
                <button
                  type="button"
                  onClick={handleClose}
                  disabled={isUploading}
                  className="px-4 py-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-medium transition disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleUpload}
                  disabled={!selectedFile || isUploading}
                  className="flex items-center gap-2 px-5 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold shadow-xs transition disabled:opacity-50"
                >
                  {isUploading ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>Processing...</span>
                    </>
                  ) : (
                    <>
                      <UploadCloud className="w-3.5 h-3.5" />
                      <span>Start Upload & Audit</span>
                    </>
                  )}
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

