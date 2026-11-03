#!/usr/bin/env python3
"""
test/test_docling.py
====================
Test script and runner for IBM Docling (https://docling.ai/).
Docling is an advanced document parsing framework that extracts clean Markdown,
structured HTML tables (via TableFormer), and layout elements from complex PDFs.

Reference:
    https://docling.ai/
    https://github.com/DS4SD/docling

Usage:
    # Run test on default sample PDF (Page 4 of Dean et al. 2025)
    python test/test_docling.py

    # Run on a specific PDF and page
    python test/test_docling.py --pdf "pk_pipeline/test_data/Dean et al. 2025 3 compartment (PFOA, PFOS, PFHxS).pdf" --page 4

    # Run on an entire PDF
    python test/test_docling.py --pdf "pk_pipeline/test_data/s12249-023-02680-y.pdf" --output "test/s12249_docling.md"
"""

import os
import sys
import time
import argparse
import tempfile
from pathlib import Path

# Ensure repository root is on PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DEFAULT_PDF = "pk_pipeline/test_data/Dean et al. 2025 3 compartment (PFOA, PFOS, PFHxS).pdf"
DEFAULT_PAGE = 4
DEFAULT_OUTPUT = "test/dean_page4_docling.md"


def run_docling_conversion(
    pdf_path: str,
    page_number: int = None,
    do_ocr: bool = True,
    do_table_structure: bool = True,
    do_formula_enrichment: bool = True
) -> str:
    """
    Run Docling DocumentConverter on a PDF file (optionally sliced to a specific 1-indexed page).
    Returns the converted Markdown string with structured tables.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found at: {pdf_path}")

    try:
        import pymupdf
    except ImportError:
        import fitz as pymupdf

    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions

    temp_pdf_to_clean = None
    target_path = pdf_path

    # If a specific page is requested, extract just that page to a temp PDF
    if page_number is not None:
        doc = pymupdf.open(pdf_path)
        if page_number < 1 or page_number > len(doc):
            raise IndexError(f"Page number {page_number} is out of bounds (document has {len(doc)} pages).")

        print(f"Extracting Page {page_number}/{len(doc)} to temporary PDF for focused conversion...")
        single_doc = pymupdf.open()
        single_doc.insert_pdf(doc, from_page=page_number - 1, to_page=page_number - 1)

        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        single_doc.save(tmp.name)
        tmp.close()
        target_path = tmp.name
        temp_pdf_to_clean = tmp.name

    try:
        print("[Docling] Configuring DocumentConverter pipeline options...")
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = do_ocr
        pipeline_options.do_table_structure = do_table_structure
        if hasattr(pipeline_options, "do_formula_enrichment"):
            pipeline_options.do_formula_enrichment = do_formula_enrichment

        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )

        print(f"[Docling] Converting document: {target_path} (OCR={do_ocr}, TableFormer={do_table_structure})...")
        t0 = time.time()
        conversion_result = converter.convert(target_path)
        elapsed = time.time() - t0
        print(f"[Docling] Conversion completed in {elapsed:.2f}s!")

        docling_doc = conversion_result.document
        markdown_text = docling_doc.export_to_markdown()

        # Extract and format any tables explicitly as HTML tables if available
        tables = getattr(docling_doc, "tables", [])
        print(f"[Docling] Extracted {len(tables)} structured table(s).")

        return markdown_text

    finally:
        if temp_pdf_to_clean and os.path.exists(temp_pdf_to_clean):
            try:
                os.unlink(temp_pdf_to_clean)
            except Exception:
                pass


def test_docling():
    """Unit test for Docling conversion."""
    pdf_path = DEFAULT_PDF
    if not os.path.exists(pdf_path):
        print(f"Skipping test_docling: test PDF not found at {pdf_path}")
        return

    md_output = run_docling_conversion(pdf_path, page_number=4, do_ocr=False)
    assert len(md_output) > 100
    assert "Table 1" in md_output or "PFOS" in md_output or "PFOA" in md_output
    print("test_docling passed successfully!")


def main():
    parser = argparse.ArgumentParser(description="Test and benchmark IBM Docling on PDF documents.")
    parser.add_argument("--pdf", type=str, default=DEFAULT_PDF, help="Path to PDF file")
    parser.add_argument("--page", type=int, default=DEFAULT_PAGE, help="Page number (1-indexed) to convert, or 0 for whole doc")
    parser.add_argument("--output", type=str, default=DEFAULT_OUTPUT, help="Output markdown file path")
    parser.add_argument("--no-ocr", dest="ocr", action="store_false", default=True, help="Disable OCR (faster for digital text PDFs)")
    parser.add_argument("--no-table", dest="table", action="store_false", default=True, help="Disable TableFormer structure recognition")

    args = parser.parse_args()
    page_to_run = args.page if args.page > 0 else None

    print(f"\n{'='*65}")
    print(f"  IBM Docling OCR & Table Structure Benchmark")
    print(f"{'='*65}")
    print(f"  • Input PDF:    {args.pdf}")
    print(f"  • Page:         {page_to_run if page_to_run else 'All Pages'}")
    print(f"  • OCR:          {args.ocr}")
    print(f"  • TableFormer:  {args.table}")
    print(f"  • Output file:  {args.output}")
    print(f"{'='*65}\n")

    t_start = time.time()
    try:
        md_text = run_docling_conversion(
            pdf_path=args.pdf,
            page_number=page_to_run,
            do_ocr=args.ocr,
            do_table_structure=args.table
        )

        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(md_text)

        total_time = time.time() - t_start
        print(f"\n{'='*65}")
        print(f"  Docling Output Preview (first 500 characters):")
        print(f"{'='*65}")
        print(md_text[:500] if md_text else "(No text extracted)")
        print(f"\n{'='*65}")
        print(f"  Total processing time: {total_time:.2f}s")
        print(f"  Full result saved to:  {out_path.resolve()}")
        print(f"{'='*65}\n")

    except Exception as e:
        print(f"\n[Docling Error] Execution failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
