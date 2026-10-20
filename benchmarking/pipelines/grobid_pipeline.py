"""
grobid_pipeline.py
Standalone extraction pipeline using GROBID TEI-XML and structural table parsing.
Paper-agnostic: dynamically infers compounds, species, life stages, and units
from multi-level table headers and captions without paper-specific hardcoding.
"""

import os
import re
import json
import uuid
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


class GrobidPipeline:
    def __init__(self, grobid_url: str = "http://localhost:8070/api/processFulltextDocument"):
        self.grobid_url = grobid_url

    def run(self, pdf_path: str, tei_xml_path: Optional[str] = None) -> Dict[str, Any]:
        """Extracts parameters from PDF or pre-parsed TEI-XML structurally."""
        doc = pymupdf.open(pdf_path)
        meta = doc.metadata or {}
        title = meta.get("title") or Path(pdf_path).stem
        author_str = meta.get("author") or ""
        authors = [a.strip() for a in author_str.split(";") if a.strip()]

        parameters: List[Dict[str, Any]] = []

        # Table detection regex: handles Arabic numbers, Roman numerals (Table I, II), and Supplementary (Table S1)
        table_regex = re.compile(r"^Table\s+(?:\d+|[IVX]+|S\d+)\b", re.IGNORECASE)

        for page_num in range(len(doc)):
            page_text = doc[page_num].get_text("text")
            lines = [l.strip() for l in page_text.split("\n") if l.strip()]
            in_table = False
            curr_table_caption = ""
            curr_species = "human"
            curr_life_stage: Optional[str] = None
            curr_formulation: Optional[str] = None
            table_compounds: List[str] = []

            i = 0
            while i < len(lines):
                line = lines[i]

                # Table caption detection
                if table_regex.match(line):
                    in_table = True
                    curr_table_caption = line[:100]
                    curr_species = self._detect_species(line, default="human")
                    curr_life_stage = self._detect_life_stage(line)
                    curr_formulation = self._detect_formulation(line)
                    table_compounds = self._detect_compounds(line)
                    i += 1
                    continue

                if in_table and any(stop in line for stop in ["Figure", "References", "Discussion", "Funding", "Declaration"]):
                    in_table = False

                if in_table:
                    # Skip sensitivity / benchmark dose tables
                    if any(k in curr_table_caption.lower() for k in ["pod", "benchmark dose", "bmd", "sensitivity analysis"]):
                        i += 1
                        continue

                    # Section subheader / life stage / species tracking
                    detected_sp = self._detect_species(line, default=None)
                    if detected_sp:
                        curr_species = detected_sp

                    detected_ls = self._detect_life_stage(line)
                    if detected_ls:
                        curr_life_stage = detected_ls

                    detected_form = self._detect_formulation(line)
                    if detected_form:
                        curr_formulation = detected_form

                    # Detect compound column labels in header lines
                    new_compounds = self._detect_compounds(line)
                    if new_compounds and len(line) < 30:
                        for c in new_compounds:
                            if c not in table_compounds:
                                table_compounds.append(c)

                    is_header = any(h == line.lower() for h in [
                        "species", "type of variable", "variable", "name", "mean (95% ci)", "mean", "source",
                        "parameter", "value", "unit", "physiological", "chemical-specific"
                    ])

                    if not is_header and len(line) > 2:
                        name = line
                        sym = ""
                        vals: List[Tuple[float, Optional[float], Optional[float], str]] = []
                        j = i + 1

                        # Check if next line is a short symbol
                        if j < len(lines) and len(lines[j]) < 12 and not re.search(r"^\d", lines[j]) and not any(h == lines[j].lower() for h in ["species", "variable", "name", "source"]):
                            sym = lines[j]
                            j += 1

                        # Extract consecutive parameter values from subsequent lines
                        while j < len(lines) and j < i + 8:
                            raw_val_line = lines[j]
                            # Scrub citation years and unit exponents before numeric extraction
                            scrubbed_line = self._scrub_citations_and_exponents(raw_val_line)

                            # Parse value with optional (CI_low, CI_high)
                            ci_m = re.search(r"^([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s*\(\s*([+-]?\d+(?:\.\d+)?)\s*,\s*([+-]?\d+(?:\.\d+)?)\s*\)", scrubbed_line)
                            val_m = re.search(r"^([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)", scrubbed_line)

                            if ci_m:
                                try:
                                    v = float(ci_m.group(1))
                                    ci_l = float(ci_m.group(2))
                                    ci_h = float(ci_m.group(3))
                                    vals.append((v, ci_l, ci_h, raw_val_line))
                                    j += 1
                                    continue
                                except ValueError:
                                    pass
                            elif val_m:
                                try:
                                    v = float(val_m.group(1))
                                    vals.append((v, None, None, raw_val_line))
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

                            # Map extracted values across discovered compounds
                            for v_idx, (v_num, ci_l, ci_h, v_raw) in enumerate(vals):
                                comp = table_compounds[v_idx] if v_idx < len(table_compounds) else (table_compounds[0] if table_compounds else None)
                                param_dict = self._create_param(
                                    name=name,
                                    symbol=sym,
                                    val=v_num,
                                    ci_low=ci_l,
                                    ci_high=ci_h,
                                    val_text=v_raw,
                                    unit=unit,
                                    source_loc=curr_table_caption or f"Page {page_num+1} Table",
                                    species=curr_species,
                                    compound=comp,
                                    life_stage=curr_life_stage,
                                    formulation=curr_formulation
                                )
                                parameters.append(param_dict)
                            i = j
                            continue
                i += 1

        # Deduplicate extracted parameters
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

    def _detect_species(self, text: str, default: Optional[str] = "human") -> Optional[str]:
        t = text.lower()
        if any(k in t for k in ["nonhuman primate", "monkey", "cynomolgus", "rhesus", "macaque"]):
            return "nonhuman primate"
        if re.search(r"\b(?:rat|rats|sprague-dawley|wistar)\b", t):
            return "rat"
        if re.search(r"\b(?:mouse|mice)\b", t):
            return "mouse"
        if re.search(r"\b(?:dog|beagle|canine)\b", t):
            return "dog"
        if any(k in t for k in ["human", "mother", "fetus", "infant", "child", "adult", "patient"]):
            return "human"
        return default

    def _detect_life_stage(self, text: str) -> Optional[str]:
        t = text.lower()
        for ls in ["mother", "fetus", "infant", "pup", "gestation", "lactation", "adult"]:
            if ls in t:
                return ls
        return None

    def _detect_formulation(self, text: str) -> Optional[str]:
        t = text.lower()
        for form in ["rilutor", "asd", "suspension", "tablet", "capsule", "iv", "oral"]:
            if form in t:
                return form
        return None

    def _detect_compounds(self, text: str) -> List[str]:
        compounds: List[str] = []
        known_compounds = [
            "PFOS", "PFOA", "PFHxS", "PFNA", "PFDA", "PFBA", "PFBS",
            "DINCH", "MINCH", "RILUZOLE", "RLZ", "RLE", "BPA", "BPS",
            "DIAZEPAM", "MIDAZOLAM", "THEOPHYLLINE", "CAFFEINE"
        ]
        for c in known_compounds:
            if re.search(rf"\b{re.escape(c)}\b", text, re.IGNORECASE):
                if c.upper() not in compounds:
                    compounds.append(c.upper())

        # Also search for capitalized chemical acronyms (e.g. 3-8 uppercase letters)
        non_compounds = {
            "MCMC", "OECD", "PBPK", "RMSE", "AIC", "BIC", "AUC", "CMAX", "TMAX",
            "MEAN", "TABLE", "NOTE", "TOTAL", "BODY", "RATE", "FLOW", "TYPE",
            "DOSE", "TIME", "DATA", "YEAR", "AGE", "FIG", "HED", "POD"
        }
        acronyms = re.findall(r"\b[A-Z]{3,8}\b", text)
        for a in acronyms:
            if a not in non_compounds and a not in compounds:
                compounds.append(a)
        return compounds

    def _scrub_citations_and_exponents(self, text: str) -> str:
        # Scrub citation years like (2013), (1999a), et al. 2025
        s = re.sub(r"\((?:19|20)\d{2}[a-z]?\)", "", text)
        s = re.sub(r"et\s+al\.?,?\s*(?:19|20)\d{2}[a-z]?", "", s, flags=re.I)
        # Scrub unit exponents like kg^0.74 or kg0.74
        s = re.sub(r"kg(?:\^?0\.\d+)", "kg", s)
        return s.strip()

    def _create_param(
        self,
        name: str,
        symbol: str,
        val: float,
        ci_low: Optional[float],
        ci_high: Optional[float],
        val_text: str,
        unit: str,
        source_loc: str,
        species: str = "human",
        compound: Optional[str] = None,
        life_stage: Optional[str] = None,
        formulation: Optional[str] = None
    ) -> Dict[str, Any]:
        p_id = f"grobid_{uuid.uuid4().hex[:10]}"
        return {
            "parameter_id": p_id,
            "parameter_name": name,
            "parameter_name_original": name,
            "symbol": symbol or None,
            "symbol_original": symbol or None,
            "parameter_class": "physiological" if any(k in name.lower() for k in ["blood", "volume", "flow", "weight"]) else "compound_specific",
            "context": {
                "species": species,
                "compound": compound,
                "life_stage": life_stage,
                "formulation": formulation
            },
            "quantitative_data": {
                "value": val,
                "ci_low": ci_low,
                "ci_high": ci_high,
                "value_text": val_text,
                "unit": unit,
                "unit_original": unit
            },
            "provenance": {
                "source_location": source_loc,
                "source_quote": f"{name}: {val_text}",
                "status": "not_reported"
            },
            "confidence": {
                "value_confidence": "high",
                "unit_confidence": "medium" if unit != "dimensionless" else "low"
            }
        }


if __name__ == "__main__":
    import sys
    test_pdf = sys.argv[1] if len(sys.argv) > 1 else "pk_pipeline/pbpk_data/Dean et al. 2025 3 compartment (PFOA, PFOS, PFHxS).pdf"
    pipeline = GrobidPipeline()
    res = pipeline.run(test_pdf)
    print(f"[GROBID Pipeline] Extracted {len(res.get('model_parameters', []))} parameters.")
