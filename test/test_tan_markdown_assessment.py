"""Test case: Convert scientific paper PDF to Markdown, then ask all Tan et al. questions to LLM.

This test validates the end-to-end PBPK assessment workflow:
  1. PDF Document -> Markdown conversion (preserving page markers, headings, tables, LaTeX math, footnotes).
  2. Section-aware Markdown routing (filtering Introduction background & References while preserving Results/Sensitivity).
  3. Construction of the Tan PBPK reporting questionnaire prompt across all 36 items.
  4. Querying the LLM with the Markdown paper to answer each Tan questionnaire item.
  5. Post-processing normalization, auditable evidence verification, and deterministic confidence scoring.
  6. Export of structured JSON and human-readable Markdown assessment reports.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path

import pytest

from pk_pipeline.schemas import ResponseOption, TanPBPKAssessment
from pk_pipeline.tan_assessor import (
    TAN_QUESTIONNAIRE_ITEMS,
    TAN_SECTIONS,
    assess_tan_from_markdown,
    build_tan_markdown_assessment_prompt,
    convert_pdf_to_markdown,
    evaluate_tan_from_markdown,
    extract_relevant_markdown_for_items,
    normalize_tan_assessment,
)

DEAN_PDF = "pk_pipeline/test_data/Dean et al. 2025 3 compartment (PFOA, PFOS, PFHxS).pdf"
KARRER_PDF = "pk_pipeline/test_data/Karrer et al.pdf"
OUTPUT_DIR = "output/tan_markdown_assessment"


def ensure_output_dir() -> Path:
    out = Path(OUTPUT_DIR)
    out.mkdir(parents=True, exist_ok=True)
    return out


# ─── 1. PDF TO MARKDOWN CONVERSION TESTS ───────────────────────────────────────

def test_convert_dean_pdf_to_markdown():
    """Verify that a PBPK PDF paper is converted to a clean, page-indexed Markdown file."""
    assert os.path.exists(DEAN_PDF), f"Test PDF file missing: {DEAN_PDF}"

    out_dir = ensure_output_dir()
    md_path = out_dir / "dean_2025_converted.md"

    md_text = convert_pdf_to_markdown(DEAN_PDF, output_md_path=str(md_path))

    assert md_path.exists(), "Markdown output file was not created on disk."
    assert len(md_text) > 10000, f"Markdown text too short ({len(md_text)} chars)."

    # Verify explicit page markers were injected for citation provenance
    assert "<!-- PAGE 1 -->" in md_text and "### [Page 1]" in md_text

    # Verify key PBPK markers from Dean et al.
    assert "Adapting existing toxicokinetic models" in md_text or "Dean" in md_text
    assert "PFOA" in md_text or "PFOS" in md_text or "PFHxS" in md_text
    assert "|" in md_text or "table" in md_text.lower()


def test_convert_karrer_pdf_to_markdown():
    """Verify conversion for Karrer et al. multi-compartment PBPK paper."""
    assert os.path.exists(KARRER_PDF), f"Test PDF file missing: {KARRER_PDF}"

    out_dir = ensure_output_dir()
    md_path = out_dir / "karrer_converted.md"

    md_text = convert_pdf_to_markdown(KARRER_PDF, output_md_path=str(md_path))

    assert md_path.exists()
    assert len(md_text) > 20000
    assert "<!-- PAGE 1 -->" in md_text
    assert "Karrer" in md_text or "biphenyl" in md_text.lower() or "pcb" in md_text.lower()


# ─── 2. SECTION-AWARE MARKDOWN ROUTING & PROMPT CONSTRUCTION TESTS ─────────────

def test_section_aware_markdown_routing_preserves_tail_sections():
    """Verify that evaluation/sensitivity batches receive Results & Sensitivity even in a 50k-char paper."""
    filler_intro = "Generic toxicology history prose. " * 900  # ~30,000 chars of background
    sample_md = (
        "# PBPK Model of Compound X\n\n"
        "## Abstract\nWe built a PBPK model for Compound X.\n\n"
        f"## Introduction\n{filler_intro}\n\n"
        "The objective of this study was to predict internal dose metrics in humans.\n\n"
        "## Materials and Methods\nWe used mrgsolve v1.0 with lsoda solver.\n\n"
        "## Results and Model Evaluation\nPredictions matched independent validation data within 2-fold error (AAFE = 1.28).\n\n"
        "## Sensitivity Analysis\nLocal sensitivity analysis perturbed parameters by 1% and identified hepatic clearance as sensitive.\n\n"
        "## References\n1. Author A (2020) Generic reference."
    )

    by_id = {item["item_id"]: item for item in TAN_QUESTIONNAIRE_ITEMS}
    eval_items = [by_id[iid] for iid in TAN_SECTIONS["evaluation_and_sensitivity"]]

    routed = extract_relevant_markdown_for_items(sample_md, items=eval_items, max_chars=15000)

    assert "AAFE = 1.28" in routed, "Evaluation metrics at the end of the paper were lost!"
    assert "perturbed parameters by 1%" in routed, "Sensitivity analysis section was lost!"
    assert "Author A (2020) Generic reference" not in routed, "References section should be stripped!"
    assert "General Introduction background excluded" in routed, "Generic Introduction prose should be filtered!"


def test_tan_markdown_prompt_construction():
    """Ensure that the generated prompt uses exact schema field names (`details`, `structured_details`)."""
    sample_md = "<!-- PAGE 1 -->\n### [Page 1]\n# Test PBPK Study\n\n## Methods\nWe modeled PFOA using a 3-compartment model."
    prompt = build_tan_markdown_assessment_prompt(
        sample_md,
        paper_title="Test PBPK Study",
        include_no_think=True,
    )

    for item in TAN_QUESTIONNAIRE_ITEMS:
        assert item["item_id"] in prompt, f"Missing item_id {item['item_id']} in prompt."

    # Verify `/no_think` is placed inside `<|im_start|>system` rather than before it
    assert prompt.startswith("<|im_start|>system\n/no_think\n")
    assert 'NEVER use `"rationale"` in place of `"details"`' in prompt
    assert '"structured_details"' in prompt
    assert "Test PBPK Study" in prompt


# ─── 3. DETERMINISTIC BASELINE & NORMALIZATION TESTS ──────────────────────────

def test_deterministic_markdown_baseline_evaluation():
    """Test deterministic rule-based evaluation of Markdown without requiring an LLM."""
    sample_md = """<!-- PAGE 1 -->
### [Page 1]
# Adapting existing toxicokinetic models for PFOA and PFOS in humans
https://doi.org/10.1093/toxsci/kfaf087
_Toxicological Sciences_, 2025

## Abstract
We adapted a 3-compartment PBPK/TK model to evaluate internal dose metrics for PFOA, PFOS, and PFHxS.

## Methods
Oral absorption rate ka was 0.5 h^-1. Protein binding to albumin was modeled with free fraction fu.
Urinary excretion was described by renal clearance and saturable reabsorption.
All differential equations were simulated in R package mrgsolve using the Radau ODE solver.

| Parameter | Symbol | Value | Unit |
|---|---|---|---|
| Renal clearance | CLr | 0.001 | L/h/kg |
| Free fraction | fu | 0.02 | dimensionless |

## Results & Evaluation
Model predictions were compared to human biomonitoring data with AAFE = 1.35 and RMSE = 0.12.
Local parameter sensitivity analysis was conducted.
"""
    assessment = evaluate_tan_from_markdown(sample_md, paper_title="Adapting existing TK models")

    assert isinstance(assessment, TanPBPKAssessment)
    assert len(assessment.items) == len(TAN_QUESTIONNAIRE_ITEMS)

    tan_1_1 = next(it for it in assessment.items if it.item_id == "TAN_1.1")
    assert tan_1_1.response == ResponseOption.PARTIALLY
    assert "Adapting existing" in str(tan_1_1.evidence[0].source_quote)
    assert tan_1_1.confidence == "high"

    tan_2_4_7 = next(it for it in assessment.items if it.item_id == "TAN_2.4.7")
    assert tan_2_4_7.response == ResponseOption.PARTIALLY
    assert "mrgsolve" in tan_2_4_7.details.lower()


def test_normalize_tan_assessment_handles_rationale_alias():
    """Ensure normalize_tan_assessment gracefully maps `rationale` -> `details` if emitted by an LLM."""
    raw_llm_payload = {
        "items": [
            {
                "item_id": "TAN_1.1",
                "response": "yes",
                "rationale": "Modeled PFOA and PFOS in a 3-compartment TK model.",
                "structured_details": {"model_name": "3-compartment TK model", "target_compounds": ["PFOA", "PFOS"]},
                "evidence": [
                    {
                        "source_page": 1,
                        "source_section": "Abstract",
                        "source_location": "Page 1, Abstract",
                        "source_quote": "We adapted a 3-compartment TK model for PFOA and PFOS.",
                    }
                ],
            }
        ]
    }
    normalized = normalize_tan_assessment(raw_llm_payload)
    tan_1_1 = next(it for it in normalized.items if it.item_id == "TAN_1.1")
    assert tan_1_1.response == ResponseOption.YES
    assert tan_1_1.details == "Modeled PFOA and PFOS in a 3-compartment TK model."
    assert tan_1_1.confidence == "high"


# ─── 4. LIVE LLM ASSESSMENT TEST ──────────────────────────────────────────────

def test_llm_answers_tan_questions_from_markdown():
    """End-to-end test: Convert paper to Markdown and ask all Tan questions to the LLM."""
    asyncio.run(_async_test_llm_answers_tan_questions_from_markdown())


async def _async_test_llm_answers_tan_questions_from_markdown():
    out_dir = ensure_output_dir()
    md_path = out_dir / "dean_2025_converted.md"

    if not md_path.exists():
        convert_pdf_to_markdown(DEAN_PDF, output_md_path=str(md_path))

    with open(md_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    try:
        from pk_pipeline.ml_services import SGLangExtractor
        ext = SGLangExtractor()
        server_ready = getattr(ext, "is_loaded", False)
    except Exception:
        server_ready = False

    if not server_ready:
        pytest.skip("LLM server not currently reachable. Running deterministic baseline verification.")

    assessment = await assess_tan_from_markdown(
        markdown_text=md_text,
        extractor=ext,
        paper_title="Adapting existing toxicokinetic models to relate PFAS intake to biomarkers in humans",
        mode="sections",
        max_new_tokens=8000,
    )

    assert isinstance(assessment, TanPBPKAssessment)
    assert len(assessment.items) == 36, f"Expected 36 Tan items, got {len(assessment.items)}"

    json_path = out_dir / "dean_2025_tan_assessment.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(assessment.model_dump(), f, indent=2)

    report_path = out_dir / "dean_2025_tan_report.md"
    _generate_markdown_report(assessment, report_path)

    assert json_path.exists()
    assert report_path.exists()

    positive_items = [
        it for it in assessment.items
        if it.response in (ResponseOption.YES, ResponseOption.PARTIALLY) and it.item_id != "TAN_1.3"
    ]
    assert len(positive_items) >= 5, "Expected at least 5 positive Tan ratings from Dean et al. markdown."

    for item in positive_items:
        assert len(item.evidence) > 0, f"Item {item.item_id} had rating {item.response} but empty evidence."
        assert item.confidence in ("high", "medium", "low")


def _generate_markdown_report(assessment: TanPBPKAssessment, out_path: Path):
    """Generate a clean, readable Markdown table report of the Tan assessment."""
    lines = [
        "# Tan et al. PBPK Reporting Assessment Report",
        f"**Template**: {assessment.template_name} ({assessment.template_version})  ",
        f"**Model Scope**: {assessment.assessment_scope}  ",
        f"**Fit-for-purpose Summary**: {assessment.overall_fit_for_purpose}  \n",
        "## Summary of Questionnaire Items\n",
        "| Item ID | Section | Response | Confidence | Details & Verbatim Evidence |",
        "|---|---|:---:|:---:|---|",
    ]

    for item in assessment.items:
        quote = item.evidence[0].source_quote if item.evidence and item.evidence[0].source_quote else "N/A"
        loc = item.evidence[0].source_location if item.evidence and item.evidence[0].source_location else ""
        page = f"p.{item.evidence[0].source_page}" if item.evidence and item.evidence[0].source_page else ""
        loc_full = ", ".join(p for p in (page, loc) if p)
        ev_str = f"*{quote[:90]}...* ({loc_full})" if quote != "N/A" else "None"
        resp_badge = f"**{item.response.value.upper()}**"
        lines.append(f"| `{item.item_id}` | {item.section} | {resp_badge} | {item.confidence} | {item.details} <br/>*Evidence*: {ev_str} |")

    lines.append("\n## Key Gaps Identified\n")
    for gap in assessment.key_gaps[:10]:
        lines.append(f"- {gap}")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


# ─── 5. CLI RUNNER ─────────────────────────────────────────────────────────────

def run_cli():
    parser = argparse.ArgumentParser(description="Convert paper PDF to Markdown and run Tan Questionnaire via LLM.")
    parser.add_argument("--paper", choices=["dean", "karrer"], default="dean", help="Preset test paper to assess.")
    parser.add_argument("--pdf", type=str, default=None, help="Custom PDF file path.")
    parser.add_argument("--title", type=str, default=None, help="Paper title override.")
    parser.add_argument("--mode", choices=["single", "sections"], default="sections", help="LLM evaluation mode.")
    parser.add_argument("--dry-run", action="store_true", help="Run deterministic markdown evaluation without LLM.")
    args = parser.parse_args()

    pdf_file = args.pdf or (DEAN_PDF if args.paper == "dean" else KARRER_PDF)
    title = args.title or ("Adapting existing TK models for PFAS" if args.paper == "dean" else "Karrer et al. PCB-153 PBPK model")

    print(f"\n{'='*70}")
    print("Tan et al. PBPK Markdown Assessment Runner")
    print(f"{'='*70}")
    print(f"Target PDF : {pdf_file}")
    print(f"Title      : {title}")
    print(f"Mode       : {args.mode} (Dry run: {args.dry_run})\n")

    out_dir = ensure_output_dir()
    stem = Path(pdf_file).stem
    md_path = out_dir / f"{stem}.md"

    print(f"[Step 1/3] Converting PDF to Markdown -> {md_path}...")
    md_text = convert_pdf_to_markdown(pdf_file, output_md_path=str(md_path))
    print(f"           Done! Converted {len(md_text):,} characters of Markdown.\n")

    print("[Step 2/3] Answering all 36 Tan questions...")
    if args.dry_run:
        print("           (Running deterministic baseline from Markdown...)")
        assessment = evaluate_tan_from_markdown(md_text, paper_title=title)
    else:
        print(f"           (Querying LLM via SGLangExtractor in mode='{args.mode}'...)")
        assessment = asyncio.run(
            assess_tan_from_markdown(
                markdown_text=md_text,
                paper_title=title,
                mode=args.mode,
            )
        )

    json_path = out_dir / f"{stem}_tan_assessment.json"
    report_path = out_dir / f"{stem}_tan_report.md"
    print("\n[Step 3/3] Saving assessment results...")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(assessment.model_dump(), f, indent=2)
    _generate_markdown_report(assessment, report_path)
    print(f"           JSON saved   : {json_path}")
    print(f"           Report saved : {report_path}\n")

    print(f"{'='*70}")
    print(f"RESULTS SUMMARY ({assessment.overall_fit_for_purpose})")
    print(f"{'='*70}")
    yes_cnt = sum(it.response == ResponseOption.YES for it in assessment.items)
    part_cnt = sum(it.response == ResponseOption.PARTIALLY for it in assessment.items)
    no_cnt = sum(it.response == ResponseOption.NO for it in assessment.items)
    cannot_cnt = sum(it.response == ResponseOption.I_CANNOT_ANSWER for it in assessment.items)
    na_cnt = sum(it.response == ResponseOption.NOT_APPLICABLE for it in assessment.items)

    print(f"  YES             : {yes_cnt}")
    print(f"  PARTIALLY       : {part_cnt}")
    print(f"  NO              : {no_cnt}")
    print(f"  I CANNOT ANSWER : {cannot_cnt}")
    print(f"  NOT APPLICABLE  : {na_cnt}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    run_cli()