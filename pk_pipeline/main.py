import os
import json
import argparse
import asyncio
import pymupdf
from pdf2image import convert_from_path

import sys
# Ensure the root directory is on PYTHONPATH so pk_pipeline modules can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pk_pipeline.schemas import ExtractedDocument, ExtractionRequest
from pk_pipeline.ml_services import SGLangExtractor
from pk_pipeline.config import logger, Config

# Initialize models lazily
extractor = None
tatr_processor = None
tatr_model = None
tatr_sr_processor = None
tatr_sr_model = None

# Species sub-header keywords to detect in table section rows
_SPECIES_KEYWORDS = [
    "rat", "human", "mouse", "rabbit", "dog", "monkey",
    "pig", "hamster", "guinea pig", "non-human primate", "nhp", "sheep"
]

# Removed ColQwenRetriever as per MinerU migration plan

def get_extractor():
    global extractor
    if extractor is None:
        print("Loading Vision-Language Extractor: Qwen3-VL-8B-Instruct (via SGLang)...")
        extractor = SGLangExtractor()
        print("Extractor model loaded successfully.")
    return extractor

def get_tatr():
    global tatr_processor, tatr_model
    if tatr_processor is None or tatr_model is None:
        print("Loading Table Transformer (TATR) object detection model...")
        from transformers import AutoImageProcessor, TableTransformerForObjectDetection
        tatr_processor = AutoImageProcessor.from_pretrained("microsoft/table-transformer-detection")
        tatr_model = TableTransformerForObjectDetection.from_pretrained("microsoft/table-transformer-detection")
        print("TATR loaded successfully.")
    return tatr_processor, tatr_model

laya_filter = None

def get_laya():
    global laya_filter
    if laya_filter is None:
        print("Loading System-1 Decision Model: Laya (convaiinnovations/laya)...")
        from pk_pipeline.ml_services import LayaFilter
        laya_filter = LayaFilter()
    return laya_filter

wevisdoc_parser = None

def get_wevisdoc():
    global wevisdoc_parser
    if wevisdoc_parser is None:
        print("Loading WeVisDoc Document OCR: Tencent/WeVisDoc-4B...")
        from pk_pipeline.ml_services import WeVisDocParser
        wevisdoc_parser = WeVisDocParser()
    return wevisdoc_parser

def print_laya_summary(stats: dict, triage_type: str):
    print(f"\n{'='*65}")
    print(f" LAYA TRIAGE & FILTER SUMMARY")
    print(f"{'='*65}")
    print(f"  • Pre-flight Document Classification: {triage_type}")
    print(f"  • Candidate Chunks Evaluated:         {stats.get('evaluated', 0)}")
    print(f"  • Chunks Retained for Extraction:     {stats.get('retained', 0)}")
    print(f"  • Chunks Discarded by Laya:           {stats.get('discarded', 0)}")
    if stats.get('discarded', 0) > 0:
        est_saved = stats['discarded'] * 25
        print(f"  • Estimated VLM Compute Saved:        ~{est_saved}s ({stats['discarded']} calls skipped)")
    print(f"{'='*65}\n")

def print_wevisdoc_summary(stats: dict):
    if stats.get("pages_transcribed", 0) > 0:
        print(f"\n{'='*65}")
        print(f" WEVISDOC-4B OCR TABLE TRANSCRIPTION SUMMARY")
        print(f"{'='*65}")
        print(f"  • Model:                Tencent/WeVisDoc-4B")
        print(f"  • Table Pages Parsed:   {stats.get('pages_transcribed', 0)}")
        print(f"  • Output Format:        Structured HTML Tables & LaTeX Formulas")
        print(f"{'='*65}\n")


# Removed TATR-SR globals and helpers, using Header Repetition instead

def convert_pdf_to_images(pdf_path: str):
    logger.debug(f"Attempting to convert PDF to images: {pdf_path}")
    if not os.path.exists(pdf_path):
        logger.error(f"File not found: {pdf_path}")
        raise FileNotFoundError(f"File not found: {pdf_path}")
    
    try:
        # 300 DPI for sharper table crops — critical for tiny subscripts (e.g. kg^0.74)
        images = convert_from_path(pdf_path, dpi=300)
        logger.info(f"Successfully converted PDF to {len(images)} images.")
        return images
    except Exception as e:
        logger.error(f"Failed to convert PDF: {str(e)}")
        raise

import copy
import re

# ─────────────────────────────────────────────────────────────
# Parameter Category Classifier
# ─────────────────────────────────────────────────────────────

# Keywords strongly associated with SYSTEM-SPECIFIC (physiological) parameters.
# These describe the biological organism, not the drug.
_SYSTEM_KEYWORDS = [
    # Anatomical / organ volumes
    "body weight", "organ weight", "tissue volume", "volume fraction",
    "cardiac output", "blood flow", "regional blood flow", "plasma flow",
    "glomerular filtration", "renal filtration", "urine flow",
    "fractional blood flow", "fractional tissue volume",
    # Tissue composition
    "water content", "lipid content", "protein content", "neutral lipid",
    "phospholipid", "albumin", "water fraction", "lipid fraction",
    "neutral phospholipid", "acidic phospholipid",
    # Biological activity / enzyme/transporter abundance
    "enzyme abundance", "transporter expression", "mrna", "cyp abundance",
    "microsomal protein", "hepatocellularity", "liver weight",
    # Common PBPK anatomical symbols
    "qco", "qliv", "qkid", "qgut", "qfat", "qsk", "qmam", "qr", "qfil",
    "vblood", "vliv", "vkid", "vgut", "vfat", "vsk", "vr", "vmam", "vfil",
    "bw", "vfet",
    # General physiological descriptors
    "physiological", "anatomical", "hemodynamic", "species-specific",
    "population", "tissue",
]

# Keywords strongly associated with COMPOUND-SPECIFIC (chemical/biochemical) parameters.
_COMPOUND_KEYWORDS = [
    # Physicochemical
    "molecular weight", "logp", "logd", "log p", "log d",
    "pka", "solubility", "intrinsic solubility", "particle size",
    "particle density", "particle radius", "lipophilicity",
    "ionization", "dissociation", "Henderson",
    # Protein binding / blood
    "plasma protein binding", "fraction unbound", "fu", "fup", "fub",
    "blood-to-plasma", "blood to plasma", "b/p ratio", "b:p",
    # Permeability / transport
    "permeability", "caco-2", "caco2", "papp", "passive permeability",
    "p-glycoprotein", "pgp", "efflux", "influx transporter",
    "membrane permeability",
    # Metabolism / clearance
    "intrinsic clearance", "clint", "cl_int", "metabolic clearance",
    "in vitro clearance", "microsomal clearance", "hepatic clearance",
    "renal clearance", "total clearance", "apparent clearance",
    "half-life", "half life", "t1/2", "elimination rate",
    "metabolic rate", "vmax", "km",
    # Inhibition
    "inhibition constant", "ki", "ic50", "ec50",
    # Distribution
    "volume of distribution", "vd", "vc", "vp",
    "partition coefficient", "tissue-to-plasma", "tissue:plasma",
    "distribution coefficient",
    # Absorption
    "absorption rate", "ka", "bioavailability", "fraction absorbed",
    "first-pass", "gut absorption", "dissolution",
]


# Subclasses that always belong to the 'physiological' class
_PHYSIOLOGICAL_SUBCLASSES = [
    # Blood flow subclasses
    "organ_blood_flow_fraction", "blood_flow_fraction", "organ_blood_flow",
    # Volume subclasses
    "organ_volume_fraction", "volume_fraction", "organ_volume",
    # Other physiological
    "glomerular_filtration", "glomerular_filtration_rate",
    "cardiac_output",
    "body_weight",
    "hematocrit",
    "milk_flow",
    "urine_production",
]

# Subclasses that always belong to the 'biochemical' class
_BIOCHEMICAL_SUBCLASSES = [
    # Transport / binding
    "partition_coefficient", "fraction_unbound",
    # Absorption
    "absorption_rate_constant", "gastric_emptying_rate", "fecal_elimination_rate_constant",
    # Enzyme kinetics
    "maximal_velocity", "michaelis_menten_constant",
    # Clearance / elimination
    "renal_clearance", "metabolic_clearance", "clearance",
    "biliary_elimination_rate", "urinary_excretion_rate",
    # Distribution
    "distribution_volume", "distribution_rate",
    # PK properties
    "elimination_half_life", "bioavailability",
    # Transfer / activity
    "transfer_rate", "relative_activity_factor",
    # In vitro
    "microsomal_protein_yield", "fraction_metabolized", "ptc_protein",
]


def _classify_parameter_category(param: dict) -> str:
    """Classify a single parameter dict as 'physiological', 'biochemical', or 'compound_specific'.

    Rules (applied in order, first match wins):
    1. If parameter_subclass maps to a known physiological subclass -> physiological.
    2. If parameter_subclass maps to a known biochemical subclass -> biochemical.
    3. If parameter_name or symbol contains physiological keywords -> physiological.
    4. If parameter_name or symbol contains biochemical/compound keywords -> biochemical.
    5. Default: physiological (anatomical parameters dominate PBPK tables).
    """
    import re as _re
    subclass = (param.get("parameter_subclass") or "").lower()
    name = (param.get("parameter_name_original") or param.get("parameter_name") or "").lower()
    symbol = (param.get("symbol_original") or param.get("symbol") or "").lower()
    full_text = f"{name} {symbol} {subclass}"

    def _matches(kw: str, text: str) -> bool:
        if len(kw) <= 4:
            return bool(_re.search(r'\b' + _re.escape(kw) + r'\b', text))
        return kw in text

    # Rule 1: subclass-based physiological
    for sub in _PHYSIOLOGICAL_SUBCLASSES:
        if sub in subclass:
            return "physiological"

    # Rule 2: subclass-based biochemical
    for sub in _BIOCHEMICAL_SUBCLASSES:
        if sub in subclass:
            return "biochemical"

    # Rule 3: name-based physiological
    for kw in _SYSTEM_KEYWORDS:
        if _matches(kw, full_text):
            return "physiological"

    # Rule 4: name-based biochemical/compound
    for kw in _COMPOUND_KEYWORDS:
        if _matches(kw, full_text):
            return "biochemical"

    # Rule 5: default
    return "physiological"


def flatten_parameter_blocks(parameter_blocks: list) -> list:
    import hashlib
    flat_params = []
    for block in parameter_blocks:
        for p in getattr(block, "parameters", []):
            if hasattr(block, "implied_species") and block.implied_species and not p.context.species:
                p.context.species = block.implied_species
            if hasattr(block, "implied_unit_original") and block.implied_unit_original and not p.quantitative_data.unit_original:
                p.quantitative_data.unit_original = block.implied_unit_original
            if hasattr(block, "parameter_class") and block.parameter_class and not getattr(p, "parameter_class", None):
                p.parameter_class = block.parameter_class
                
            if not p.parameter_id:
                prov = getattr(p, "provenance", None)
                ctx = getattr(p, "context", None)
                source_tbl = getattr(prov, "source_table", "") or ""
                row_str = getattr(prov, "row_id", "") or "_".join(getattr(prov, "row_path", []) or [])
                col_str = getattr(prov, "column_id", "") or "_".join(getattr(prov, "column_path", []) or [])
                p_name = getattr(p, "parameter_name_original", "") or getattr(p, "symbol_original", "") or ""
                cmpd = getattr(ctx, "compound", "") or ""
                spec = getattr(ctx, "species", "") or ""
                
                raw_identity = f"{source_tbl}|{row_str}|{col_str}|{p_name}|{cmpd}|{spec}".lower().strip()
                if raw_identity == "|||||":
                    raw_identity = p.model_dump_json()
                h = hashlib.sha256(raw_identity.encode("utf-8")).hexdigest()[:16]
                p.parameter_id = f"param_{h}"
                
            flat_params.append(p.model_dump())
    return flat_params


def _unit_from_parameter_name(name: str) -> str | None:
    """Return a unit printed at the end of a table's parameter label."""
    match = re.search(r"\(([^()]+)\)\s*$", name or "")
    return match.group(1).strip() if match else None


def _parse_cell_uncertainty(value_text: str) -> tuple[float | None, float | None]:
    """Parse the common ``estimate (lower, upper)`` table notation."""
    match = re.search(
        r"\(\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s*,\s*"
        r"([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s*\)",
        value_text or "",
    )
    if not match:
        return None, None
    return float(match.group(1)), float(match.group(2))


def _parameters_from_table_evidence(table_evidences: list[dict]) -> list[dict]:
    """Recover parameter records when a table extraction returns an empty block.

    JATS parsing already gives us aligned row, column, and cell evidence. This
    intentionally conservative fallback only handles parameter tables with both
    a descriptor column (``Variable``/``Name``) and a numerical estimate column
    (``Mean``/``Estimate``/``Value``). Outcome tables are left untouched.
    Recovered records retain cell-level provenance and are marked for review.
    """
    from pk_pipeline.schemas import (
        BiologicalContext,
        ConfidenceScores,
        ExtractedParameter,
        Provenance,
        QuantitativeData,
        Uncertainty,
    )
    import hashlib

    recovered = []
    species_terms = (
        "nonhuman primate", "cynomolgus monkey", "rhesus macaque",
        "human", "rat", "mouse", "rabbit", "dog", "monkey", "pig",
    )

    for table in table_evidences or []:
        if not isinstance(table, dict) or table.get("evidence_status") != "success":
            continue
        columns = table.get("columns") or []
        rows = {row.get("row_id"): row for row in table.get("rows") or []}
        cells = table.get("cells") or []
        if not columns or not rows or not cells:
            continue

        column_paths = {
            col.get("column_id"): [str(part) for part in col.get("path") or []]
            for col in columns
        }
        descriptor_columns = {
            column_id for column_id, path in column_paths.items()
            if any(token in " ".join(path).lower() for token in ("variable", "parameter", "name", "symbol"))
        }
        value_columns = {
            column_id for column_id, path in column_paths.items()
            if any(token in " ".join(path).lower() for token in ("mean", "estimate", "value", "fitted", "optimized"))
        }
        # A table must explicitly look like a model-parameter table. This
        # prevents toxicity/outcome tables with numeric result columns from
        # becoming model parameters.
        if not descriptor_columns or not value_columns:
            continue

        cells_by_row: dict[str, list[dict]] = {}
        for cell in cells:
            cells_by_row.setdefault(cell.get("row_id"), []).append(cell)

        table_compounds = [str(c) for c in table.get("subject_compounds") or []]
        for row_id, row_cells in cells_by_row.items():
            row = rows.get(row_id)
            if not row:
                continue
            row_path = [str(part) for part in row.get("path") or []]
            row_text = " ".join(row_path)
            descriptor_cells = [c for c in row_cells if c.get("column_id") in descriptor_columns]
            if not descriptor_cells:
                continue
            # Prefer the descriptive cell over a short symbol such as BW.
            parameter_name = max((str(c.get("text") or "").strip() for c in descriptor_cells), key=len, default="")
            if not parameter_name:
                continue
            symbol = min((str(c.get("text") or "").strip() for c in descriptor_cells), key=len, default=None)
            if symbol == parameter_name:
                symbol = None
            unit = _unit_from_parameter_name(parameter_name)
            species = next((term for term in species_terms if re.search(rf"\b{re.escape(term)}\b", row_text, re.I)), None)

            for cell in row_cells:
                column_id = cell.get("column_id")
                value = cell.get("numeric_value")
                if column_id not in value_columns or value is None:
                    continue
                col_path = column_paths.get(column_id, [])
                header_text = " ".join(col_path)
                compound = next((c for c in table_compounds if re.search(rf"\b{re.escape(c)}\b", header_text, re.I)), None)
                if compound is None and len(table_compounds) == 1:
                    compound = table_compounds[0]
                lower, upper = _parse_cell_uncertainty(str(cell.get("text") or ""))
                source_quote = " | ".join([
                    str(table.get("title") or table.get("table_id") or ""),
                    " > ".join(row_path),
                    " > ".join(col_path),
                    str(cell.get("text") or ""),
                ])
                source_cell = next(
                    (c for c in row_cells if "source" in " ".join(column_paths.get(c.get("column_id"), [])).lower()),
                    None,
                )
                source_text = str(source_cell.get("text") or "").lower() if source_cell else ""
                status = "fitted" if "optim" in source_text else "literature"
                identity = f"{table.get('table_id')}|{row_id}|{column_id}|{parameter_name}|{compound}|{species}".lower()
                parameter = ExtractedParameter(
                    parameter_id=f"param_{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:16]}",
                    parameter_name_original=parameter_name,
                    symbol_original=symbol,
                    context=BiologicalContext(compound=compound, species=species),
                    quantitative_data=QuantitativeData(
                        value_text=str(cell.get("text") or ""),
                        value=float(value),
                        uncertainty=Uncertainty(lower=lower, upper=upper) if lower is not None else None,
                        unit_original=unit,
                        unit_standardized=unit,
                    ),
                    provenance=Provenance(
                        source_table=table.get("table_id"),
                        row_id=row_id,
                        column_id=column_id,
                        cell_id=cell.get("cell_id"),
                        row_path=row_path,
                        column_path=col_path,
                        source_quote=source_quote,
                        status=status,
                        evidence_directness="direct",
                    ),
                    confidence=ConfidenceScores(
                        value_confidence="high",
                        provenance_confidence="high",
                        unit_confidence="medium" if unit else "low",
                    ),
                    needs_review=True,
                )
                recovered.append(parameter.model_dump())
    return recovered

def _load_chunk_checkpoint(checkpoint_dir: str, chunk_key: str):
    """Factor 5 & 6: Load previously extracted chunk to resume interrupted runs."""
    import re
    safe_key = re.sub(r"[^A-Za-z0-9_.-]", "_", str(chunk_key)).strip("_")[:80] or "chunk"
    cp_file = os.path.join(checkpoint_dir, f"{safe_key}.json")
    if os.path.exists(cp_file):
        try:
            with open(cp_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            from pk_pipeline.schemas import ExtractedPage
            return ExtractedPage.model_validate(data)
        except Exception as e:
            logger.warning(f"Could not read chunk checkpoint {cp_file}: {e}")
    return None

def _save_chunk_checkpoint(checkpoint_dir: str, chunk_key: str, page) -> None:
    """Factor 5 & 6: Persist extracted chunk immediately for fault tolerance and resume."""
    import re
    safe_key = re.sub(r"[^A-Za-z0-9_.-]", "_", str(chunk_key)).strip("_")[:80] or "chunk"
    cp_file = os.path.join(checkpoint_dir, f"{safe_key}.json")
    try:
        os.makedirs(checkpoint_dir, exist_ok=True)
        with open(cp_file, "w", encoding="utf-8") as f:
            if hasattr(page, "model_dump_json"):
                f.write(page.model_dump_json(indent=2))
            else:
                json.dump(page, f, indent=2)
    except Exception as e:
        logger.warning(f"Failed to save chunk checkpoint {cp_file}: {e}")

def _merge_biological_basis(final_doc: dict, extracted_page) -> None:
    if not extracted_page or not getattr(extracted_page, "biological_basis", None):
        return
    bb_dict = extracted_page.biological_basis.model_dump(by_alias=True, exclude_none=True)
    if not final_doc.get("biological_basis"):
        final_doc["biological_basis"] = bb_dict
        return
    curr_bb = final_doc["biological_basis"]
    existing_quotes = {
        (a.get("evidence_quote") or a.get("description") or "").strip().lower()
        for a in curr_bb.get("stated_assumptions", [])
    }
    for a in bb_dict.get("stated_assumptions", []):
        key = (a.get("evidence_quote") or a.get("description") or "").strip().lower()
        if key and key not in existing_quotes:
            curr_bb.setdefault("stated_assumptions", []).append(a)
            existing_quotes.add(key)
    existing_adme = set(curr_bb.get("adme_determinants", []))
    for d in bb_dict.get("adme_determinants", []):
        if d not in existing_adme:
            curr_bb.setdefault("adme_determinants", []).append(d)
            existing_adme.add(d)
    existing_mech = set(curr_bb.get("specialized_mechanisms", []))
    for m in bb_dict.get("specialized_mechanisms", []):
        if m not in existing_mech:
            curr_bb.setdefault("specialized_mechanisms", []).append(m)
            existing_mech.add(m)


def _merge_model_structure(final_doc: dict, extracted_page) -> None:
    """Merge model structure, compartments, connections, and scaling rules from visual diagram and text."""
    if not extracted_page or not getattr(extracted_page, "model_structure", None):
        return
    ms_dict = extracted_page.model_structure.model_dump(by_alias=True, exclude_none=True)
    if not final_doc.get("model_structure"):
        final_doc["model_structure"] = ms_dict
        return

    curr_ms = final_doc["model_structure"]
    new_conns = ms_dict.get("connections", [])
    curr_conns = curr_ms.get("connections", [])
    if len(new_conns) > len(curr_conns):
        curr_ms["connections"] = new_conns
    elif new_conns and curr_conns:
        # Merge any connections not already present
        existing_conn_keys = {(c.get("source"), c.get("target")) for c in curr_conns}
        for c in new_conns:
            if (c.get("source"), c.get("target")) not in existing_conn_keys:
                curr_conns.append(c)

    new_comps = ms_dict.get("compartments", [])
    curr_comps = curr_ms.get("compartments", [])
    if len(new_comps) > len(curr_comps) or not curr_comps:
        curr_ms["compartments"] = new_comps
    elif new_comps and curr_comps:
        existing_comp_ids = {c.get("id") for c in curr_comps}
        for c in new_comps:
            if c.get("id") not in existing_comp_ids:
                curr_comps.append(c)

    for k in ["allometric_scaling_rules", "scaling_equations"]:
        if ms_dict.get(k):
            existing = set(curr_ms.get(k, []))
            for item in ms_dict[k]:
                if item not in existing:
                    curr_ms.setdefault(k, []).append(item)

    if ms_dict.get("absorption") and not curr_ms.get("absorption"):
        curr_ms["absorption"] = ms_dict["absorption"]
    if ms_dict.get("elimination") and not curr_ms.get("elimination"):
        curr_ms["elimination"] = ms_dict["elimination"]



def finalize_extracted_document(document: dict) -> dict:
    """Validate and serialize the canonical output contract before persistence."""
    return ExtractedDocument.model_validate(document).model_dump(mode="json")


def refresh_parameter_views(document: dict) -> None:
    """Materialize backwards-compatible parameter category views from canonical data."""
    parameters = document.get("model_parameters", [])
    document["system_specific_parameters"] = [
        parameter for parameter in parameters if parameter.get("parameter_class") == "physiological"
    ]
    document["compound_specific_parameters"] = [
        parameter for parameter in parameters if parameter.get("parameter_class") != "physiological"
    ]

def post_process_document(document, pdf_path):
    print("Step 4: Running Python Post-Processing Cleanup...")
    # XML table parsing can be completely successful while a constrained LLM
    # response returns an empty parameter_blocks list.  Do not silently emit a
    # superficially successful document with no model parameters in that case.
    if not document.get("model_parameters"):
        recovered = _parameters_from_table_evidence(document.get("table_evidence", []))
        if recovered:
            document["model_parameters"] = recovered
            logger.warning(
                "LLM extraction returned no model parameters; recovered %d "
                "cell-backed records from parameter-table evidence.",
                len(recovered),
            )
        elif document.get("table_evidence"):
            logger.warning(
                "LLM extraction returned no model parameters and no safe "
                "parameter-table fallback was available."
            )
    # 1. Clean up parameters with no quantitative value, and split multi-formulation comma-separated values
    new_params = []
    for p in document.get("model_parameters", []):
        q_data = p.get("quantitative_data", {})
        
        # Skip parameters with no quantitative value whatsoever
        if q_data.get("value_text") is None and q_data.get("value") is None:
            continue
            
        # Reroute non-PBPK physical measurements (like contact angle) that the LLM mistakenly placed here
        p_name_lower = (p.get("parameter_name_original") or "").lower()
        uo_str = q_data.get("unit_original") or ""
        
        if "contact angle" in p_name_lower or uo_str == "°" or "particle size" in p_name_lower or "dissolution" in p_name_lower:
            print(f"  -> [Safety] Rerouting '{p.get('parameter_name_original')}' from model_parameters to formulation_characterization.")
            # extract first formulation name if present
            fm_form = (p.get("context") or {}).get("formulation", [None])
            fm_form = fm_form[0] if fm_form else (p.get("context") or {}).get("compound")
            fm = {
                "measurement_type": "contact_angle" if ("angle" in p_name_lower or uo_str == "°") else "particle_size",
                "sample_component": fm_form,
                "probe_liquid": None,
                "value": q_data.get("value"),
                "variance": q_data.get("variance"),
                "variance_type": q_data.get("variance_type"),
                "unit": uo_str,
                "provenance": p.get("provenance")
            }
            if "formulation_characterization" not in document:
                document["formulation_characterization"] = []
            document["formulation_characterization"].append(fm)
            continue
        
        # Split comma-separated multi-formulation values into distinct atomic records
        # e.g. Kabs = '0.69, 2.19' for formulations ['Rilutor', 'ASD']
        val_text = (q_data.get("value_text") or "")
        formulations = (p.get("context") or {}).get("formulation") or []
        if (
            "," in val_text
            and q_data.get("value") is None  # not already a single float
        ):
            raw_vals = [v.strip() for v in val_text.split(",")]
            parsed = []
            for rv in raw_vals:
                try:
                    parsed.append((rv, float(rv)))
                except ValueError:
                    pass
            if parsed and len(parsed) > 1:
                # If we don't have enough formulations, pad with generic names or reuse what we have
                forms_to_use = formulations.copy()
                while len(forms_to_use) < len(parsed):
                    forms_to_use.append(f"Formulation {len(forms_to_use)+1}")
                
                for (rv, fv), form in zip(parsed, forms_to_use):
                    child = copy.deepcopy(p)
                    child["context"]["formulation"] = [form] if form and not form.startswith("Formulation ") else []
                    child["quantitative_data"]["value_text"] = rv
                    child["quantitative_data"]["value"] = fv
                    child["quantitative_data"]["range_start"] = None
                    child["quantitative_data"]["range_end"] = None
                    new_params.append(child)
                continue
        
        # Enforce type: if value is somehow a string (LLM hallucination), nullify it
        if q_data.get("value") is not None and not isinstance(q_data.get("value"), (int, float)):
            try:
                p["quantitative_data"]["value"] = float(q_data.get("value"))
            except (ValueError, TypeError):
                p["quantitative_data"]["value"] = None
        
        # Prevent silent order-of-magnitude corruption: check for dropped SI prefixes
        uo = q_data.get("unit_original")
        us = q_data.get("unit_standardized")
        if uo and us:
            uo_lower = uo.lower()
            us_lower = us.lower()
            prefixes = ["nmol", "μmol", "umol", "mmol", "pmol", "mg", "μg", "ug", "ng", "pg", "ml", "μl", "ul"]
            for prefix in prefixes:
                norm_p = prefix.replace("μ", "u")
                norm_uo = uo_lower.replace("μ", "u")
                norm_us = us_lower.replace("μ", "u")
                if norm_p in norm_uo and norm_p not in norm_us:
                    print(f"  -> [Safety] Nullifying corrupted unit_standardized '{us}' (dropped '{prefix}' from '{uo}')")
                    p["quantitative_data"]["unit_standardized"] = None
                    break
        
        # Also fix when range_start and range_end are actually comma-pairs for two formulations
        r_start = q_data.get("range_start")
        r_end = q_data.get("range_end")
        if r_start is not None and r_end is not None:
            try:
                if len(formulations) == 2:
                    # This is two formulation values, not a range
                    for fv, form in [(float(r_start), formulations[0]), (float(r_end), formulations[1])]:
                        child = copy.deepcopy(p)
                        child["context"]["formulation"] = [form]
                        child["quantitative_data"]["value"] = fv
                        child["quantitative_data"]["value_text"] = str(fv)
                        child["quantitative_data"]["range_start"] = None
                        child["quantitative_data"]["range_end"] = None
                        new_params.append(child)
                    continue
            except (TypeError, ValueError):
                pass
            
        new_params.append(p)
    document["model_parameters"] = new_params
    
    # 2. Text-sweep for targeted commonly dropped parameters (e.g. ratios broken across columns)
    try:
        if pdf_path and os.path.exists(pdf_path):
            doc = pymupdf.open(pdf_path)
            text = ""
            for page in doc:
                text += page.get_text() + " "
                
            # Generic regex for "ratio [...] for [COMPOUND]"
            if "ratio" in text.lower() or "ktrans" in text.lower() or "placental" in text.lower():
                # Restrict compound to 2+ uppercase letters/numbers to avoid "the", "methods"
                matches = re.finditer(r'([0-9]*\.?[0-9]+)\s+for\s+([A-Z0-9][A-Za-z0-9\-_]{1,10})', text)
                for match in matches:
                    val = float(match.group(1))
                    comp = match.group(2)
                    
                    # Ignore common stop words that might match
                    if comp.lower() in ["the", "methods", "example", "all", "each", "this"]:
                        continue
                        
                    # check context window
                    start = max(0, match.start() - 200)
                    end = min(len(text), match.end() + 200)
                    context = text[start:end].lower()
                    
                    if "placental" in context or "cord/mother" in context or "maternal/cord" in context or "ktrans" in context:
                        # Check if this parameter already exists in document["parameters"]
                        exists = False
                        for p in document["model_parameters"]:
                            c = (p.get("context") or {}).get("compound", "")
                            if not c: continue
                            n = p.get("parameter_name_original", "").lower()
                            if c.lower() == comp.lower() and ("ratio" in n or "placental" in n):
                                exists = True
                                break
                        if not exists:
                            print(f"  -> Post-processing sweep found missed parameter: {comp} Placental transfer ratio = {val}")
                            from pk_pipeline.schemas import ExtractedParameter, BiologicalContext, QuantitativeData, Provenance
                            import hashlib
                            raw_id = f"sweep|placental_transfer_ratio|{comp}".lower()
                            h = hashlib.sha256(raw_id.encode("utf-8")).hexdigest()[:16]
                            sweep_param = ExtractedParameter(
                                parameter_id=f"param_{h}",
                                parameter_class="biochemical",
                                parameter_subclass="partition_coefficient",
                                parameter_name_original=f"Placental transfer ratio for {comp}",
                                symbol_original="ktrans",
                                context=BiologicalContext(
                                    compound=comp,
                                    species=None,
                                    life_stage=None,
                                    organ="placenta",
                                    route=None,
                                    population=None
                                ),
                                quantitative_data=QuantitativeData(
                                    value_text=str(val),
                                    value=val,
                                    unit_original="dimensionless",
                                    unit_standardized="dimensionless"
                                ),
                                provenance=Provenance(
                                    source_location="Regex text sweep fallback",
                                    source_quote=text[match.start():match.end()],
                                    status="literature",
                                    evidence_directness="direct"
                                ),
                                needs_review=True
                            )
                            document["model_parameters"].append(sweep_param.model_dump())
                            
    except Exception as e:
        print(f"  -> Error in post-processing text sweep: {e}")

    # 2.5 PBPK Inheritance, Dimensionless Unit Whitelist, and Deduplication
    print("  -> Applying PBPK inheritance, dimensionless unit whitelist, and deduplication...")
    from pk_pipeline.compartmental_assembler import (
        apply_pbpk_inheritance,
        deduplicate_and_format_records
    )
    document["model_parameters"] = apply_pbpk_inheritance(document.get("model_parameters", []))
    document["model_parameters"] = deduplicate_and_format_records(document.get("model_parameters", []))

    # 3. Classify each parameter using the 3-class taxonomy
    print("  -> Classifying parameters into physiological / biochemical / compound_specific...")
    for p in document.get("model_parameters", []):
        # Only override if not already set by VLM or block propagation
        cls = p.get("parameter_class") or _classify_parameter_category(p)
        p["parameter_class"] = cls

    # 4. Strict Schema Revalidation for all parameters in canonical model_parameters
    print("  -> Revalidating all parameters against ExtractedParameter schema...")
    from pk_pipeline.schemas import ExtractedParameter
    from pydantic import ValidationError
    validated_params = []
    for p in document.get("model_parameters", []):
        try:
            valid_p = ExtractedParameter.model_validate(p)
            validated_params.append(valid_p.model_dump())
        except ValidationError as exc:
            logger.error(f"Parameter failed final schema validation: {exc}. Parameter: {p.get('parameter_name_original')}")
            if isinstance(p, dict):
                p["needs_review"] = True
                p.setdefault("validation_errors", []).append(str(exc))
                validated_params.append(p)

    # CANONICAL source list - preserved for audit trails and Tier 1 / Tier 2 verification
    document["model_parameters"] = validated_params
    
    # Filtered views derived from canonical model_parameters
    refresh_parameter_views(document)
    system_params = document["system_specific_parameters"]
    compound_params = document["compound_specific_parameters"]

    print(f"     physiological: {len(system_params)}  |  compound/biochemical: {len(compound_params)}  |  total canonical: {len(validated_params)}")

    return document

async def run_pipeline(pdf_path: str, target_compounds: list = None, use_wevisdoc: bool = True, force_pdf: bool = False, verify: bool = True, output_dir: str = "output"):
    print(f"Starting PK Extraction Pipeline for: {os.path.basename(pdf_path)}")
    logger.info(f"Received request to extract PK data from: {pdf_path}")
    
    pdf_stem = os.path.splitext(os.path.basename(pdf_path))[0]
    checkpoint_dir = os.path.join(output_dir or Config.OUTPUT_DIR, ".checkpoints", pdf_stem)
    os.makedirs(checkpoint_dir, exist_ok=True)
    
    wevisdoc_stats = {"pages_transcribed": 0}

    # --- Fast Document Triage via Laya ---
    doc_triage_type = "unknown"
    laya_stats = {"evaluated": 0, "discarded": 0, "retained": 0}
    try:
        if pdf_path and os.path.exists(pdf_path):
            with pymupdf.open(pdf_path) as _pdoc:
                if len(_pdoc) > 0:
                    _first_page_text = _pdoc[0].get_text()[:3000]
                    if _first_page_text:
                        doc_triage_type = get_laya().classify_model_type(_first_page_text)
                        print(f"  -> [Laya Pre-flight Triage] Document classified as: '{doc_triage_type}'")
    except Exception as e:
        logger.debug(f"Laya pre-flight triage skipped: {e}")
    
    # --- NEW: Paper Resolution ---
    from pk_pipeline.ingestion.pmc_fetcher import extract_doi_from_pdf, extract_title_from_pdf, resolve_paper
    
    doi = extract_doi_from_pdf(pdf_path)
    title = extract_title_from_pdf(pdf_path, doi=doi)

    res = {"xml_path": None, "pdf_path": None, "source": None, "source_type": "published"}
    if force_pdf:
        print("Step 0/3: --force-pdf enabled: Bypassing publisher XML resolution to force PDF & WeVisDoc OCR pipeline.")
    elif doi or title:
        print("Step 0/3: Resolving paper via PMC/EuropePMC/Unpaywall/Semantic Scholar...")
        res = resolve_paper(doi=doi, title=title, pdf_path=pdf_path)

        if res.get("xml_path"):
            print(f"  -> XML available at {res['xml_path']}! Using JATS XML fast-path...")
            from pk_pipeline.ingestion.xml_parser import parse_jats_xml

            xml_data = parse_jats_xml(res["xml_path"], filter_narrative=True)

            final_document = {
                "page_metadata": xml_data.get("metadata", {"title": None, "authors": None, "journal": None, "year": None}),
                "model_classification": {"model_type": "not_applicable", "evidence_quote": None},
                "model_context": None,
                "biological_basis": None,
                "model_structure": None,
                "metabolic_pathways": [],
                "model_parameters": [],
                "observed_data": [],
                "simulated_data": [],
                "formulation_characterization": [],
                "qualitative_findings": [],
                "parameter_mentions_without_values": [],
                "table_evidence": [],
                "dosing": [],
                "ingestion_source": res.get("source"),
                "ingestion_source_type": res.get("source_type", "published"),
            }

            # Filter out chunks that were skipped by the narrative filter
            chunks = [c for c in xml_data.get("chunks", []) if c.get("kept", True)]

            # Pre-collect any pre-computed XML table evidence into final_document
            for c in chunks:
                te = c.get("table_evidence")
                if te:
                    final_document["table_evidence"].append(te.model_dump())

            # Separate figure chunks — they may need image download + visual dispatch
            figure_chunks  = [c for c in chunks if c["role"] == "figure_xml"]
            text_chunks    = [c for c in chunks if c["role"] != "figure_xml"]

            # Filter narrative text chunks using Laya to avoid wasting LLM compute on empty text
            filtered_text_chunks = []
            for c in text_chunks:
                if c.get("role") == "narrative_xml":
                    laya_stats["evaluated"] += 1
                    keep, prob, mtype = get_laya().is_pk_relevant(c.get("content", ""))
                    if not keep:
                        laya_stats["discarded"] += 1
                        print(f"  -> [Laya Filter] Skipped narrative chunk '{c.get('title', 'narrative')}' (no PK data, p={prob:.2f})")
                        continue
                    laya_stats["retained"] += 1
                filtered_text_chunks.append(c)
            text_chunks = filtered_text_chunks

            diagram_chunks = [c for c in figure_chunks if c.get("is_diagram")]
            caption_chunks = [c for c in figure_chunks if not c.get("is_diagram")]

            # ONLY extract images for chunks that are strictly diagrams
            if diagram_chunks:
                # If we have the local PDF, extract the diagram pages directly from it!
                if pdf_path and os.path.exists(pdf_path):
                    print(f"  -> Extracting {len(diagram_chunks)} diagram images directly from local PDF...")
                    pdf_images = convert_pdf_to_images(pdf_path)
                    pdf_doc = pymupdf.open(pdf_path)
                    
                    for chunk in diagram_chunks:
                        title_to_find = chunk.get("title", "").lower().strip()
                        caption_snippet = chunk.get("caption", "").lower().strip()[:50]
                        best_page_idx = -1
                        
                        for i in range(len(pdf_doc)):
                            page_text = pdf_doc[i].get_text("text").lower()
                            # Prioritize exact caption match
                            if caption_snippet and caption_snippet in page_text:
                                best_page_idx = i
                                break
                            # Fallback to title match
                            elif title_to_find and title_to_find in page_text:
                                best_page_idx = i
                                
                        if best_page_idx != -1:
                            chunk["image_obj"] = pdf_images[best_page_idx]
                            print(f"    - Matched '{title_to_find}' to PDF page {best_page_idx + 1}")
                        else:
                            print(f"    - Could not locate '{title_to_find}' in PDF text.")
                else:
                    # Fallback to PMC downloader if no local PDF was provided
                    from pk_pipeline.ingestion.pmc_fetcher import fetch_all_figures
                    xml_stem = os.path.splitext(os.path.basename(res["xml_path"]))[0]
                    pmcid_for_figs = xml_stem.split("_")[0]
                    print(f"  -> Downloading {len(diagram_chunks)} diagram images from PMC for {pmcid_for_figs}...")
                    diagram_chunks = fetch_all_figures(pmcid_for_figs, diagram_chunks)
                    from PIL import Image
                    for c in diagram_chunks:
                        if c.get("image_path"):
                            try:
                                c["image_obj"] = Image.open(c["image_path"])
                            except Exception as e:
                                print(f"    - Failed to load PMC image {c['image_path']}: {e}")
                
                # Keep only diagrams that have a successfully loaded PIL Image
                diagram_chunks = [c for c in diagram_chunks if "image_obj" in c]

            n_text    = len(text_chunks) + len(caption_chunks)
            n_visual  = len(diagram_chunks)
            print(f"  -> {n_text} text chunks + {n_visual} visual figure chunks queued for LLM.")

            if text_chunks or caption_chunks or diagram_chunks:
                print(f"Step 1/1: Running Extraction ({n_text} text + {n_visual} visual)...")
                # Use concurrency 3 to ensure smooth, non-congested continuous batching on SGLang
                sem = asyncio.Semaphore(3)

                async def bound_extract_text(chunk, idx):
                    chunk_title = chunk.get("title", "") or f"chunk_{idx}"
                    chunk_key = f"xml_{chunk.get('role', 'text')}_{chunk_title}_{idx}"
                    cached = _load_chunk_checkpoint(checkpoint_dir, chunk_key)
                    if cached:
                        n_p = sum(len(b.parameters) for b in cached.parameter_blocks or [])
                        print(f"  -> [Resume] Loaded cached extraction for '{chunk_title}' ({n_p} params)")
                        return cached
                    async with sem:
                        te = chunk.get("table_evidence")
                        page = await get_extractor().extract_from_text(
                            chunk["content"], 
                            role=chunk["role"], 
                            chunk_title=chunk.get("title", ""),
                            table_evidence=te
                        )
                        _save_chunk_checkpoint(checkpoint_dir, chunk_key, page)
                        return page

                async def bound_extract_image(chunk, idx):
                    chunk_title = chunk.get("title", "") or f"diag_{idx}"
                    chunk_key = f"xml_diag_{chunk_title}_{idx}"
                    cached = _load_chunk_checkpoint(checkpoint_dir, chunk_key)
                    if cached:
                        n_p = sum(len(b.parameters) for b in cached.parameter_blocks or [])
                        print(f"  -> [Resume] Loaded cached extraction for '{chunk_title}' ({n_p} params)")
                        return cached
                    async with sem:
                        img = chunk["image_obj"]
                        page = await get_extractor().extract_data(
                            img,
                            role="figure_crop",
                            evidence_text=f"{chunk['title']}: {chunk['caption']}",
                            chunk_title=chunk.get("title", "")
                        )
                        _save_chunk_checkpoint(checkpoint_dir, chunk_key, page)
                        return page

                tasks = (
                    [bound_extract_text(c, idx) for idx, c in enumerate(text_chunks + caption_chunks)]
                    + [bound_extract_image(c, idx) for idx, c in enumerate(diagram_chunks)]
                )
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Filter out exceptions and log them
                extracted_chunks = []
                for chunk_idx, res_item in enumerate(results):
                    if isinstance(res_item, Exception):
                        print(f"Warning: Chunk {chunk_idx} failed extraction: {res_item}")
                    else:
                        extracted_chunks.append(res_item)

                for extracted_page in extracted_chunks:
                    if extracted_page and extracted_page.model_classification and extracted_page.model_classification.model_type != "not_applicable":
                        if final_document["model_classification"]["model_type"] == "not_applicable":
                            final_document["model_classification"] = extracted_page.model_classification.model_dump()

                    if extracted_page and extracted_page.model_context and not final_document["model_context"]:
                        final_document["model_context"] = extracted_page.model_context.model_dump(by_alias=True, exclude_none=True)
                    _merge_biological_basis(final_document, extracted_page)
                    _merge_model_structure(final_document, extracted_page)
                    if extracted_page and extracted_page.metabolic_pathways:
                        final_document["metabolic_pathways"].extend([m.model_dump(by_alias=True, exclude_none=True) for m in extracted_page.metabolic_pathways])

                    if extracted_page.parameter_blocks:
                        flat_params = flatten_parameter_blocks(extracted_page.parameter_blocks)
                        final_document["model_parameters"].extend(flat_params)
                    if extracted_page.observed_data:
                        final_document["observed_data"].extend([r.model_dump() for r in extracted_page.observed_data])
                    if extracted_page.simulated_data:
                        final_document["simulated_data"].extend([r.model_dump() for r in extracted_page.simulated_data])
                    if extracted_page.formulation_characterization:
                        final_document["formulation_characterization"].extend([m.model_dump() for m in extracted_page.formulation_characterization])
                    if extracted_page.qualitative_findings:
                        final_document["qualitative_findings"].extend([q.model_dump() for q in extracted_page.qualitative_findings])
                    if extracted_page.parameter_mentions_without_values:
                        final_document["parameter_mentions_without_values"].extend([m.model_dump() for m in extracted_page.parameter_mentions_without_values])
                    if extracted_page.table_evidence:
                        for te_item in extracted_page.table_evidence:
                            te_dict = te_item.model_dump()
                            if not any(e.get("table_id") == te_dict.get("table_id") for e in final_document["table_evidence"]):
                                final_document["table_evidence"].append(te_dict)

            if final_document["model_classification"]["model_type"] == "not_applicable" and doc_triage_type in ["pbpk", "compartmental", "nca"]:
                final_document["model_classification"]["model_type"] = doc_triage_type
                final_document["model_classification"]["evidence_quote"] = "Classified via Laya System-1 triage."

            final_document["laya_filter_summary"] = {
                "model_type_triage": doc_triage_type,
                "evaluated_chunks": laya_stats["evaluated"],
                "discarded_chunks": laya_stats["discarded"],
                "retained_chunks": laya_stats["retained"]
            }
            print_laya_summary(laya_stats, doc_triage_type)

            print("Step: Extracting Dosing Events from Methods...")
            try:
                doc = pymupdf.open(pdf_path)
                methods_text = ""
                for i in range(min(15, len(doc))):
                    methods_text += doc[i].get_text() + "\n"
                dosing_data = await get_extractor().extract_dosing_from_text(methods_text)
                if dosing_data and dosing_data.dosing:
                    final_document["dosing"] = [d.model_dump() for d in dosing_data.dosing]
            except Exception as e:
                print(f"  -> Failed to extract dosing: {e}")

            logger.info("Successfully completed XML extraction fast-path.")
            processed = post_process_document(final_document, pdf_path)
            if verify:
                from pk_pipeline.verifier import verify_document
                verify_document(processed)
            print("Step: Running Tier 2 Evaluation Pass...")
            try:
                judgments = await get_extractor().evaluate_extracted_model(json.dumps(processed))
                processed["evaluator_judgments"] = judgments.model_dump()
            except Exception as e:
                print(f"  -> Failed to run Tier 2 evaluation: {e}")
            return finalize_extracted_document(processed)

        if res.get("pdf_path") and res.get("source") in ["unpaywall", "semantic_scholar", "biorxiv", "medrxiv"]:
            print(f"  -> Switching from local PDF to Open Access PDF ({res['source']}): {res['pdf_path']}")
            if res.get("source_type") == "preprint":
                print(f"  -> ⚠️  Source is a PREPRINT — results will carry ingestion_source_type='preprint'.")
            pdf_path = res["pdf_path"]
    else:
        print("  -> Could not extract DOI or Title from local PDF. Proceeding with local file.")
    # -----------------------------
    
    # 1. Look for MinerU Output
    print("Step 1/3: Locating MinerU structured layout output...")
    logger.debug("Step 1: MinerU Parsing")
    
    pdf_dir = os.path.dirname(pdf_path)
    pdf_stem = os.path.splitext(os.path.basename(pdf_path))[0]
    
    mineru_json_path = None
    candidates = [
        os.path.join(pdf_dir, pdf_stem, "auto", "content_list.json"),
        os.path.join(pdf_dir, pdf_stem, "auto", "middle.json"),
        os.path.join(pdf_dir, "output", pdf_stem, "auto", "content_list.json"),
        os.path.join(pdf_dir, "output", pdf_stem, "auto", "middle.json"),
        os.path.join(pdf_dir, pdf_stem, "content_list.json"),
        os.path.join(pdf_dir, pdf_stem, "middle.json")
    ]
    for c in candidates:
        if os.path.exists(c):
            mineru_json_path = c
            break
            
    if not mineru_json_path:
        print(f"  -> MinerU structured output not found. Attempting PyMuPDF4LLM fallback extraction...")
        logger.debug("Falling back to PyMuPDF4LLM extraction.")
        
        import pymupdf4llm
        from PIL import Image, ImageDraw
        import io
        
        md_chunks = pymupdf4llm.to_markdown(pdf_path, page_chunks=True)
        pdf_doc = pymupdf.open(pdf_path)
        
        import torch
        t_processor, t_model = get_tatr()
        
        llm_payloads = []
        
        for i, chunk in enumerate(md_chunks):
            page_num = i + 1
            text = chunk.get("text", "")
            page = pdf_doc[i]
            has_image = len(page.get_images()) > 0
            
            pix = page.get_pixmap(matrix=pymupdf.Matrix(300/72, 300/72))
            full_page_img = Image.open(io.BytesIO(pix.tobytes())).convert("RGB")
            
            # --- TATR Detection on EVERY page ---
            inputs = t_processor(images=full_page_img, return_tensors="pt")
            with torch.no_grad():
                outputs = t_model(**inputs)
                
            target_sizes = torch.tensor([full_page_img.size[::-1]])
            results = t_processor.post_process_object_detection(outputs, threshold=0.7, target_sizes=target_sizes)[0]
            
            table_boxes = []
            for score, label, box in zip(results["scores"], results["labels"], results["boxes"]):
                if label.item() == 0:
                    table_boxes.append(box.tolist())
                    
            if table_boxes:
                # --- Crop each detected table box individually ---
                # Padding (in pixels at 300 DPI render) to retain sub-headers / footnotes
                PAD = 30
                img_w, img_h = full_page_img.size

                from pk_pipeline.ingestion.xml_parser import is_valid_pbpk_input_table, preprocess_table_dataframe
                pdf_tables = None
                try:
                    pdf_tables = page.find_tables()
                except Exception as e:
                    logger.debug(f"page.find_tables() note: {e}")

                for t_idx, box in enumerate(table_boxes):
                    x_min, y_min, x_max, y_max = box
                    # Apply padding, clamped to image bounds
                    cx0 = max(0, int(x_min) - PAD)
                    cy0 = max(0, int(y_min) - PAD)
                    cx1 = min(img_w, int(x_max) + PAD)
                    cy1 = min(img_h, int(y_max) + PAD)

                    table_crop_img = full_page_img.crop((cx0, cy0, cx1, cy1))

                    table_context = text  # fallback: native text from pymupdf4llm

                    # Try to match with PyMuPDF find_tables DataFrame
                    matched_preprocessed_md = None
                    if pdf_tables and pdf_tables.tables:
                        for p_tab in pdf_tables.tables:
                            try:
                                p_df = p_tab.to_pandas()
                                tab_rect = p_tab.bbox
                                caption_rect = pymupdf.Rect(0, max(0, tab_rect[1] - 80), page.rect.width, tab_rect[1])
                                footnotes_rect = pymupdf.Rect(0, tab_rect[3], page.rect.width, min(page.rect.height, tab_rect[3] + 120))
                                p_caption = page.get_text("text", clip=caption_rect).strip()
                                p_footnotes = page.get_text("text", clip=footnotes_rect).strip()

                                # Gate out non-input tables (sensitivity analysis, POD/HED, exposure)
                                if not is_valid_pbpk_input_table(p_caption, p_df.to_string()):
                                    print(f"  -> [Table Gating] Gated out non-input table on Page {page_num}: '{p_caption[:40]}'")
                                    continue

                                matched_preprocessed_md = preprocess_table_dataframe(p_df, caption=p_caption, footnotes=p_footnotes)
                                break
                            except Exception as e:
                                logger.debug(f"PyMuPDF find_tables error: {e}")

                    if use_wevisdoc:
                        try:
                            print(f"  -> [WeVisDoc-4B] Transcribing Page {page_num} Table {t_idx+1}/{len(table_boxes)} (crop {cx1-cx0}x{cy1-cy0}px)...")
                            wevisdoc_md = get_wevisdoc().parse_image(table_crop_img)
                            table_context = wevisdoc_md
                            wevisdoc_stats["pages_transcribed"] += 1
                            print(f"  -> [WeVisDoc-4B] Page {page_num} Table {t_idx+1} transcribed ({len(wevisdoc_md)} chars).")
                        except Exception as e:
                            print(f"  -> [WeVisDoc-4B] Notice: transcription fallback to native text ({e})")
                            table_context = text

                    if matched_preprocessed_md:
                        table_context = matched_preprocessed_md + "\n\n" + table_context

                    llm_payloads.append({
                        "role": "page_with_table",
                        "page": page_num,
                        "table_index": t_idx + 1,
                        "img_obj": table_crop_img,        # tight crop, not full page
                        "markdown_context": table_context,
                    })
            elif has_image:
                laya_stats["evaluated"] += 1
                keep, prob, mtype = get_laya().is_pk_relevant(text)
                if keep:
                    laya_stats["retained"] += 1
                    llm_payloads.append({
                        "role": "page_with_figure",
                        "page": page_num,
                        "img_obj": full_page_img,
                        "markdown_context": text,
                    })
                else:
                    laya_stats["discarded"] += 1
                    print(f"  -> [Laya Filter] Page {page_num} figure skipped (no PK model or parameters, p={prob:.2f})")
            elif len(text.strip()) > 50:
                laya_stats["evaluated"] += 1
                keep, prob, mtype = get_laya().is_pk_relevant(text)
                if keep:
                    laya_stats["retained"] += 1
                    llm_payloads.append({
                        "role": "narrative_xml",
                        "page": page_num,
                        "markdown_context": text.strip()
                    })
                else:
                    laya_stats["discarded"] += 1
                    print(f"  -> [Laya Filter] Page {page_num} narrative skipped (no PK parameters detected, p={prob:.2f})")
            
        print(f"  -> Separated {len(md_chunks)} pages into {len(llm_payloads)} distinct chunks. Running LLM extraction concurrently...")
        
        sem = asyncio.Semaphore(5)
        async def bound_extract(p, idx):
            role = p.get("role")
            if role == "page_with_table":
                t_idx = p.get("table_index", 1)
                chunk_title = f"Page {p['page']} Table {t_idx}"
                chunk_key = f"pdf_table_p{p['page']}_t{t_idx}_{idx}"
                cached = _load_chunk_checkpoint(checkpoint_dir, chunk_key)
                if cached:
                    n_p = sum(len(b.parameters) for b in cached.parameter_blocks or [])
                    print(f"  -> [Resume] Loaded cached extraction for '{chunk_title}' ({n_p} params)")
                    return cached
                async with sem:
                    table_evidence = await get_extractor().extract_table_evidence(
                        p["img_obj"],
                        markdown_context=p["markdown_context"],
                        chunk_title=chunk_title
                    )
                    page = await get_extractor().extract_data(
                        p["img_obj"],
                        role="table_crop",
                        evidence_text=p["markdown_context"],
                        chunk_title=chunk_title,
                        table_evidence=table_evidence
                    )
                    _save_chunk_checkpoint(checkpoint_dir, chunk_key, page)
                    return page
            elif role == "page_with_figure":
                chunk_title = f"Page {p['page']} figure"
                chunk_key = f"pdf_figure_p{p['page']}_{idx}"
                cached = _load_chunk_checkpoint(checkpoint_dir, chunk_key)
                if cached:
                    n_p = sum(len(b.parameters) for b in cached.parameter_blocks or [])
                    print(f"  -> [Resume] Loaded cached extraction for '{chunk_title}' ({n_p} params)")
                    return cached
                async with sem:
                    page = await get_extractor().extract_data(
                        p["img_obj"],
                        role="full_page",
                        evidence_text=p["markdown_context"],
                        chunk_title=chunk_title
                    )
                    _save_chunk_checkpoint(checkpoint_dir, chunk_key, page)
                    return page
            else:
                chunk_title = f"Page {p['page']} Text"
                chunk_key = f"pdf_narrative_p{p['page']}_{idx}"
                cached = _load_chunk_checkpoint(checkpoint_dir, chunk_key)
                if cached:
                    n_p = sum(len(b.parameters) for b in cached.parameter_blocks or [])
                    print(f"  -> [Resume] Loaded cached extraction for '{chunk_title}' ({n_p} params)")
                    return cached
                async with sem:
                    page = await get_extractor().extract_from_text(
                        p["markdown_context"],
                        role=role,
                        chunk_title=chunk_title
                    )
                    _save_chunk_checkpoint(checkpoint_dir, chunk_key, page)
                    return page
                    
        tasks = [bound_extract(p, idx) for idx, p in enumerate(llm_payloads)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        final_document = {
            "page_metadata": {"title": None, "authors": None, "journal": None, "year": None},
            "model_classification": {"model_type": "not_applicable", "evidence_quote": None},
            "model_context": None,
            "biological_basis": None,
            "model_structure": None,
            "metabolic_pathways": [],
            "model_parameters": [],
            "observed_data": [],
            "simulated_data": [],
            "formulation_characterization": [],
            "qualitative_findings": [],
            "parameter_mentions_without_values": [],
            "table_evidence": [],
        }
        
        for chunk_idx, res_item in enumerate(results):
            if isinstance(res_item, Exception):
                print(f"Warning: Page {chunk_idx+1} failed extraction: {res_item}")
            else:
                extracted_page = res_item
                if extracted_page and extracted_page.model_classification and extracted_page.model_classification.model_type != "not_applicable":
                    if final_document["model_classification"]["model_type"] == "not_applicable":
                        final_document["model_classification"] = extracted_page.model_classification.model_dump()
                if extracted_page and extracted_page.model_context and not final_document["model_context"]:
                    final_document["model_context"] = extracted_page.model_context.model_dump(by_alias=True, exclude_none=True)
                _merge_biological_basis(final_document, extracted_page)
                _merge_model_structure(final_document, extracted_page)
                if extracted_page and extracted_page.metabolic_pathways:
                    final_document["metabolic_pathways"].extend([m.model_dump(by_alias=True, exclude_none=True) for m in extracted_page.metabolic_pathways])
                if extracted_page and extracted_page.parameter_blocks:
                    flat_params = flatten_parameter_blocks(extracted_page.parameter_blocks)
                    final_document["model_parameters"].extend(flat_params)
                if extracted_page and extracted_page.observed_data:
                    final_document["observed_data"].extend([r.model_dump() for r in extracted_page.observed_data])
                if extracted_page and extracted_page.simulated_data:
                    final_document["simulated_data"].extend([r.model_dump() for r in extracted_page.simulated_data])
                if extracted_page and extracted_page.formulation_characterization:
                    final_document["formulation_characterization"].extend([m.model_dump() for m in extracted_page.formulation_characterization])
                if extracted_page and extracted_page.qualitative_findings:
                    final_document["qualitative_findings"].extend([q.model_dump() for q in extracted_page.qualitative_findings])
                if extracted_page and extracted_page.parameter_mentions_without_values:
                    final_document["parameter_mentions_without_values"].extend([m.model_dump() for m in extracted_page.parameter_mentions_without_values])
                if extracted_page and extracted_page.table_evidence:
                    final_document["table_evidence"].extend([t.model_dump() for t in extracted_page.table_evidence])
                    
        if final_document["model_classification"]["model_type"] == "not_applicable" and doc_triage_type in ["pbpk", "compartmental", "nca"]:
            final_document["model_classification"]["model_type"] = doc_triage_type
            final_document["model_classification"]["evidence_quote"] = "Classified via Laya System-1 triage."
            
        final_document["laya_filter_summary"] = {
            "model_type_triage": doc_triage_type,
            "evaluated_chunks": laya_stats["evaluated"],
            "discarded_chunks": laya_stats["discarded"],
            "retained_chunks": laya_stats["retained"]
        }
        print_laya_summary(laya_stats, doc_triage_type)

        final_document["wevisdoc_summary"] = {
            "enabled": use_wevisdoc,
            "pages_transcribed": wevisdoc_stats["pages_transcribed"]
        }
        print_wevisdoc_summary(wevisdoc_stats)

        logger.info("Successfully completed PyMuPDF fallback extraction.")
        processed = post_process_document(final_document, pdf_path)
        if verify:
            from pk_pipeline.verifier import verify_document
            verify_document(processed)
        return finalize_extracted_document(processed)
        
    print(f"Found MinerU structured output: {mineru_json_path}")
    
    with open(mineru_json_path, "r", encoding="utf-8") as f:
        mineru_data = json.load(f)
        
    # Handle both VLM backend (list of blocks) and Pipeline backend (dict with pdf_info)
    blocks = []
    if isinstance(mineru_data, list):
        blocks = mineru_data
    elif isinstance(mineru_data, dict) and "pdf_info" in mineru_data:
        for page in mineru_data["pdf_info"]:
            blocks.extend(page.get("blocks", []))
    else:
        # Generic fallback if structure differs slightly
        blocks = mineru_data.get("blocks", [])

    print(f"MinerU identified {len(blocks)} total document blocks.")

    # 2. Filter blocks for Tables and Figures using Relevance Keywords
    print("Step 2/3: Filtering for Pharmacokinetic tables and figures...")
    logger.debug("Step 2: Candidate Relevance Filtering")
    
    table_keywords = ["pharmacokinetic", "parameter", "pk", "clearance", "volume of distribution", "half-life"]
    if target_compounds:
        table_keywords.extend([c.lower() for c in target_compounds])
        
    diagram_keywords = ["pharmacokinetic", "model structure", "diagram", "mass balance", "pbpk"]
    
    pdf_doc = pymupdf.open(pdf_path)
    vlm_inputs = []
    
    def normalize_bbox(bbox, page_width, page_height):
        # MinerU bboxes might be [x0, y0, x1, y1]
        return bbox
        
    for block in blocks:
        block_type = block.get("type", "")
        if block_type not in ["table", "image", "figure"]:
            continue
            
        # Extract metadata flexibly
        # VLM backend might use 'page_idx', pipeline might use 'page_no'
        page_idx = block.get("page_idx", block.get("page_no", 0))
        if isinstance(page_idx, str):
            page_idx = int(page_idx)
            
        bbox = block.get("bbox")
        if not bbox or len(bbox) != 4:
            continue
            
        # Extract evidence text via PyMuPDF around the bbox
        try:
            page = pdf_doc[page_idx]
        except IndexError:
            # MinerU might 1-index pages?
            try:
                page = pdf_doc[page_idx - 1]
                page_idx -= 1
            except IndexError:
                continue
                
        # Get caption from MinerU or fallback to extracting text directly around bbox
        caption = block.get("text", block.get("caption", "")).lower()
        
        # PyMuPDF uses points. We assume MinerU bbox is in points. 
        # If it's normalized, this will fail, but we assume points for now.
        x0, y0, x1, y1 = bbox
        rect = pymupdf.Rect(x0, y0, x1, y1)
        evidence_text = page.get_text("text", clip=rect)
        
        # Expand rect slightly to capture nearby caption if MinerU missed it
        expanded_rect = pymupdf.Rect(max(0, x0 - 20), max(0, y0 - 40), x1 + 20, y1 + 40)
        surrounding_text = page.get_text("text", clip=expanded_rect).lower()
        
        search_text = caption + " " + surrounding_text
        
        if block_type == "table":
            if any(kw in search_text for kw in table_keywords):
                # We have a relevant table!
                # Render the crop at 300 DPI
                pix = page.get_pixmap(matrix=pymupdf.Matrix(300/72, 300/72), clip=rect)
                from PIL import Image
                import io
                img = Image.open(io.BytesIO(pix.tobytes()))
                
                vlm_inputs.append({
                    "img": img, 
                    "page_index": page_idx + 1, 
                    "role": "table_crop", 
                    "evidence_text": evidence_text
                })
                
        elif block_type in ["image", "figure"]:
            if any(kw in search_text for kw in diagram_keywords):
                # Render the crop at 300 DPI
                pix = page.get_pixmap(matrix=pymupdf.Matrix(300/72, 300/72), clip=rect)
                from PIL import Image
                import io
                crop_img = Image.open(io.BytesIO(pix.tobytes()))
                
                # We optionally send the full page as well if needed, but for now we send the precise crop
                # The user's plan: "Primary image: a fresh crop... Secondary image: full page (optional)"
                # To keep it simple and avoid modifying SGLang extractor signature, we pass the crop.
                vlm_inputs.append({
                    "img": crop_img, 
                    "page_index": page_idx + 1, 
                    "role": "figure_crop", 
                    "evidence_text": surrounding_text,
                    "chunk_title": caption[:50]
                })

    print(f"Queued {len(vlm_inputs)} filtered regions for LLM extraction.")
    
    # Save images to a debug folder for inspection
    debug_dir = os.path.join(pdf_dir, f"{pdf_stem}_vlm_inputs")
    os.makedirs(debug_dir, exist_ok=True)
    for idx, item in enumerate(vlm_inputs):
        img_path = os.path.join(debug_dir, f"candidate_{idx:02d}_page_{item['page_index']}_{item['role']}.png")
        item['img'].save(img_path)
    print(f"Saved {len(vlm_inputs)} VLM input images to: {debug_dir}")
    
    # 3. Extract data using SGLang with schema enforcement
    print(f"Step 3/3: Running VLM extraction on {len(vlm_inputs)} images concurrently...")
    logger.debug("Step 3: Targeted Extraction across multiple pages")
    
    final_document = {
        "page_metadata": {"title": None, "authors": None, "journal": None, "year": None},
        "model_classification": {"model_type": "not_applicable", "evidence_quote": None},
        "model_context": None,
        "biological_basis": None,
        "model_structure": None,
        "metabolic_pathways": [],
        "model_parameters": [],
        "observed_data": [],
        "simulated_data": [],
        "formulation_characterization": [],
        "qualitative_findings": [],
        "parameter_mentions_without_values": [],
        "dosing": []
    }
    # Use a Semaphore to limit concurrency to 2 pages at a time to prevent GPU OOM deadlocks
    sem = asyncio.Semaphore(2)
    async def bound_extract(item):
        async with sem:
            return await get_extractor().extract_data(item["img"], role=item["role"], evidence_text=item.get("evidence_text", ""))
            
    tasks = [bound_extract(item) for item in vlm_inputs]
    extracted_pages = await asyncio.gather(*tasks)
    
    for extracted_page in extracted_pages:
        
        # Merge metadata
        if extracted_page.page_metadata:
            pm = extracted_page.page_metadata
            if not final_document["page_metadata"]["title"] and pm.title:
                final_document["page_metadata"]["title"] = pm.title
            if not final_document["page_metadata"]["authors"] and pm.authors:
                final_document["page_metadata"]["authors"] = pm.authors
            if not final_document["page_metadata"]["journal"] and pm.journal:
                final_document["page_metadata"]["journal"] = pm.journal
            if not final_document["page_metadata"]["year"] and pm.year:
                final_document["page_metadata"]["year"] = pm.year
        
        # Merge model_classification (take the first meaningful one)
        if extracted_page.model_classification and extracted_page.model_classification.model_type != "not_applicable":
            if final_document["model_classification"]["model_type"] == "not_applicable":
                final_document["model_classification"] = extracted_page.model_classification.model_dump()
        
        # Merge model_context, biological_basis, structure, pathways
        if extracted_page.model_context and not final_document["model_context"]:
            final_document["model_context"] = extracted_page.model_context.model_dump(by_alias=True, exclude_none=True)
        _merge_biological_basis(final_document, extracted_page)
        _merge_model_structure(final_document, extracted_page)
        if extracted_page.metabolic_pathways:
            final_document["metabolic_pathways"].extend([m.model_dump(by_alias=True, exclude_none=True) for m in extracted_page.metabolic_pathways])
            
        # Aggregate all parameters
        if extracted_page.parameter_blocks:
            flat_params = flatten_parameter_blocks(extracted_page.parameter_blocks)
            final_document["model_parameters"].extend(flat_params)
        if extracted_page.observed_data:
            final_document["observed_data"].extend([r.model_dump() for r in extracted_page.observed_data])
        if extracted_page.simulated_data:
            final_document["simulated_data"].extend([r.model_dump() for r in extracted_page.simulated_data])
        if extracted_page.formulation_characterization:
            final_document["formulation_characterization"].extend([m.model_dump() for m in extracted_page.formulation_characterization])
        if extracted_page.qualitative_findings:
            final_document["qualitative_findings"].extend([q.model_dump() for q in extracted_page.qualitative_findings])
        if extracted_page.parameter_mentions_without_values:
            final_document["parameter_mentions_without_values"].extend([m.model_dump() for m in extracted_page.parameter_mentions_without_values])
            
    print("Step: Extracting Dosing Events from Methods...")
    try:
        doc = pymupdf.open(pdf_path)
        methods_text = ""
        for i in range(min(15, len(doc))):
            methods_text += doc[i].get_text() + "\n"
        dosing_data = await get_extractor().extract_dosing_from_text(methods_text)
        if dosing_data and dosing_data.dosing:
            final_document["dosing"] = [d.model_dump() for d in dosing_data.dosing]
    except Exception as e:
        print(f"  -> Failed to extract dosing: {e}")
    
    logger.info("Successfully completed extraction pipeline.")
    processed = post_process_document(final_document, pdf_path)
    if verify:
        from pk_pipeline.verifier import verify_document
        verify_document(processed)
        
    print("Step: Running Tier 2 Evaluation Pass...")
    try:
        judgments = await get_extractor().evaluate_extracted_model(json.dumps(processed))
        processed["evaluator_judgments"] = judgments.model_dump()
    except Exception as e:
        print(f"  -> Failed to run Tier 2 evaluation: {e}")
        
    return finalize_extracted_document(processed)

import time
import glob
import traceback

def main():
    parser = argparse.ArgumentParser(
        description="Run the PK Parameter Extraction Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single PDF
  python -m pk_pipeline.main paper.pdf

  # Multiple PDFs listed directly
  python -m pk_pipeline.main paper1.pdf paper2.pdf paper3.pdf

  # Entire directory (recursive)
  python -m pk_pipeline.main ./test_data/

  # Mix of directories and individual files
  python -m pk_pipeline.main ./batch1/ ./batch2/ extra.pdf

  # 3 documents processed concurrently (good for I/O-bound fetch steps)
  python -m pk_pipeline.main ./test_data/ --workers 3

  # With LLM verification on errors
  python -m pk_pipeline.main ./test_data/ --llm-verify
        """
    )
    parser.add_argument(
        "input_paths", type=str, nargs="+",
        help="PDF files, directories of PDFs, or a mix of both"
    )
    parser.add_argument("--compounds", nargs="+", help="Target compounds to steer search (e.g., PFOS PFOA)")
    parser.add_argument("--output_dir", type=str, default="output", help="Directory for output JSONs (default: 'output')")
    parser.add_argument(
        "--workers", type=int, default=2,
        help="Max PDFs processed concurrently (default: 2). "
             "Higher = faster for I/O-bound steps; lower = safer for VRAM."
    )
    parser.add_argument("--wevisdoc", action="store_true", default=True, help="Use WeVisDoc-4B for table OCR (default: True)")
    parser.add_argument("--no-wevisdoc", dest="wevisdoc", action="store_false", help="Disable WeVisDoc OCR")
    parser.add_argument("--force-pdf", action="store_true", default=False, help="Bypass XML resolution and force PDF+WeVisDoc OCR pipeline")
    parser.add_argument("--no-verify", action="store_true", default=False, help="Disable Tier 1 rule-based verification")
    parser.add_argument(
        "--llm-verify", action="store_true", default=False,
        help="Enable Tier 2 LLM critic (reviews flagged params, applies corrections in-place). Requires running SGLang server."
    )
    parser.add_argument(
        "--llm-verify-warnings", action="store_true", default=False,
        help="Also run Tier 2 critic on warning-level flags (not just errors)."
    )

    args = parser.parse_args()

    # ── Gather PDFs ──────────────────────────────────────────────────────────
    pdf_files = []
    for path in args.input_paths:
        if not os.path.exists(path):
            print(f"Warning: '{path}' does not exist. Skipping.")
            continue
        if os.path.isdir(path):
            found = sorted(glob.glob(os.path.join(path, "**", "*.pdf"), recursive=True))
            if not found:
                print(f"Warning: No PDF files found under '{path}'.")
            pdf_files.extend(found)
        else:
            if not path.lower().endswith(".pdf"):
                print(f"Warning: '{path}' is not a .pdf file. Skipping.")
                continue
            pdf_files.append(path)

    # Deduplicate, preserve order
    seen: set = set()
    pdf_files = [p for p in pdf_files if not (os.path.abspath(p) in seen or seen.add(os.path.abspath(p)))]

    if not pdf_files:
        print("Error: No valid PDF files found to process.")
        return

    n = len(pdf_files)
    print(f"\nFound {n} PDF(s) to process (workers={args.workers}):")
    for i, p in enumerate(pdf_files, 1):
        print(f"  {i:>3}. {os.path.basename(p)}")
    print()

    os.makedirs(args.output_dir, exist_ok=True)

    # ── Pre-load models once ─────────────────────────────────────────────────
    print("Booting AI models into GPU memory. This is a one-time 'cold start' penalty...")
    load_start = time.time()
    get_extractor()
    print(f"Models loaded in {time.time() - load_start:.1f}s.\n")

    # ── Async batch runner ────────────────────────────────────────────────────
    results_map: dict = {}
    lock = asyncio.Lock()   # protects completed/failed counters
    completed_count = [0]
    failed_count    = [0]

    async def process_one(pdf_path: str, sem: asyncio.Semaphore, position: int) -> None:
        async with sem:
            label    = f"[{position}/{n}]"
            basename = os.path.basename(pdf_path)
            print(f"\n{'─'*60}")
            print(f"  START  {label} {basename}")
            print(f"{'─'*60}")
            doc_start = time.time()
            try:
                result = await run_pipeline(
                    pdf_path,
                    args.compounds,
                    use_wevisdoc=args.wevisdoc,
                    force_pdf=args.force_pdf,
                    verify=not args.no_verify,
                    output_dir=args.output_dir,
                )

                # ── Save immediately ─────────────────────────────────────────
                base_name   = os.path.splitext(basename)[0]
                output_path = os.path.join(args.output_dir, f"{base_name}.json")
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)

                doc_time = time.time() - doc_start
                n_params = len(result.get("model_parameters", [])) if isinstance(result, dict) else "?"
                print(f"  DONE   {label} {basename}  |  {n_params} params  |  {doc_time:.1f}s  ->  {output_path}")

                # ── Optional Tier 2 LLM critic ───────────────────────────────
                if args.llm_verify and isinstance(result, dict):
                    tier1_clean = (result.get("verification") or {}).get("clean", True)
                    if tier1_clean:
                        print(f"  [T2]   {label} Tier 1 clean — LLM critic skipped.")
                    else:
                        err_n = (result.get("verification") or {}).get("error_count", 0)
                        print(f"  [T2]   {label} Running LLM critic on {err_n} error(s)...")
                        from pk_pipeline.verifier import verify_document_with_llm
                        _, llm_sum = await verify_document_with_llm(
                            result,
                            verbose=False,
                            include_warnings=args.llm_verify_warnings,
                        )
                        refresh_parameter_views(result)
                        result = finalize_extracted_document(result)
                        with open(output_path, "w", encoding="utf-8") as f:
                            json.dump(result, f, indent=2, ensure_ascii=False)
                        print(
                            f"  [T2]   {label} {llm_sum.get('patched',0)} patched, "
                            f"{llm_sum.get('rejected',0)} rejected in "
                            f"{llm_sum.get('elapsed_s',0):.1f}s. Re-saved."
                        )

                async with lock:
                    results_map[pdf_path] = result
                    completed_count[0]   += 1

            except Exception as exc:
                elapsed = time.time() - doc_start
                print(f"  FAIL   {label} {basename}  |  {elapsed:.1f}s  |  {exc}")
                logger.debug(traceback.format_exc())
                async with lock:
                    results_map[pdf_path] = exc
                    failed_count[0]      += 1

    async def run_batch() -> None:
        sem   = asyncio.Semaphore(args.workers)
        tasks = [
            process_one(pdf_path, sem, i)
            for i, pdf_path in enumerate(pdf_files, 1)
        ]
        await asyncio.gather(*tasks)

    # ── Execute ───────────────────────────────────────────────────────────────
    batch_start = time.time()
    try:
        asyncio.run(run_batch())
    except KeyboardInterrupt:
        print("\nInterrupted by user.")

    batch_time = time.time() - batch_start

    # ── Summary ───────────────────────────────────────────────────────────────
    total_params   = sum(len(r.get("model_parameters", [])) for r in results_map.values() if isinstance(r, dict))
    total_laya     = sum((r.get("laya_filter_summary") or {}).get("discarded_chunks", 0) for r in results_map.values() if isinstance(r, dict))
    total_wevisdoc = sum((r.get("wevisdoc_summary") or {}).get("pages_transcribed", 0) for r in results_map.values() if isinstance(r, dict))

    print(f"\n{'='*60}")
    print(f"  BATCH COMPLETE")
    print(f"{'='*60}")
    print(f"  PDFs:        {n}  (succeeded: {completed_count[0]}, failed: {failed_count[0]})")
    print(f"  Total time:  {batch_time:.1f}s  (avg {batch_time/n:.1f}s/doc, workers={args.workers})")
    print(f"  Total params extracted: {total_params}")
    if total_laya:
        print(f"  Laya saved:  ~{total_laya * 25}s VLM compute ({total_laya} chunks skipped)")
    if total_wevisdoc:
        print(f"  WeVisDoc:    {total_wevisdoc} table pages OCR'd")
    print(f"  Output dir:  {os.path.abspath(args.output_dir)}")
    if failed_count[0]:
        print(f"\n  Failed documents:")
        for p, r in results_map.items():
            if isinstance(r, Exception):
                print(f"    x {os.path.basename(p)}: {r}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
