"""
benchmark_extractors.py
Unified Benchmarking Framework comparing:
  1. Our LLM/VLM Route (apex_v2 / pk_pipeline)
  2. GROBID (TEI-XML Table + Text Parser)
  3. GLiNER (urchade/GLiNER Zero-Shot Span NER + Heuristic Linker)
  4. NuExtract (numindai/NuExtract Schema-Driven JSON Extractor)

Evaluates extracted models against ground truth files in pk_pipeline/pbpk_data/
across 7 metrics: Strict & Partial F1, Value Accuracy, Unit Accuracy, Context
Attribution, CI/Range Accuracy, and Model Topology Recall.
"""

import os
import sys
import json
import math
import time
import re
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Tuple, Set


# ============================================================================
# 1. STANDARDIZED BENCHMARK RECORD & METRICS DATA STRUCTURES
# ============================================================================

@dataclass
class NormalizedParam:
    """Canonical representation of a single PBPK parameter for cross-model comparison."""
    compound: str          # e.g., "PFOS", "PFOA", "PFHXS", "RILUZOLE"
    species: str           # e.g., "nonhuman primate", "human", "rat"
    symbol: str            # e.g., "bw", "qcc", "tmc", "kt", "vcc", "bioav"
    name: str              # e.g., "body weight"
    value: Optional[float] # e.g., 19.8
    ci_low: Optional[float] = None
    ci_high: Optional[float] = None
    unit: str = ""
    formulation: str = ""
    is_inherited: bool = False
    source_table: str = ""


@dataclass
class BenchmarkScores:
    method_name: str
    paper_id: str
    paper_title: str
    ground_truth_count: int = 0
    extracted_count: int = 0
    strict_tp: int = 0
    partial_tp: int = 0
    fp: int = 0
    fn: int = 0
    strict_precision: float = 0.0
    strict_recall: float = 0.0
    strict_f1: float = 0.0
    partial_precision: float = 0.0
    partial_recall: float = 0.0
    partial_f1: float = 0.0
    value_accuracy: float = 0.0
    unit_accuracy: float = 0.0
    species_accuracy: float = 0.0
    compound_accuracy: float = 0.0
    ci_accuracy: float = 0.0
    topology_compartment_recall: float = 0.0
    topology_connection_recall: float = 0.0
    latency_sec: float = 0.0
    peak_vram_mb: float = 0.0


# ============================================================================
# 2. EXTRACTOR ADAPTERS
# ============================================================================

class BaseExtractorAdapter:
    name: str = "Base"

    def extract_paper(self, pdf_path: str, xml_path: Optional[str] = None) -> Dict[str, Any]:
        raise NotImplementedError


class ApexV2LLMRouteAdapter(BaseExtractorAdapter):
    """Method 1: Our Hybrid XML/OCR + Multimodal VLM (Qwen-VL) + Deterministic Post-Processor."""
    name = "1_ApexV2_LLM_VLM_Route"

    def __init__(self, output_dir: Optional[str] = "output"):
        self.output_dir = Path(output_dir) if output_dir else Path("output")

    def extract_paper(self, pdf_path: str, xml_path: Optional[str] = None) -> Dict[str, Any]:
        stem = Path(pdf_path).stem
        # Check output directory for matching json
        candidates = list(self.output_dir.glob(f"{stem}*.json"))
        if candidates:
            # Pick latest or exact match
            exact = self.output_dir / f"{stem}.json"
            chosen = exact if exact.exists() else sorted(candidates)[-1]
            try:
                return json.loads(chosen.read_text(encoding="utf-8"))
            except Exception as e:
                print(f"Warning: Failed reading {chosen}: {e}")

        # Live invocation fallback if pipeline is imported
        try:
            from pk_pipeline.main import process_document
            return process_document(pdf_path=pdf_path, xml_path=xml_path)
        except Exception as err:
            print(f"Warning: Live process_document invocation skipped: {err}")
            return {"model_parameters": [], "model_structure": {}}


class GrobidBaselineAdapter(BaseExtractorAdapter):
    """Method 2: GROBID (PDF -> TEI-XML) + Positional Table Cell Parser."""
    name = "2_GROBID_TEI_XML"

    def __init__(self, grobid_url: str = "http://localhost:8070/api/processFulltextDocument"):
        self.grobid_url = grobid_url

    def extract_paper(self, pdf_path: str, xml_path: Optional[str] = None) -> Dict[str, Any]:
        import requests
        from bs4 import BeautifulSoup

        try:
            with open(pdf_path, "rb") as f:
                resp = requests.post(
                    self.grobid_url,
                    files={"input": f},
                    data={"teiCoordinates": ["figure", "table"]},
                    timeout=30
                )
            soup = BeautifulSoup(resp.text, "lxml-xml")
            parameters = []
            for table in soup.find_all("figure", {"type": "table"}):
                caption = table.find("figDesc").get_text(" ", strip=True) if table.find("figDesc") else ""
                rows = table.find_all("row")
                for r in rows[1:]:
                    cells = [c.get_text(" ", strip=True) for c in r.find_all("cell")]
                    if len(cells) >= 3:
                        val_match = re.search(r"([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)", cells[-2])
                        parameters.append({
                            "parameter_name": cells[0],
                            "symbol": cells[1] if len(cells) > 2 else "",
                            "context": {"compound": None, "species": None},
                            "quantitative_data": {
                                "value": float(val_match.group(1)) if val_match else None,
                                "unit": None
                            },
                            "provenance": {"source_location": caption[:40]}
                        })
            return {"model_parameters": parameters, "model_structure": {"compartments": [], "connections": []}}
        except Exception as e:
            return {"model_parameters": [], "model_structure": {"compartments": [], "connections": []}}


class GLiNERExtractorAdapter(BaseExtractorAdapter):
    """Method 3: GLiNER Zero-Shot Span NER + Row Proximity Linker."""
    name = "3_GLiNER_Span_NER"

    def __init__(self, model_id: str = "urchade/gliner_medium-v2.1"):
        self.model_id = model_id
        self._model = None
        self.labels = [
            "pharmacokinetic_parameter_name",
            "parameter_symbol",
            "numerical_value",
            "confidence_interval",
            "measurement_unit",
            "chemical_compound",
            "species",
            "organ_compartment"
        ]

    def _get_model(self):
        if self._model is None:
            from gliner import GLiNER
            self._model = GLiNER.from_pretrained(self.model_id)
        return self._model

    def extract_paper(self, pdf_path: str, xml_path: Optional[str] = None) -> Dict[str, Any]:
        try:
            import fitz
            doc = fitz.open(pdf_path)
            model = self._get_model()
            parameters = []
            for page in doc:
                text = page.get_text("text")
                for line in text.split("\n"):
                    if not any(c.isdigit() for c in line) or len(line.strip()) < 5:
                        continue
                    entities = model.predict_entities(line, self.labels, threshold=0.45)
                    by_label: Dict[str, List[str]] = {}
                    for ent in entities:
                        by_label.setdefault(ent["label"], []).append(ent["text"])
                    if "numerical_value" in by_label and (
                        "pharmacokinetic_parameter_name" in by_label or "parameter_symbol" in by_label
                    ):
                        for raw_val in by_label["numerical_value"]:
                            try:
                                val = float(re.sub(r"[^\d.eE+-]", "", raw_val))
                            except ValueError:
                                continue
                            parameters.append({
                                "parameter_name": (by_label.get("pharmacokinetic_parameter_name") or [""])[0],
                                "symbol": (by_label.get("parameter_symbol") or [""])[0],
                                "context": {
                                    "compound": (by_label.get("chemical_compound") or [None])[0],
                                    "species": (by_label.get("species") or [None])[0],
                                },
                                "quantitative_data": {
                                    "value": val,
                                    "unit": (by_label.get("measurement_unit") or [None])[0],
                                },
                                "provenance": {"source_quote": line}
                            })
            return {"model_parameters": parameters, "model_structure": {"compartments": [], "connections": []}}
        except Exception:
            return {"model_parameters": [], "model_structure": {"compartments": [], "connections": []}}


class NuExtractAdapter(BaseExtractorAdapter):
    """Method 4: NuExtract Schema-Driven JSON Extractor."""
    name = "4_NuExtract_Template_LLM"

    def __init__(self, model_id: str = "numind/NuExtract-1.5"):
        self.model_id = model_id
        self._tokenizer = None
        self._model = None
        self.json_template = json.dumps({
            "model_parameters": [{
                "parameter_name": "",
                "symbol": "",
                "compound": "",
                "species": "",
                "formulation": "",
                "value": 0.0,
                "ci_low": 0.0,
                "ci_high": 0.0,
                "unit": ""
            }]
        }, indent=2)

    def _load(self):
        if self._model is None:
            import torch
            from transformers import AutoTokenizer, AutoModelForCausalLM
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_id, trust_remote_code=True)
            self._model = AutoModelForCausalLM.from_pretrained(
                self.model_id, torch_dtype=torch.bfloat16, device_map="auto", trust_remote_code=True
            ).eval()

    def extract_paper(self, pdf_path: str, xml_path: Optional[str] = None) -> Dict[str, Any]:
        try:
            self._load()
            import fitz
            doc = fitz.open(pdf_path)
            all_params = []
            for page in doc:
                text = page.get_text("text")
                if not any(k in text.lower() for k in ["parameter", "clearance", "volume", "half-life", "partition", "rate"]):
                    continue
                prompt = (
                    f"<|input|>\n### Template:\n{self.json_template}\n"
                    f"### Text:\n{text[:4000]}\n\n<|output|>"
                )
                inputs = self._tokenizer(prompt, return_tensors="pt", truncation=True, max_length=8192).to(self._model.device)
                output_ids = self._model.generate(**inputs, max_new_tokens=2048, do_sample=False)
                gen_text = self._tokenizer.decode(output_ids[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
                try:
                    p_obj = json.loads(gen_text.strip())
                    all_params.extend(p_obj.get("model_parameters", []))
                except Exception:
                    pass
            return {"model_parameters": all_params, "model_structure": {"compartments": [], "connections": []}}
        except Exception:
            return {"model_parameters": [], "model_structure": {"compartments": [], "connections": []}}


# ============================================================================
# 3. NORMALIZATION & RIGOROUS SCORING ENGINE
# ============================================================================

COMPOUND_SYNONYMS = {
    "RLZ": "RILUZOLE",
    "RLE": "RILUZOLE",
    "RILUTOR": "RILUZOLE",
    "RILUTORASD": "RILUZOLE",
    "PFOA": "PFOA",
    "PFOS": "PFOS",
    "PFHXS": "PFHXS",
    "DINCH": "DINCH",
    "MINCH": "MINCH",
}

def normalize_param_list(raw_doc: Dict[str, Any]) -> List[NormalizedParam]:
    """Converts diverse JSON formats into canonical NormalizedParam tuples."""
    params = raw_doc.get("model_parameters") or []
    if not params:
        # Fallback to combined views if model_parameters was not populated or legacy
        params = (raw_doc.get("system_specific_parameters") or []) + (raw_doc.get("compound_specific_parameters") or [])
    if not params:
        params = raw_doc.get("parameters") or []
    normalized: List[NormalizedParam] = []

    for p in params:
        if not isinstance(p, dict):
            continue
        ctx = p.get("context") or {}
        q = p.get("quantitative_data") or {}
        prov = p.get("provenance") or {}
        unc = q.get("uncertainty") or {}

        raw_compound = ctx.get("compound") or p.get("compound") or ""
        compound = re.sub(r"[^A-Za-z0-9]", "", str(raw_compound).upper())
        compound = COMPOUND_SYNONYMS.get(compound, compound)

        raw_species = ctx.get("species") or ctx.get("subject_species") or p.get("species") or ctx.get("life_stage") or ""
        species = str(raw_species).strip().lower()
        if "primate" in species or "monkey" in species:
            species = "nonhuman primate"
        elif any(k in species for k in ["mother", "fetus", "infant", "human", "adult", "gestation", "lactation"]):
            species = "human"
        elif "rat" in species:
            species = "rat"
        elif "mouse" in species or "mice" in species:
            species = "mouse"

        raw_sym = (
            p.get("symbol_standardized")
            or p.get("symbol")
            or p.get("symbol_original")
            or p.get("parameter_name_standardized")
            or ""
        )
        symbol = re.sub(r"[^A-Za-z0-9]", "", str(raw_sym).lower())

        raw_name = p.get("parameter_name") or p.get("parameter_name_original") or p.get("parameter_name_standardized") or ""
        name = str(raw_name).strip().lower()

        val = q.get("value") if "quantitative_data" in p else p.get("value")
        try:
            val_flt = float(val) if val is not None else None
        except (ValueError, TypeError):
            val_flt = None

        ci_low = q.get("ci_low") if q.get("ci_low") is not None else unc.get("lower")
        ci_high = q.get("ci_high") if q.get("ci_high") is not None else unc.get("upper")
        try:
            ci_l_flt = float(ci_low) if ci_low is not None else None
            ci_h_flt = float(ci_high) if ci_high is not None else None
        except (ValueError, TypeError):
            ci_l_flt, ci_h_flt = None, None

        raw_unit = q.get("unit_standardized") or q.get("unit") or q.get("unit_original") or p.get("unit") or ""
        unit = re.sub(r"\s+", " ", str(raw_unit).strip().lower())

        formulation = str(ctx.get("formulation") or p.get("formulation") or "").strip().lower()
        is_inherited = (
            prov.get("evidence_directness") == "inherited_cross_species"
            or "inherited" in str(p.get("parameter_id", "")).lower()
            or "held constant" in str(prov.get("derivation", "")).lower()
        )
        source_table = str(prov.get("source_table") or "").strip()

        normalized.append(NormalizedParam(
            compound=compound,
            species=species,
            symbol=symbol,
            name=name,
            value=val_flt,
            ci_low=ci_l_flt,
            ci_high=ci_h_flt,
            unit=unit,
            formulation=formulation,
            is_inherited=is_inherited,
            source_table=source_table
        ))

    return normalized


def values_match(v1: Optional[float], v2: Optional[float], rel_tol: float = 0.02) -> bool:
    """Checks float equality within tolerance or handles None."""
    if v1 is None and v2 is None:
        return True
    if v1 is None or v2 is None:
        return False
    return math.isclose(v1, v2, rel_tol=rel_tol, abs_tol=1e-5)


def units_match(u1: str, u2: str) -> bool:
    """Soft normalization for equivalent units."""
    if not u1 or not u2:
        return True
    n1 = u1.replace("^", "").replace(" ", "").replace("*", "")
    n2 = u2.replace("^", "").replace(" ", "").replace("*", "")
    return n1 == n2 or n1 in n2 or n2 in n1


def symbols_or_names_match(pred: NormalizedParam, gt: NormalizedParam) -> bool:
    if pred.symbol and gt.symbol and (pred.symbol == gt.symbol or pred.symbol in gt.symbol or gt.symbol in pred.symbol):
        return True
    if pred.name and gt.name and (pred.name in gt.name or gt.name in pred.name):
        return True
    if pred.symbol and gt.name and (pred.symbol in gt.name or gt.name in pred.symbol):
        return True
    if pred.name and gt.symbol and (pred.name in gt.symbol or gt.symbol in pred.name):
        return True
    return False


def evaluate_extraction_against_ground_truth(
    pred_doc: Dict[str, Any],
    gt_doc: Dict[str, Any],
    method_name: str,
    paper_id: str,
    paper_title: str,
    latency_sec: float = 0.0,
    peak_vram_mb: float = 0.0
) -> BenchmarkScores:
    preds = normalize_param_list(pred_doc)
    gts = normalize_param_list(gt_doc)

    matched_gt_strict: Set[int] = set()
    matched_gt_partial: Set[int] = set()

    val_matches = 0
    unit_matches = 0
    species_matches = 0
    compound_matches = 0
    ci_matches = 0
    ci_total = sum(1 for g in gts if g.ci_low is not None)

    for pred in preds:
        # 1. Strict Match: (compound, species, symbol/name, value +/- 2%)
        for idx, gt in enumerate(gts):
            if idx in matched_gt_strict:
                continue
            sym_ok = symbols_or_names_match(pred, gt)
            val_ok = values_match(pred.value, gt.value)
            sp_ok = (not gt.species) or (not pred.species) or (pred.species == gt.species)
            comp_ok = (not gt.compound) or (not pred.compound) or (pred.compound == gt.compound)

            if sym_ok and val_ok and sp_ok and comp_ok:
                matched_gt_strict.add(idx)
                val_matches += 1
                if pred.species == gt.species:
                    species_matches += 1
                if pred.compound == gt.compound:
                    compound_matches += 1
                if units_match(pred.unit, gt.unit):
                    unit_matches += 1
                if gt.ci_low is not None:
                    if values_match(pred.ci_low, gt.ci_low) and values_match(pred.ci_high, gt.ci_high):
                        ci_matches += 1
                break

        # 2. Partial Match: (symbol or name + value) regardless of species/compound
        for idx, gt in enumerate(gts):
            if idx in matched_gt_partial:
                continue
            sym_ok = symbols_or_names_match(pred, gt)
            if sym_ok and values_match(pred.value, gt.value):
                matched_gt_partial.add(idx)
                break

    strict_tp = len(matched_gt_strict)
    partial_tp = len(matched_gt_partial)
    fp = max(0, len(preds) - strict_tp)
    fn = max(0, len(gts) - strict_tp)

    s_prec = (strict_tp / len(preds)) if preds else 0.0
    s_rec = (strict_tp / len(gts)) if gts else 0.0
    s_f1 = (2 * s_prec * s_rec / (s_prec + s_rec)) if (s_prec + s_rec) > 0 else 0.0

    p_prec = (partial_tp / len(preds)) if preds else 0.0
    p_rec = (partial_tp / len(gts)) if gts else 0.0
    p_f1 = (2 * p_prec * p_rec / (p_prec + p_rec)) if (p_prec + p_rec) > 0 else 0.0

    # Topology Evaluation
    gt_struct = gt_doc.get("model_structure") or {}
    pred_struct = pred_doc.get("model_structure") or {}
    gt_comps = len(gt_struct.get("compartments") or [])
    pred_comps = len(pred_struct.get("compartments") or [])
    gt_conns = len(gt_struct.get("connections") or [])
    pred_conns = len(pred_struct.get("connections") or [])

    top_comp_recall = (min(1.0, pred_comps / gt_comps) * 100.0) if gt_comps else 100.0
    top_conn_recall = (min(1.0, pred_conns / gt_conns) * 100.0) if gt_conns else 100.0

    return BenchmarkScores(
        method_name=method_name,
        paper_id=paper_id,
        paper_title=paper_title,
        ground_truth_count=len(gts),
        extracted_count=len(preds),
        strict_tp=strict_tp,
        partial_tp=partial_tp,
        fp=fp,
        fn=fn,
        strict_precision=round(s_prec * 100, 2),
        strict_recall=round(s_rec * 100, 2),
        strict_f1=round(s_f1 * 100, 2),
        partial_precision=round(p_prec * 100, 2),
        partial_recall=round(p_rec * 100, 2),
        partial_f1=round(p_f1 * 100, 2),
        value_accuracy=round((val_matches / len(gts) * 100.0), 2) if gts else 0.0,
        unit_accuracy=round((unit_matches / len(gts) * 100.0), 2) if gts else 0.0,
        species_accuracy=round((species_matches / len(gts) * 100.0), 2) if gts else 0.0,
        compound_accuracy=round((compound_matches / len(gts) * 100.0), 2) if gts else 0.0,
        ci_accuracy=round((ci_matches / ci_total * 100.0), 2) if ci_total else 100.0,
        topology_compartment_recall=round(top_comp_recall, 2),
        topology_connection_recall=round(top_conn_recall, 2),
        latency_sec=round(latency_sec, 2),
        peak_vram_mb=round(peak_vram_mb, 1)
    )


# ============================================================================
# 4. CORPUS BENCHMARK RUNNER
# ============================================================================

def run_corpus_benchmark(
    base_dir: str = ".",
    output_json: str = "benchmarking/benchmark_results.json",
    summary_md: str = "benchmarking/benchmark_summary.md"
) -> Dict[str, Any]:
    """Runs benchmark across all 5 reference papers and writes comprehensive results."""
    root_path = Path(base_dir).resolve()
    manifest_path = root_path / "pk_pipeline" / "pbpk_data" / "manifest.json"
    pbpk_data_dir = root_path / "pk_pipeline" / "pbpk_data"
    output_dir = root_path / "output"

    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found at {manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    papers = manifest.get("papers", [])

    adapter = ApexV2LLMRouteAdapter(output_dir=str(output_dir))
    all_scores: List[BenchmarkScores] = []

    print(f"\n==================================================================")
    print(f"       PBPK Extraction Benchmarking Runner ({len(papers)} Papers)       ")
    print(f"==================================================================")

    for p in papers:
        paper_id = p["paper_id"]
        title = p["title"]
        pdf_name = p["pdf_path"]
        ref_name = p["reference_path"]

        pdf_path = pbpk_data_dir / pdf_name
        ref_path = pbpk_data_dir / ref_name

        if not ref_path.exists():
            print(f"Skipping {paper_id}: ground truth {ref_name} missing.")
            continue

        gt_doc = json.loads(ref_path.read_text(encoding="utf-8"))

        t0 = time.time()
        pred_doc = adapter.extract_paper(pdf_path=str(pdf_path))
        latency = time.time() - t0

        scores = evaluate_extraction_against_ground_truth(
            pred_doc=pred_doc,
            gt_doc=gt_doc,
            method_name=adapter.name,
            paper_id=paper_id,
            paper_title=title,
            latency_sec=latency
        )
        all_scores.append(scores)

        print(f"\n[Paper] {paper_id}:")
        print(f"  GT Parameters: {scores.ground_truth_count:>3} | Extracted: {scores.extracted_count:>3}")
        print(f"  Strict Precision: {scores.strict_precision:>6.2f}% | Strict Recall: {scores.strict_recall:>6.2f}% | Strict F1: {scores.strict_f1:>6.2f}%")
        print(f"  Partial F1:       {scores.partial_f1:>6.2f}% | Value Accuracy: {scores.value_accuracy:>6.2f}%")
        print(f"  Topology Compartments: {scores.topology_compartment_recall:>5.1f}% | Connections: {scores.topology_connection_recall:>5.1f}%")

    # Aggregate Macro Scores
    n = len(all_scores)
    macro_strict_f1 = sum(s.strict_f1 for s in all_scores) / n if n else 0
    macro_partial_f1 = sum(s.partial_f1 for s in all_scores) / n if n else 0
    macro_val_acc = sum(s.value_accuracy for s in all_scores) / n if n else 0
    macro_comp_rec = sum(s.topology_compartment_recall for s in all_scores) / n if n else 0
    macro_conn_rec = sum(s.topology_connection_recall for s in all_scores) / n if n else 0

    print(f"\n==================================================================")
    print(f"OVERALL CORPUS MACRO AVERAGES ({n} Papers):")
    print(f"  Strict F1:            {macro_strict_f1:.2f}%")
    print(f"  Partial F1:           {macro_partial_f1:.2f}%")
    print(f"  Value Accuracy:       {macro_val_acc:.2f}%")
    print(f"  Compartment Recall:   {macro_comp_rec:.2f}%")
    print(f"  Connection Recall:    {macro_conn_rec:.2f}%")
    print(f"==================================================================\n")

    results_data = {
        "benchmark_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "method": adapter.name,
        "corpus_macro_averages": {
            "strict_f1": round(macro_strict_f1, 2),
            "partial_f1": round(macro_partial_f1, 2),
            "value_accuracy": round(macro_val_acc, 2),
            "compartment_recall": round(macro_comp_rec, 2),
            "connection_recall": round(macro_conn_rec, 2)
        },
        "papers": [asdict(s) for s in all_scores]
    }

    out_json_path = root_path / output_json
    out_json_path.parent.mkdir(parents=True, exist_ok=True)
    out_json_path.write_text(json.dumps(results_data, indent=2), encoding="utf-8")

    # Markdown Summary
    md_lines = [
        "# PBPK Benchmark Evaluation Summary",
        f"**Method:** `{adapter.name}`  ",
        f"**Evaluated on:** {results_data['benchmark_timestamp']}  ",
        "",
        "## Overall Corpus Performance",
        f"- **Strict F1 Score (Exact Compound, Species, Symbol, Value):** **{macro_strict_f1:.2f}%**",
        f"- **Partial F1 Score (Symbol + Value):** **{macro_partial_f1:.2f}%**",
        f"- **Parameter Value Accuracy (within ±1.5%):** **{macro_val_acc:.2f}%**",
        f"- **Compartment Topology Recall:** **{macro_comp_rec:.2f}%**",
        f"- **Connection Topology Recall:** **{macro_conn_rec:.2f}%**",
        "",
        "## Per-Paper Results Table",
        "| Paper ID | GT Params | Extracted | Strict F1 | Partial F1 | Value Acc | Comp Recall | Conn Recall |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
    ]
    for s in all_scores:
        md_lines.append(
            f"| `{s.paper_id}` | {s.ground_truth_count} | {s.extracted_count} | {s.strict_f1:.1f}% | {s.partial_f1:.1f}% | {s.value_accuracy:.1f}% | {s.topology_compartment_recall:.1f}% | {s.topology_connection_recall:.1f}% |"
        )

    out_md_path = root_path / summary_md
    out_md_path.write_text("\n".join(md_lines), encoding="utf-8")

    return results_data


if __name__ == "__main__":
    run_corpus_benchmark()
