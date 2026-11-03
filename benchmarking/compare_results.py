"""
compare_results.py
CLI tool to inspect and compare detailed extraction diffs between
output/ predictions and pk_pipeline/pbpk_data/ ground truth references.

Usage:
  python benchmarking/compare_results.py --paper dean_2025_pfas
  python benchmarking/compare_results.py --all
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List
from benchmarking.benchmark_extractors import (
    normalize_param_list,
    values_match,
    units_match,
    evaluate_extraction_against_ground_truth
)


def load_manifest(base_dir: Path) -> List[Dict[str, Any]]:
    m_path = base_dir / "pk_pipeline" / "pbpk_data" / "manifest.json"
    if not m_path.exists():
        raise FileNotFoundError(f"Manifest not found at {m_path}")
    return json.loads(m_path.read_text(encoding="utf-8")).get("papers", [])


def compare_single_paper(paper_meta: Dict[str, Any], base_dir: Path, verbose: bool = True):
    pbpk_data_dir = base_dir / "pk_pipeline" / "pbpk_data"
    output_dir = base_dir / "output"

    paper_id = paper_meta["paper_id"]
    title = paper_meta["title"]
    pdf_name = paper_meta["pdf_path"]
    ref_name = paper_meta["reference_path"]

    ref_file = pbpk_data_dir / ref_name
    stem = Path(pdf_name).stem
    candidates = list(output_dir.glob(f"{stem}*.json"))

    if not ref_file.exists():
        print(f"Error: Ground truth {ref_name} not found.")
        return
    if not candidates:
        print(f"Error: No prediction file found in output/ for stem '{stem}'.")
        return

    exact = output_dir / f"{stem}.json"
    pred_file = exact if exact.exists() else sorted(candidates)[-1]

    gt_data = json.loads(ref_file.read_text(encoding="utf-8"))
    pred_data = json.loads(pred_file.read_text(encoding="utf-8"))

    gts = normalize_param_list(gt_data)
    preds = normalize_param_list(pred_data)

    scores = evaluate_extraction_against_ground_truth(
        pred_doc=pred_data,
        gt_doc=gt_data,
        method_name="ApexV2",
        paper_id=paper_id,
        paper_title=title
    )

    print("\n" + "=" * 80)
    print(f"PAPER: {paper_id} ({pdf_name})")
    print(f"TITLE: {title}")
    print(f"PREDICTION SOURCE: {pred_file.name}")
    print("=" * 80)
    print(f"Ground Truth Parameters: {len(gts)}")
    print(f"Extracted Parameters:    {len(preds)}")
    print(f"Strict True Positives:   {scores.strict_tp}")
    print(f"Partial True Positives:  {scores.partial_tp}")
    print(f"Strict Precision:        {scores.strict_precision}%")
    print(f"Strict Recall:           {scores.strict_recall}%")
    print(f"Strict F1 Score:         {scores.strict_f1}%")
    print(f"Partial F1 Score:        {scores.partial_f1}%")
    print(f"Value Accuracy:          {scores.value_accuracy}%")
    print(f"Compartment Recall:      {scores.topology_compartment_recall}%")
    print(f"Connection Recall:       {scores.topology_connection_recall}%")

    if not verbose:
        return

    # Detailed Match Breakdown
    matched_gt = set()
    matched_pred = set()

    for p_idx, p in enumerate(preds):
        for g_idx, g in enumerate(gts):
            if g_idx in matched_gt:
                continue
            sym_ok = (p.symbol and g.symbol and p.symbol == g.symbol) or (
                p.name and g.name and (p.name in g.name or g.name in p.name)
            )
            if sym_ok and values_match(p.value, g.value) and (p.species == g.species or not g.species) and (p.compound == g.compound or not g.compound):
                matched_gt.add(g_idx)
                matched_pred.add(p_idx)
                break

    unmatched_gts = [g for idx, g in enumerate(gts) if idx not in matched_gt]
    unmatched_preds = [p for idx, p in enumerate(preds) if idx not in matched_pred]

    if unmatched_gts:
        print(f"\n[-] MISSED GROUND-TRUTH PARAMETERS ({len(unmatched_gts)} items):")
        for g in unmatched_gts[:15]:
            inherited_tag = " [INHERITED]" if g.is_inherited else ""
            print(f"    - {g.compound:<6} | {g.species:<18} | {g.symbol:<10} | {g.name:<32} | Val: {g.value} {g.unit}{inherited_tag}")
        if len(unmatched_gts) > 15:
            print(f"    ... and {len(unmatched_gts) - 15} more.")

    if unmatched_preds:
        print(f"\n[+] EXTRA / CANDIDATE EXTRACTED PARAMETERS ({len(unmatched_preds)} items):")
        for p in unmatched_preds[:15]:
            print(f"    + {p.compound:<6} | {p.species:<18} | {p.symbol:<10} | {p.name:<32} | Val: {p.value} {p.unit} ({p.source_table})")
        if len(unmatched_preds) > 15:
            print(f"    ... and {len(unmatched_preds) - 15} more.")


def main():
    parser = argparse.ArgumentParser(description="PBPK Extraction Results Comparison Tool")
    parser.add_argument("--paper", type=str, help="Specific paper ID (e.g., dean_2025_pfas, loccisano_2013_pfoa_pfos)")
    parser.add_argument("--all", action="store_true", help="Compare all papers in manifest")
    parser.add_argument("--quiet", action="store_true", help="Summary metrics only, no parameter-level diffs")
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent.parent
    papers = load_manifest(base_dir)

    if args.paper:
        matched = [p for p in papers if p["paper_id"] == args.paper]
        if not matched:
            print(f"Paper '{args.paper}' not found. Available: {[p['paper_id'] for p in papers]}")
            sys.exit(1)
        compare_single_paper(matched[0], base_dir, verbose=not args.quiet)
    else:
        for p in papers:
            compare_single_paper(p, base_dir, verbose=not args.quiet)


if __name__ == "__main__":
    main()
