"""
gliner_pipeline.py
Standalone extraction pipeline using GLiNER Zero-Shot Span NER.
Paper-agnostic: combines structured table recognition (find_tables) with GLiNER entity recognition,
scrubs citation years and unit exponents, supports CIs and ranges, and deduplicates records.
"""

import os
import re
import json
import uuid
import torch
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set
import pymupdf

from pk_pipeline.schemas import (
    ExtractedDocument,
    ExtractedParameter,
    PageMetadata,
    ModelClassification,
    ModelStructure
)
from pk_pipeline.main import refresh_parameter_views


class GLiNERPipeline:
    def __init__(self, model_id: str = "urchade/gliner_small-v2.1"):
        self.model_id = model_id
        self._model = None
        self.labels = [
            "chemical_compound",
            "biological_species",
            "life_stage",
            "formulation",
            "pharmacokinetic_parameter",
            "symbol",
            "measurement_unit"
        ]

    def _get_model(self):
        if self._model is None:
            from gliner import GLiNER
            print(f"[GLiNER] Loading GLiNER model ({self.model_id})...")
            model = GLiNER.from_pretrained(self.model_id)
            if torch.cuda.is_available():
                model = model.to("cuda")
            self._model = model
        return self._model

    def run(self, pdf_path: str) -> Dict[str, Any]:
        """Extracts parameters from PDF using GLiNER span recognition."""
        doc = pymupdf.open(pdf_path)
        meta = doc.metadata or {}
        title = meta.get("title") or Path(pdf_path).stem
        author_str = meta.get("author") or ""
        authors = [a.strip() for a in author_str.split(";") if a.strip()]

        model = self._get_model()
        parameters: List[Dict[str, Any]] = []

        # Matches Table 1, Table I, Table II, Table S1, etc.
        table_regex = re.compile(r"^Table\s+(?:\d+|[IVX]+|S\d+)\b", re.IGNORECASE)

        # 1. First Pass: Structured 2D Table Parsing (for bordered/lined tables)
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            tabs = page.find_tables()

            if tabs.tables:
                for tab in tabs:
                    data = tab.extract()
                    if not data or len(data) < 2:
                        continue

                    # Analyze header rows with GLiNER
                    header_row = [str(c).strip() if c else "" for c in data[0]]
                    header_text = " | ".join(header_row)
                    try:
                        header_entities = model.predict_entities(header_text, self.labels, threshold=0.30)
                    except Exception:
                        header_entities = []

                    compounds_by_col: Dict[int, str] = {}
                    for col_idx, col_name in enumerate(header_row):
                        for ent in header_entities:
                            if ent["label"] == "chemical_compound" and ent["text"].lower() in col_name.lower():
                                compounds_by_col[col_idx] = ent["text"].upper()

                    # Process table data rows
                    for row_idx, row in enumerate(data[1:]):
                        clean_row = [str(c).strip() if c else "" for c in row]
                        if not any(clean_row):
                            continue

                        name = clean_row[0]
                        symbol = None
                        if len(clean_row) > 1 and len(clean_row[1]) < 12 and not re.search(r"^\d", clean_row[1]):
                            symbol = clean_row[1]

                        unit = "dimensionless"
                        unit_m = re.search(r"\(([^)]+)\)", name)
                        if unit_m:
                            unit = unit_m.group(1).strip()

                        # Extract numbers from data cells
                        for col_idx, cell in enumerate(clean_row[1:], start=1):
                            scrubbed_cell = self._scrub_citations_and_exponents(cell)
                            ci_m = re.search(r"^([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s*\(\s*([+-]?\d+(?:\.\d+)?)\s*,\s*([+-]?\d+(?:\.\d+)?)\s*\)", scrubbed_cell)
                            range_m = re.search(r"^([+-]?\d+(?:\.\d+)?)\s*(?:-|to)\s*([+-]?\d+(?:\.\d+)?)", scrubbed_cell)
                            val_m = re.search(r"^([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)", scrubbed_cell)

                            val: Optional[float] = None
                            ci_low: Optional[float] = None
                            ci_high: Optional[float] = None
                            start_val: Optional[float] = None
                            end_val: Optional[float] = None

                            if ci_m:
                                val = float(ci_m.group(1))
                                ci_low = float(ci_m.group(2))
                                ci_high = float(ci_m.group(3))
                            elif range_m:
                                start_val = float(range_m.group(1))
                                end_val = float(range_m.group(2))
                                val = (start_val + end_val) / 2.0
                            elif val_m:
                                val = float(val_m.group(1))

                            if val is not None:
                                compound = compounds_by_col.get(col_idx)
                                p_id = f"gliner_{uuid.uuid4().hex[:10]}"
                                parameters.append({
                                    "parameter_id": p_id,
                                    "parameter_name": name,
                                    "parameter_name_original": name,
                                    "symbol": symbol,
                                    "symbol_original": symbol,
                                    "parameter_class": "physiological" if any(k in name.lower() for k in ["blood", "volume", "flow", "weight"]) else "compound_specific",
                                    "context": {
                                        "species": "human",
                                        "compound": compound,
                                        "life_stage": None,
                                        "formulation": None
                                    },
                                    "quantitative_data": {
                                        "value": val,
                                        "start_value": start_val,
                                        "end_value": end_val,
                                        "ci_low": ci_low,
                                        "ci_high": ci_high,
                                        "value_text": cell,
                                        "unit": unit,
                                        "unit_original": unit
                                    },
                                    "provenance": {
                                        "source_location": f"Page {page_idx+1} Table",
                                        "source_quote": f"{name}: {cell}",
                                        "status": "not_reported"
                                    },
                                    "confidence": {
                                        "value_confidence": "high" if ci_m else "medium",
                                        "unit_confidence": "medium" if unit != "dimensionless" else "low"
                                    }
                                })

        # 2. Second Pass: Text-based Sequential Table Parsing Fallback (for borderless PDFs)
        if len(parameters) < 10:
            for page_idx in range(len(doc)):
                page_text = doc[page_idx].get_text("text")
                lines = [l.strip() for l in page_text.split("\n") if l.strip()]
                in_table = False
                curr_caption = ""
                curr_species = "human"
                curr_life_stage = None
                curr_formulation = None
                table_compounds: List[str] = []

                i = 0
                while i < len(lines):
                    line = lines[i]

                    # Table caption detection
                    if table_regex.match(line):
                        in_table = True
                        curr_caption = line[:100]
                        # Use GLiNER to identify compound, species, life stage in caption
                        try:
                            ents = model.predict_entities(curr_caption, self.labels, threshold=0.30)
                            table_compounds = [e["text"].upper() for e in ents if e["label"] == "chemical_compound"]
                            for e in ents:
                                if e["label"] == "biological_species":
                                    curr_species = e["text"].lower()
                                elif e["label"] == "life_stage":
                                    curr_life_stage = e["text"].lower()
                                elif e["label"] == "formulation":
                                    curr_formulation = e["text"].lower()
                        except Exception:
                            pass
                        i += 1
                        continue

                    if in_table and any(stop in line for stop in ["Figure", "References", "Discussion", "Funding", "Declaration"]):
                        in_table = False

                    if in_table:
                        # Skip sensitivity / benchmark dose tables
                        if any(k in curr_caption.lower() for k in ["pod", "benchmark dose", "bmd", "sensitivity analysis"]):
                            i += 1
                            continue

                        # Species word-boundary detection
                        if re.search(r"\b(?:rat|rats|sprague-dawley|wistar)\b", line, re.I):
                            curr_species = "rat"
                        elif re.search(r"\b(?:mouse|mice)\b", line, re.I):
                            curr_species = "mouse"
                        elif re.search(r"\b(?:nonhuman primate|monkey|monkeys|cynomolgus)\b", line, re.I):
                            curr_species = "nonhuman primate"
                        elif re.search(r"\b(?:human|humans)\b", line, re.I) and len(line) < 20:
                            curr_species = "human"

                        # Detect compounds in short column headers
                        if len(line) < 30:
                            try:
                                col_ents = model.predict_entities(line, self.labels, threshold=0.30)
                                for e in col_ents:
                                    if e["label"] == "chemical_compound" and e["text"].upper() not in table_compounds:
                                        table_compounds.append(e["text"].upper())
                            except Exception:
                                pass

                        is_header = any(h == line.lower() for h in [
                            "species", "type of variable", "variable", "name", "mean (95% ci)", "mean", "source",
                            "parameter", "value", "unit", "physiological", "chemical-specific"
                        ])

                        if not is_header and len(line) > 2:
                            name = line
                            sym = ""
                            vals: List[Tuple[float, Optional[float], Optional[float], str]] = []
                            j = i + 1

                            if j < len(lines) and len(lines[j]) < 12 and not re.search(r"^\d", lines[j]) and not any(h == lines[j].lower() for h in ["species", "variable", "name", "source"]):
                                sym = lines[j]
                                j += 1

                            while j < len(lines) and j < i + 8:
                                scrubbed_line = self._scrub_citations_and_exponents(lines[j])
                                ci_m = re.search(r"^([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s*\(\s*([+-]?\d+(?:\.\d+)?)\s*,\s*([+-]?\d+(?:\.\d+)?)\s*\)", scrubbed_line)
                                range_m = re.search(r"^([+-]?\d+(?:\.\d+)?)\s*(?:-|to)\s*([+-]?\d+(?:\.\d+)?)", scrubbed_line)
                                val_m = re.search(r"^([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)", scrubbed_line)

                                if ci_m:
                                    try:
                                        vals.append((float(ci_m.group(1)), float(ci_m.group(2)), float(ci_m.group(3)), lines[j]))
                                        j += 1
                                        continue
                                    except ValueError:
                                        pass
                                elif range_m:
                                    try:
                                        s_v = float(range_m.group(1))
                                        e_v = float(range_m.group(2))
                                        vals.append(((s_v + e_v) / 2.0, s_v, e_v, lines[j]))
                                        j += 1
                                        continue
                                    except ValueError:
                                        pass
                                elif val_m:
                                    try:
                                        vals.append((float(val_m.group(1)), None, None, lines[j]))
                                        j += 1
                                        continue
                                    except ValueError:
                                        pass
                                break

                            if vals:
                                unit = "dimensionless"
                                unit_m = re.search(r"\(([^)]+)\)", name)
                                if unit_m:
                                    unit = unit_m.group(1).strip()

                                for v_idx, (v_num, ci_l, ci_h, v_raw) in enumerate(vals):
                                    comp = table_compounds[v_idx] if v_idx < len(table_compounds) else (table_compounds[0] if table_compounds else None)
                                    p_id = f"gliner_{uuid.uuid4().hex[:10]}"
                                    parameters.append({
                                        "parameter_id": p_id,
                                        "parameter_name": name,
                                        "parameter_name_original": name,
                                        "symbol": sym or None,
                                        "symbol_original": sym or None,
                                        "parameter_class": "physiological" if any(k in name.lower() for k in ["blood", "volume", "flow", "weight"]) else "compound_specific",
                                        "context": {
                                            "species": curr_species,
                                            "compound": comp,
                                            "life_stage": curr_life_stage,
                                            "formulation": curr_formulation
                                        },
                                        "quantitative_data": {
                                            "value": v_num,
                                            "ci_low": ci_l,
                                            "ci_high": ci_h,
                                            "value_text": v_raw,
                                            "unit": unit,
                                            "unit_original": unit
                                        },
                                        "provenance": {
                                            "source_location": curr_caption or f"Page {page_idx+1} Table",
                                            "source_quote": f"{name}: {v_raw}",
                                            "status": "not_reported"
                                        },
                                        "confidence": {
                                            "value_confidence": "high" if ci_l is not None else "medium",
                                            "unit_confidence": "medium" if unit != "dimensionless" else "low"
                                        }
                                    })
                                i = j
                                continue
                    i += 1

        # 3. Deduplicate extracted parameters
        deduped: List[Dict[str, Any]] = []
        seen_keys: Set[Tuple[str, Optional[float], Optional[str], str]] = set()
        for p in parameters:
            q = p.get("quantitative_data", {})
            ctx = p.get("context", {})
            k = (
                p.get("parameter_name", "").lower(),
                q.get("value"),
                ctx.get("compound"),
                ctx.get("species", "")
            )
            if k not in seen_keys:
                seen_keys.add(k)
                deduped.append(p)

        doc_dict = {
            "page_metadata": {
                "title": title or None,
                "authors": authors or None,
                "journal": None,
                "year": None
            },
            "model_classification": {
                "model_type": "not_applicable",
                "evidence_quote": None
            },
            "model_structure": {
                "reported_compartment_count": None,
                "compartments": [],
                "connections": [],
                "equations_provided": "none"
            },
            "model_parameters": deduped
        }

        refresh_parameter_views(doc_dict)
        return ExtractedDocument.model_validate(doc_dict).model_dump(mode="json")

    def _scrub_citations_and_exponents(self, text: str) -> str:
        # Scrub citation years like (2013), (1999a), et al. 2025
        s = re.sub(r"\((?:19|20)\d{2}[a-z]?\)", "", text)
        s = re.sub(r"et\s+al\.?,?\s*(?:19|20)\d{2}[a-z]?", "", s, flags=re.I)
        # Scrub unit exponents like kg^0.74 or kg0.74
        s = re.sub(r"kg(?:\^?0\.\d+)", "kg", s)
        return s.strip()


if __name__ == "__main__":
    import sys
    test_pdf = sys.argv[1] if len(sys.argv) > 1 else "pk_pipeline/pbpk_data/Dean et al. 2025 3 compartment (PFOA, PFOS, PFHxS).pdf"
    pipeline = GLiNERPipeline()
    res = pipeline.run(test_pdf)
    print(f"[GLiNER Pipeline] Extracted {len(res.get('model_parameters', []))} parameters.")
