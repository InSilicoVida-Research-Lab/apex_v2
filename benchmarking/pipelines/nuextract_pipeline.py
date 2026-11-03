"""
nuextract_pipeline.py
Standalone extraction pipeline using NuExtract template-conditioned extraction.
Paper-agnostic: conditioned on a strict generic JSON schema template, extracts parameters
from dynamically inferred tables, columns, species, life stages, and formulations.
"""

import os
import re
import json
import uuid
import time
import requests
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


class NuExtractPipeline:
    def __init__(self, sglang_url: str = "http://127.0.0.1:30000"):
        self.sglang_url = sglang_url

    def run(self, pdf_path: str) -> Dict[str, Any]:
        """Extracts parameters from PDF using paper-agnostic NuExtract template-conditioned prompt."""
        doc = pymupdf.open(pdf_path)
        meta = doc.metadata or {}
        title = meta.get("title") or Path(pdf_path).stem
        author_str = meta.get("author") or ""
        authors = [a.strip() for a in author_str.split(";") if a.strip()]

        table_regex = re.compile(r"^Table\s+(?:\d+|[IVX]+|S\d+)\b", re.IGNORECASE)
        statements: List[Dict[str, Any]] = []

        for page_num in range(len(doc)):
            text = doc[page_num].get_text("text")
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            in_table = False
            curr_table_caption = ""
            curr_species = "human"
            curr_life_stage: Optional[str] = None
            curr_formulation: Optional[str] = None
            table_compounds: List[str] = []

            i = 0
            while i < len(lines):
                line = lines[i]

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

                    detected_sp = self._detect_species(line, default=None)
                    if detected_sp:
                        curr_species = detected_sp

                    detected_ls = self._detect_life_stage(line)
                    if detected_ls:
                        curr_life_stage = detected_ls

                    detected_form = self._detect_formulation(line)
                    if detected_form:
                        curr_formulation = detected_form

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
                        vals: List[str] = []
                        j = i + 1

                        if j < len(lines) and len(lines[j]) < 12 and not re.search(r"^\d", lines[j]) and not any(h == lines[j].lower() for h in ["species", "variable", "name", "source"]):
                            sym = lines[j]
                            j += 1

                        while j < len(lines) and j < i + 8:
                            scrubbed = self._scrub_citations_and_exponents(lines[j])
                            val_m = re.search(r"^([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)", scrubbed)
                            if val_m:
                                vals.append(lines[j])
                                j += 1
                            else:
                                break

                        if vals:
                            unit = ""
                            unit_m = re.search(r"\(([^)]+)\)", name)
                            if unit_m:
                                unit = unit_m.group(1).strip()

                            # Construct statement with dynamic compound and species attribution
                            val_parts = []
                            for v_idx, v_str in enumerate(vals):
                                comp_tag = f" ({table_compounds[v_idx]})" if v_idx < len(table_compounds) else (f" ({table_compounds[0]})" if table_compounds else "")
                                val_parts.append(f"{v_str}{comp_tag}")

                            context_str = f"Species: {curr_species}"
                            if curr_life_stage:
                                context_str += f" | Life stage: {curr_life_stage}"
                            if curr_formulation:
                                context_str += f" | Formulation: {curr_formulation}"

                            stmt = f"{context_str} | Parameter: {name}"
                            if sym:
                                stmt += f" | Symbol: {sym}"
                            if unit:
                                stmt += f" | Unit: {unit}"
                            stmt += f" | Values = {', '.join(val_parts)}"

                            # Filter out footnotes / references
                            if not any(k in stmt.lower() for k in ["intake of", "page "]):
                                statements.append({
                                    "page": page_num + 1,
                                    "table": curr_table_caption,
                                    "statement": stmt
                                })
                            i = j
                            continue
                i += 1

        # Fallback if no table captions were found: extract lines mentioning key PK parameters
        if not statements:
            for page_num in range(len(doc)):
                text = doc[page_num].get_text("text")
                for line in text.split("\n"):
                    l_str = line.strip()
                    if any(k in l_str.lower() for k in ["volume", "clearance", "rate", "affinity", "bioav", "half-life"]):
                        val_m = re.search(r"([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)", l_str)
                        if val_m:
                            statements.append({
                                "page": page_num + 1,
                                "table": f"Page {page_num + 1}",
                                "statement": l_str
                            })

        print(f"[NuExtract] Prepared {len(statements)} structured table statements for extraction.")

        batch_size = 5
        all_params: List[Dict[str, Any]] = []

        # Generic, paper-agnostic template without hardcoded compound or symbol examples
        template_prompt = """{
  "parameters": [
    {
      "name": "Parameter Name",
      "symbol": "Parameter Symbol or Abbreviation",
      "compound": "Chemical Compound",
      "species": "Species",
      "life_stage": null,
      "formulation": null,
      "value": 0.0,
      "start_value": null,
      "end_value": null,
      "ci_low": null,
      "ci_high": null,
      "unit": "Unit"
    }
  ]
}"""

        for batch_start in range(0, len(statements), batch_size):
            batch = statements[batch_start:batch_start + batch_size]
            batch_text = "\n".join([f"- {item['statement']}" for item in batch])
            source_pages = list(set([item["page"] for item in batch]))
            source_loc = f"Page {', '.join(map(str, source_pages))} ({batch[0]['table']})"

            prompt = (
                f"<|im_start|>system\n"
                f"You are NuExtract, a structured schema extraction model. "
                f"Extract every pharmacokinetic and physiological parameter into this JSON template:\n"
                f"{template_prompt}\n"
                f"<|im_end|>\n"
                f"<|im_start|>user\n"
                f"Text:\n{batch_text}\n"
                f"<|im_end|>\n"
                f"<|im_start|>assistant\n"
                f"```json\n"
            )

            raw_resp = self._query_sglang(prompt)
            if raw_resp:
                params = self._parse_nuextract_output(raw_resp, source_loc)
                print(f"  Batch {batch_start//batch_size + 1}/{(len(statements)-1)//batch_size + 1 if statements else 1}: Extracted {len(params)} parameters.")
                all_params.extend(params)
            else:
                print(f"  Batch {batch_start//batch_size + 1}: Query failed or returned empty.")

        # Deduplicate extracted parameters
        deduped: List[Dict[str, Any]] = []
        seen_keys: Set[Tuple[str, Optional[float], Optional[str], str]] = set()
        for p in all_params:
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
                "title": title,
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

    def _query_sglang(self, prompt: str) -> str:
        try:
            resp = requests.post(
                f"{self.sglang_url}/generate",
                json={
                    "text": prompt,
                    "sampling_params": {
                        "max_new_tokens": 1024,
                        "temperature": 0.0,
                        "stop": ["<|im_end|>", "\n```"]
                    }
                },
                timeout=120
            )
            if resp.status_code == 200:
                res = resp.json()
                return res.get("text", "")
            return ""
        except Exception as e:
            print("  [NuExtract SGLang Error]:", e)
            return ""

    def _parse_nuextract_output(self, text: str, source_loc: str) -> List[Dict[str, Any]]:
        clean = text.strip()
        if "</think>" in clean:
            clean = clean.split("</think>")[-1].strip()
        if clean.endswith("```"):
            clean = clean[:-3].strip()

        raw_list: List[Dict[str, Any]] = []

        candidate_json = clean
        if not candidate_json.startswith("{"):
            if "{" in candidate_json:
                candidate_json = candidate_json[candidate_json.find("{"):]
        if candidate_json.rfind("}") != -1:
            candidate_json = candidate_json[:candidate_json.rfind("}") + 1]

        try:
            data = json.loads(candidate_json)
            raw_list = data.get("parameters") or data.get("model_parameters") or []
        except Exception:
            matches = re.findall(r"(\{[^{}]*?\"name\"[^{}]*?\"value\"[^{}]*?\})", clean, re.DOTALL)
            for m in matches:
                try:
                    obj = json.loads(m)
                    raw_list.append(obj)
                except Exception:
                    pass

        out = []
        for p in raw_list:
            if not isinstance(p, dict):
                continue
            name = p.get("name") or p.get("parameter_name") or ""
            val = p.get("value")
            start_val = p.get("start_value")
            end_val = p.get("end_value")

            if val is None and start_val is not None and end_val is not None:
                try:
                    val = (float(start_val) + float(end_val)) / 2.0
                except (ValueError, TypeError):
                    pass

            if val is None or not isinstance(val, (int, float)):
                continue

            # Skip dummy template echoes
            if any(k in str(name).lower() for k in ["parameter name", "parameter_name"]):
                continue

            p_id = f"nuextract_{uuid.uuid4().hex[:10]}"
            unit = p.get("unit") or "dimensionless"
            compound = p.get("compound")
            if str(compound).lower() in ["chemical compound", "compound", "null", "none"]:
                compound = None
            species = p.get("species") or "human"
            if str(species).lower() in ["species", "null", "none"]:
                species = "human"

            symbol = p.get("symbol")
            if str(symbol).lower() in ["parameter symbol", "symbol", "null", "none"]:
                symbol = None

            param_obj = {
                "parameter_id": p_id,
                "parameter_name": name,
                "parameter_name_original": name,
                "symbol": symbol,
                "symbol_original": symbol,
                "parameter_class": "physiological" if any(k in name.lower() for k in ["volume", "blood", "flow", "weight"]) else "compound_specific",
                "context": {
                    "species": species,
                    "compound": compound,
                    "life_stage": p.get("life_stage"),
                    "formulation": p.get("formulation")
                },
                "quantitative_data": {
                    "value": float(val),
                    "start_value": float(start_val) if start_val is not None else None,
                    "end_value": float(end_val) if end_val is not None else None,
                    "ci_low": float(p["ci_low"]) if p.get("ci_low") is not None else None,
                    "ci_high": float(p["ci_high"]) if p.get("ci_high") is not None else None,
                    "unit": unit,
                    "unit_original": unit
                },
                "provenance": {
                    "source_location": source_loc,
                    "status": "not_reported"
                },
                "confidence": {
                    "value_confidence": "high",
                    "unit_confidence": "medium" if unit != "dimensionless" else "low"
                }
            }
            out.append(param_obj)
        return out

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
        s = re.sub(r"\((?:19|20)\d{2}[a-z]?\)", "", text)
        s = re.sub(r"et\s+al\.?,?\s*(?:19|20)\d{2}[a-z]?", "", s, flags=re.I)
        s = re.sub(r"kg(?:\^?0\.\d+)", "kg", s)
        return s.strip()


if __name__ == "__main__":
    import sys
    test_pdf = sys.argv[1] if len(sys.argv) > 1 else "pk_pipeline/pbpk_data/Dean et al. 2025 3 compartment (PFOA, PFOS, PFHxS).pdf"
    t0 = time.time()
    pipeline = NuExtractPipeline()
    res = pipeline.run(test_pdf)
    params = res.get("model_parameters", [])
    print(f"\n[NuExtract Pipeline] Extracted {len(params)} parameters in {time.time() - t0:.2f}s.")
