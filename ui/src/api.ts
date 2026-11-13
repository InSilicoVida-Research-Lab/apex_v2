import { DocumentSummary, ExtractedDocument, VerificationReport, TanPBPKAssessment } from './types';

const API_BASE = '/api';

export async function fetchDocuments(): Promise<DocumentSummary[]> {
  const res = await fetch(`${API_BASE}/documents`);
  if (!res.ok) throw new Error('Failed to fetch documents');
  const data = await res.json();
  return data.documents || [];
}

export async function fetchDocument(docId: string): Promise<ExtractedDocument> {
  const res = await fetch(`${API_BASE}/documents/${encodeURIComponent(docId)}`);
  if (!res.ok) throw new Error(`Failed to fetch document ${docId}`);
  return res.json();
}

export async function fetchMarkdown(docId: string): Promise<{ markdown: string; available: boolean }> {
  const res = await fetch(`${API_BASE}/documents/${encodeURIComponent(docId)}/markdown`);
  if (!res.ok) return { markdown: '', available: false };
  return res.json();
}

export function getPdfUrl(docId: string): string {
  return `${API_BASE}/documents/${encodeURIComponent(docId)}/pdf`;
}

export async function fetchPdfInfo(docId: string): Promise<{ available: boolean; page_count: number; filename?: string }> {
  try {
    const res = await fetch(`${API_BASE}/documents/${encodeURIComponent(docId)}/pdf/info`);
    if (!res.ok) return { available: false, page_count: 0 };
    return res.json();
  } catch {
    return { available: false, page_count: 0 };
  }
}

export function getPageImageUrl(docId: string, pageNum: number, dpi: number = 150): string {
  return `${API_BASE}/documents/${encodeURIComponent(docId)}/pages/${pageNum}?dpi=${dpi}`;
}

export async function fetchVerification(docId: string): Promise<VerificationReport> {
  const res = await fetch(`${API_BASE}/documents/${encodeURIComponent(docId)}/verification`);
  if (!res.ok) throw new Error(`Failed to run verification on ${docId}`);
  return res.json();
}

export async function fetchTanAssessment(docId: string): Promise<TanPBPKAssessment> {
  const res = await fetch(`${API_BASE}/documents/${encodeURIComponent(docId)}/tan`);
  if (!res.ok) throw new Error(`Failed to fetch Tan assessment for ${docId}`);
  return res.json();
}

export async function updateParameter(
  docId: string,
  paramId: string,
  updates: {
    value?: number | null;
    value_text?: string;
    unit?: string;
    parameter_name?: string;
    compound?: string;
    species?: string;
    status?: string;
    notes?: string;
  }
): Promise<any> {
  const res = await fetch(
    `${API_BASE}/documents/${encodeURIComponent(docId)}/parameters/${encodeURIComponent(paramId)}`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates),
    }
  );
  if (!res.ok) throw new Error('Failed to update parameter');
  return res.json();
}

export interface UploadResponse {
  status: string;
  doc_id: string;
  title: string;
  filename: string;
  pages?: number;
  parameter_count?: number;
  has_pdf?: boolean;
  has_markdown?: boolean;
  message: string;
}

export async function uploadDocument(file: File, runTan: boolean = true): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('run_tan', String(runTan));

  const res = await fetch(`${API_BASE}/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    let errorMsg = 'Failed to upload document';
    try {
      const err = await res.json();
      if (err.detail) errorMsg = err.detail;
    } catch {
      // fallback
    }
    throw new Error(errorMsg);
  }

  return res.json();
}
