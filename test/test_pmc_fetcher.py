"""
test/test_pmc_fetcher.py — End-to-end test: PDF → paper resolution → XML parsing → LLM-ready chunks.

Shows the complete extraction pipeline JUST BEFORE anything is sent to the LLM,
including which narrative sections were filtered out by the PK relevance scorer.

Usage examples:
    python test/test_pmc_fetcher.py --pdf "pk_pipeline/test_data/Loccisano 2013.pdf"
    python test/test_pmc_fetcher.py --doi 10.1289/ehp.0900940
    python test/test_pmc_fetcher.py --pmcid PMC3502013
    python test/test_pmc_fetcher.py --no-filter   # disable narrative filtering
"""

import os
import sys
import json
import shutil
import argparse
import textwrap

# Add the project root to sys.path so we can import pk_pipeline as a package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pk_pipeline.ingestion.pmc_fetcher import (
    resolve_paper,
    extract_doi_from_pdf,
    extract_title_from_pdf,
)
from pk_pipeline.ingestion.xml_parser import parse_jats_xml

# ── Terminal formatting helpers ────────────────────────────────────────────────

RESET  = "\033[0m"
BOLD   = "\033[1m"
CYAN   = "\033[96m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
DIM    = "\033[2m"

ROLE_COLORS = {
    "table_xml":     "\033[94m",   # blue
    "equation_xml":  "\033[95m",   # magenta
    "narrative_xml": "\033[90m",   # grey
    "figure_xml":    "\033[93m",   # yellow
}

ROLE_LABELS = {
    "table_xml":     "📊 TABLE",
    "equation_xml":  "∑  EQUATION",
    "narrative_xml": "📄 NARRATIVE SECTION",
    "figure_xml":    "🖼️ FIGURE",
}

def hr(char="─", n=70):
    print(char * n)


def section(title: str):
    print()
    hr("═")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    hr("═")


def print_chunk(idx: int, chunk: dict, preview_chars: int = 600):
    role  = chunk["role"]
    text  = chunk["content"]
    color = ROLE_COLORS.get(role, "")
    label = ROLE_LABELS.get(role, role.upper())

    hr()
    # For figures, show whether it will go to visual or text path
    dispatch_tag = ""
    if role == "figure_xml":
        if chunk.get("is_diagram"):
            dispatch_tag = f"  {GREEN}[→ VLM visual]{RESET}" if chunk.get("image_path") else f"  {YELLOW}[diagram, no image]{RESET}"
        else:
            dispatch_tag = f"  {DIM}[→ caption text]{RESET}"

    print(f"{color}{BOLD}  Chunk {idx:02d} — {label}{RESET}  "
          f"{DIM}({len(text):,} chars){RESET}{dispatch_tag}")
    hr()

    # Print preview, wrapped nicely
    preview = text[:preview_chars]
    if len(text) > preview_chars:
        preview += f"\n  {DIM}... [+{len(text) - preview_chars:,} chars truncated]{RESET}"

    for line in preview.splitlines():
        print(f"  {line}")
    print()


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description="Test full extraction pipeline up to (but not including) LLM dispatch",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("--pdf",   type=str, help="Path to a local PDF file")
    ap.add_argument("--pmcid", type=str, help="PMC ID (e.g. PMC3502013)")
    ap.add_argument("--doi",   type=str, help="DOI (e.g. 10.1289/ehp.0900940)")
    ap.add_argument("--title", type=str, help="Paper title for search")
    ap.add_argument("--preview", type=int, default=600,
                    help="Max chars to display per chunk (default: 600)")
    ap.add_argument("--save-xml", action="store_true",
                    help="Copy the fetched XML into test/xml_output/")
    ap.add_argument("--no-filter", action="store_true",
                    help="Disable narrative section filtering — send ALL sections to LLM")
    args = ap.parse_args()

    # ── Step 1: Resolve identifiers from PDF (if --pdf given) ─────────────────
    doi   = args.doi
    title = args.title
    pmcid = args.pmcid

    if args.pdf:
        section(f"STEP 1 — Extracting identifiers from PDF: {os.path.basename(args.pdf)}")
        doi   = extract_doi_from_pdf(args.pdf) or doi
        title = extract_title_from_pdf(args.pdf, doi=doi) or title
        print(f"  {GREEN}DOI   :{RESET} {doi or '(not found)'}")
        print(f"  {GREEN}Title :{RESET} {title or '(not found)'}")
    elif not any([pmcid, doi, title]):
        print(f"{YELLOW}No arguments given — defaulting to PMC3502013 (Loccisano 2013){RESET}")
        pmcid = "PMC3502013"

    if pmcid: print(f"  {GREEN}PMCID :{RESET} {pmcid}")
    if doi:   print(f"  {GREEN}DOI   :{RESET} {doi}")
    if title: print(f"  {GREEN}Title :{RESET} {title[:80]}")

    # ── Step 2: Resolve paper (multi-source fetcher) ───────────────────────────
    section("STEP 2 — Resolving paper (fetcher chain)")
    result = resolve_paper(doi=doi, title=title, pmcid=pmcid, pdf_path=args.pdf)

    print(f"\n  {BOLD}Resolution result:{RESET}")
    for k, v in result.items():
        status = f"{GREEN}✅{RESET}" if v else f"{DIM}—{RESET}"
        print(f"  {status}  {k}: {v}")

    xml_path = result.get("xml_path")

    # Optionally copy XML to test/xml_output/
    if xml_path and args.save_xml:
        out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "xml_output")
        os.makedirs(out_dir, exist_ok=True)
        dest = os.path.join(out_dir, os.path.basename(xml_path))
        shutil.copy2(xml_path, dest)
        print(f"\n  {GREEN}✅ XML copied to: {dest}{RESET}")

    if not xml_path:
        print(f"\n  {RED}❌ No XML retrieved — paper is not in any OA XML source.{RESET}")
        if result.get("pdf_path"):
            print(f"  PDF fallback available: {result['pdf_path']}")
        print("\n  The pipeline would fall back to PDF-to-Image → ColQwen → VLM route.")
        return

    # ── Step 3: Parse JATS XML into chunks ────────────────────────────────────
    section("STEP 3 — Parsing JATS XML + PK Relevance Filtering")
    filter_narrative = not args.no_filter
    xml_data = parse_jats_xml(xml_path, filter_narrative=filter_narrative)

    metadata = xml_data.get("metadata", {})
    chunks   = xml_data.get("chunks", [])   # kept chunks only
    skipped  = xml_data.get("skipped", [])  # dropped sections

    print(f"  {BOLD}Article Metadata:{RESET}")
    print(f"    Title   : {metadata.get('title', '—')}")
    print(f"    Authors : {', '.join(metadata.get('authors', [])) or '—'}")
    print(f"    Journal : {metadata.get('journal', '—')}")
    print(f"    Year    : {metadata.get('year', '—')}")

    # Count chunk types
    by_role = {}
    for c in chunks:
        by_role[c["role"]] = by_role.get(c["role"], 0) + 1

    total_before = len(chunks) + len(skipped)
    print(f"\n  {BOLD}Chunk filtering:{RESET}  {total_before} parsed → {GREEN}{len(chunks)} kept{RESET} / {DIM}{len(skipped)} dropped{RESET}")
    for role, count in sorted(by_role.items()):
        color = ROLE_COLORS.get(role, "")
        label = ROLE_LABELS.get(role, role)
        print(f"    {color}{label}{RESET}: {count}")

    if skipped:
        print(f"\n  {DIM}Dropped sections (low PK relevance):{RESET}")
        for s in skipped:
            print(f"    {RED}✗{RESET}  [{s['title'] or '(untitled)'}]  {DIM}→ {s['skip_reason']}{RESET}")

    # ── Step 4: Print every chunk exactly as it would be sent to the LLM ──────
    filter_note = "(filtered)" if filter_narrative else "(⚠️  no filter — ALL sections)"
    section(f"STEP 4 — LLM dispatch preview  {filter_note}  {len(chunks)} chunks")
    print(f"  {DIM}Each chunk below represents one async call to extract_from_text().{RESET}")
    print(f"  {DIM}The full content (not just the preview) would be sent to the model.{RESET}")

    for idx, chunk in enumerate(chunks, 1):
        print_chunk(idx, chunk, preview_chars=args.preview)

    # ── Summary ───────────────────────────────────────────────────────────────
    section("SUMMARY")
    total_chars    = sum(len(c["content"]) for c in chunks)
    skipped_chars  = sum(len(c["content"]) for c in skipped)
    total_before   = len(chunks) + len(skipped)
    savings_pct    = int(100 * len(skipped) / total_before) if total_before else 0

    figure_chunks  = [c for c in chunks if c["role"] == "figure_xml"]
    diagram_figs   = [c for c in figure_chunks if c.get("is_diagram")]
    caption_figs   = [c for c in figure_chunks if not c.get("is_diagram")]
    text_only      = [c for c in chunks if c["role"] != "figure_xml"]

    print(f"  {GREEN}Source           :{RESET} {result.get('source', '—')} ({result.get('source_type', '—')})")
    print(f"  {GREEN}XML path         :{RESET} {xml_path}")
    print()
    print(f"  {BOLD}Before filter    :{RESET}  {total_before} chunks  ({(total_chars + skipped_chars):,} chars)")
    print(f"  {BOLD}After filter     :{RESET}  {GREEN}{len(chunks)} chunks{RESET}  ({total_chars:,} chars, ~{total_chars // 4:,} tokens)")
    print(f"  {BOLD}Dropped          :{RESET}  {RED}{len(skipped)} sections{RESET}  ({skipped_chars:,} chars saved  ↓{savings_pct}% reduction)")
    print()
    print(f"  {BOLD}LLM dispatch breakdown:{RESET}")
    print(f"  {GREEN}  ├─ Tables        :{RESET} {by_role.get('table_xml', 0)}  (text, always kept)")
    print(f"  {GREEN}  ├─ Equations     :{RESET} {by_role.get('equation_xml', 0)}  (text, always kept)")
    print(f"  {GREEN}  ├─ Sections      :{RESET} {by_role.get('narrative_xml', 0)}  (text, PK-relevant only)")
    print(f"  {YELLOW}  ├─ Fig diagrams  :{RESET} {len(diagram_figs)}  (visual → VLM image path)")
    print(f"  {DIM}  └─ Fig captions  :{RESET} {len(caption_figs)}  (text → caption only)")
    print()
    n_visual = len(diagram_figs)
    n_text   = len(chunks) - n_visual
    print(f"  {GREEN}Total LLM calls  :{RESET} {len(chunks)}  ({n_text} text + {n_visual} visual)")
    print(f"  {GREEN}  (Semaphore(2)   :{RESET} ~{len(chunks)//2 + len(chunks)%2} concurrent batches)")
    print()
    print(f"  {BOLD}Next step:{RESET} Pass text chunks to {CYAN}extract_from_text(){RESET}")
    print(f"           Pass diagram figures to {CYAN}extract_from_image(){RESET}")
    print(f"  {DIM}(Skipped in this test — no GPU/SGLang required){RESET}")
    hr("═")


if __name__ == "__main__":
    main()
