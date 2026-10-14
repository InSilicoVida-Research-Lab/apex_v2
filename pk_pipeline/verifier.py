"""
pk_pipeline/verifier.py
=======================
Two-tier post-extraction verification system.

Tier 1 — Deterministic Rule Engine (~0-5ms, zero GPU cost)
    Fast Python rules that flag obvious anomalies:
    - Biologically implausible values
    - Missing required fields
    - Unit consistency issues
    - Duplicate/conflicting entries
    - Species/compound cross-contamination

Tier 2 — Optional LLM Critic (async, only on flagged entries)
    Uses a smaller/faster LLM to review only the flagged parameters.
    This is OPTIONAL and OFF by default. It does NOT block the main pipeline.

Design Principle: Verification adds near-ZERO latency.
    - Tier 1 is pure Python loops — completed in <10ms for any realistic document.
    - Tier 2 is async: results are appended to the output as `verification_report`
      and never block the main JSON write.
"""

from __future__ import annotations

import re
import time
import logging
from typing import Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger("pk_pipeline")

# ---------------------------------------------------------------------------
# Biological plausibility bounds for common PK parameter symbols/names
# Each entry: (name_fragments, unit_fragments, lo, hi)
# Values outside [lo, hi] get flagged as suspicious (not necessarily wrong).
# ---------------------------------------------------------------------------
_PLAUSIBILITY_RULES: list[tuple[list[str], list[str], float, float]] = [
    # Volumes (L or L/kg)
    (["volume", "vd", "vc", "vp", "vcc", "vpc"],      ["l/kg", "l kg"],   0.0001, 500.0),
    (["volume", "vd", "vc", "vp", "vcc", "vpc"],      ["l", "litre"],     0.0001, 500.0),
    # Clearances (L/h or L/h/kg)
    (["clearance", "cl", "clr", "clh", "q"],          ["l/h", "l/day"],   0.0,   5000.0),
    (["clearance", "cl", "clr", "clh", "q"],          ["ml/min"],         0.0,   5000.0),
    # Half-lives (h)
    (["half", "t1/2", "t1/2", "t_half", "thalf"],     ["h", "hr", "day"], 0.001, 50000.0),
    # Rate constants (1/h)
    (["rate", "ka", "kel", "k12", "k21", "k10"],      ["1/h", "h-1"],     0.0,   100.0),
    # Bioavailability (unitless fraction)
    (["bioavailability", "fraction", "fa", "fg"],     ["%", "fraction"],  0.0,   100.0),
    # Protein binding (fraction bound)
    (["binding", "fu", "unbound", "fraction unbound"],["%", "fraction"],  0.0,   100.0),
    # AUC (microgram*h/mL)
    (["auc"],                                          ["ug", "ng", "microg"], 0.0, 1e8),
    # Cmax (ug/mL or ng/mL)
    (["cmax", "c_max", "peak"],                        ["ug", "ng", "microg"], 0.0, 1e6),
]

# Known common PK parameter abbreviations for symbol completeness check
_KNOWN_SYMBOLS = {
    "vd", "vc", "vp", "vpc", "vcc", "cl", "clr", "clh", "q",
    "ka", "kel", "k10", "k12", "k21", "t1/2", "auc", "cmax",
    "tmax", "fu", "fa", "fg", "mrt", "ke", "kabs", "km", "vmax",
    "clint", "clp", "clm", "clrenal", "clhepatic"
}


# ---------------------------------------------------------------------------
# Verification result dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ParameterFlag:
    """Represents a single verification flag on one parameter."""
    param_index: int
    param_name: str
    severity: str          # "warning" | "error"
    rule: str              # Short rule ID
    message: str           # Human-readable explanation
    suggested_fix: Optional[str] = None


@dataclass
class VerificationReport:
    """Full verification report attached to the document output."""
    tier: int                              # 1 = rule-based only, 2 = +LLM critic
    elapsed_ms: float = 0.0
    total_parameters: int = 0
    parameters_with_flags: int = 0        # distinct parameters that have at least one flag
    total_flags: int = 0                  # total number of individual flag instances
    error_count: int = 0
    warning_count: int = 0
    flags: list = field(default_factory=list)
    summary: str = ""
    clean: bool = True                    # True if no errors/warnings found

    # Keep flagged_count as a property for backward compat
    @property
    def flagged_count(self) -> int:
        return self.total_flags

    def to_dict(self) -> dict:
        return {
            "tier": self.tier,
            "elapsed_ms": round(self.elapsed_ms, 2),
            "total_parameters": self.total_parameters,
            "parameters_with_flags": self.parameters_with_flags,
            "total_flags": self.total_flags,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "clean": self.clean,
            "summary": self.summary,
            "flags": [
                {
                    "param_index": f.param_index,
                    "param_name": f.param_name,
                    "severity": f.severity,
                    "rule": f.rule,
                    "message": f.message,
                    "suggested_fix": f.suggested_fix,
                }
                for f in self.flags
            ],
        }


# ---------------------------------------------------------------------------
# Helpers for Table and Cell Normalization / Matching
# ---------------------------------------------------------------------------

def normalize_text(text: Optional[str]) -> str:
    """Normalize text for reliable string comparison."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", str(text).strip().lower())

def normalize_table_id(s: Optional[str]) -> str:
    """Normalize table ID (e.g. 'Table 1: ...' -> 'table1', 'Table S1' -> 'tables1')."""
    if not s:
        return ""
    norm = re.sub(r"\s+", "", str(s).strip().lower())
    m = re.match(r"(table\s*s?\d+)", norm)
    if m:
        return m.group(1).replace(" ", "")
    return norm

def find_matched_cell(param: dict, te: dict) -> Optional[dict]:
    """Find the specific TableCell in TableEvidence corresponding to an extracted parameter."""
    if not te:
        return None
    cells = te.get("cells", [])
    if not cells:
        return None

    rows_by_id = {r.get("row_id"): r for r in te.get("rows", []) if r.get("row_id")}
    cols_by_id = {c.get("column_id"): c for c in te.get("columns", []) if c.get("column_id")}

    def format_cell_info(c: dict) -> dict:
        r_obj = rows_by_id.get(c.get("row_id"), {})
        c_obj = cols_by_id.get(c.get("column_id"), {})
        return {
            "cell_id": c.get("cell_id"),
            "row_id": c.get("row_id"),
            "row_path": r_obj.get("path", []),
            "column_id": c.get("column_id"),
            "column_path": c_obj.get("path", []),
            "text": c.get("text"),
            "numeric_value": c.get("numeric_value"),
            "unit": c.get("unit"),
            "qualifier": c.get("qualifier"),
            "uncertainty_text": c.get("uncertainty_text")
        }

    prov = param.get("provenance", {}) or {}
    qdata = param.get("quantitative_data", {}) or {}
    ctx = param.get("context", {}) or {}
    val = qdata.get("value")
    val_text = str(qdata.get("value_text") or "").strip()
    param_name = (param.get("parameter_name_original") or param.get("symbol_original") or "").lower()
    compound = (ctx.get("compound") or "").lower()

    # 1. Match by cell_id if present
    target_cell_id = prov.get("cell_id")
    if target_cell_id:
        for c in cells:
            if c.get("cell_id") == target_cell_id:
                return format_cell_info(c)

    # 2. Match by row_id and column_id if present
    target_row_id = prov.get("row_id")
    target_col_id = prov.get("column_id")
    if target_row_id and target_col_id:
        for c in cells:
            if c.get("row_id") == target_row_id and c.get("column_id") == target_col_id:
                return format_cell_info(c)

    # 3. Match by numeric value or text
    candidates = []
    for c in cells:
        c_val = c.get("numeric_value")
        c_text = str(c.get("text") or "").strip()
        val_match = False
        if val is not None and c_val is not None:
            if abs(c_val - val) <= abs(val) * 0.03 + 1e-6:
                val_match = True
        elif val_text and (val_text in c_text or c_text in val_text):
            val_match = True

        if val_match:
            candidates.append(c)

    if not candidates:
        return None

    if len(candidates) == 1:
        return format_cell_info(candidates[0])

    # Rank candidates by row/column match against param context
    best_c = candidates[0]
    best_score = -1
    for c in candidates:
        info = format_cell_info(c)
        score = 0
        r_text = " ".join([str(x).lower() for x in info["row_path"]])
        c_text = " ".join([str(x).lower() for x in info["column_path"]])
        if compound:
            if compound in c_text:
                score += 5
            elif compound in r_text:
                score += 3
        if param_name:
            if param_name in r_text:
                score += 5
            elif param_name in c_text:
                score += 3
        prov_r_path = " ".join([str(x).lower() for x in prov.get("row_path", [])])
        if prov_r_path and prov_r_path in r_text:
            score += 4
        prov_c_path = " ".join([str(x).lower() for x in prov.get("column_path", [])])
        if prov_c_path and prov_c_path in c_text:
            score += 4

        if score > best_score:
            best_score = score
            best_c = c

    return format_cell_info(best_c)


# ---------------------------------------------------------------------------
# Tier 1: Deterministic Rule Engine
# ---------------------------------------------------------------------------

class Tier1Verifier:
    """
    Pure-Python rule engine. Runs in <5ms for any document.
    No GPU, no network, no model loading.
    """

    def verify(self, document: dict) -> VerificationReport:
        t0 = time.monotonic()
        params: list[dict] = document.get("model_parameters", [])
        table_evidences: list[dict] = document.get("table_evidence", [])
        flags: list[ParameterFlag] = []
        
        # Build TableEvidence lookup with dual indexing (raw ID and normalized ID)
        table_evidence_dict = {}
        for te in table_evidences:
            t_id = te.get("table_id")
            if t_id:
                table_evidence_dict[t_id] = te
                table_evidence_dict[normalize_table_id(t_id)] = te
        
        # Pre-compute compound distribution per table to detect cross-contamination anomalies
        table_compounds = {}
        for i, p in enumerate(params):
            cmpd = (p.get("context") or {}).get("compound")
            tbl = (p.get("provenance") or {}).get("source_table")
            if cmpd and tbl:
                if tbl not in table_compounds:
                    table_compounds[tbl] = {}
                table_compounds[tbl][cmpd] = table_compounds[tbl].get(cmpd, 0) + 1
        
        def get_composite_key(p_dict: dict) -> tuple:
            ctx = p_dict.get("context") or {}
            species = (ctx.get("species") or "").lower()
            organ = (ctx.get("organ") or "").lower()
            formulation_raw = ctx.get("formulation")
            if formulation_raw is None:
                formulations = ()
            elif isinstance(formulation_raw, str):
                formulations = (formulation_raw.lower(),)
            else:
                formulations = tuple(sorted(str(x).lower() for x in formulation_raw))
            compound = (ctx.get("compound") or "").lower()
            life_stage = (ctx.get("life_stage") or "").lower()
            population = (ctx.get("population") or "").lower()
            
            p_class = (p_dict.get("parameter_class") or "").lower()
            p_subclass = (p_dict.get("parameter_subclass") or "").lower()
            p_name = (p_dict.get("parameter_name_standardized") or p_dict.get("parameter_name_original") or "").lower()
            source_table = ((p_dict.get("provenance") or {}).get("source_table") or "").lower()
            
            return (compound, species, life_stage, population, formulations, p_class, p_subclass, organ, p_name, source_table)

        seen_keys = {}

        for i, p in enumerate(params):
            name_orig = p.get("parameter_name_original", "")
            name_std = p.get("parameter_name_standardized", "")
            name = name_std or name_orig or ""
            symbol = p.get("symbol_original", "") or p.get("symbol_standardized", "") or ""
            ctx = p.get("context", {}) or {}
            qdata = p.get("quantitative_data", {}) or {}
            prov = p.get("provenance", {}) or {}

            # Rule 1: Missing parameter_name
            if not name or name.strip() == "":
                flags.append(ParameterFlag(
                    param_index=i, param_name="<UNNAMED>",
                    severity="error", rule="MISSING_NAME",
                    message="parameter_name_original is empty or null.",
                    suggested_fix="Provide a descriptive name or the printed symbol."
                ))

            # Rule 2: Missing compound
            compound = ctx.get("compound")
            p_class = (p.get("parameter_class") or "").lower()
            is_physiological = "physiological" in p_class
            
            if not compound and not is_physiological:
                flags.append(ParameterFlag(
                    param_index=i, param_name=name,
                    severity="warning", rule="MISSING_COMPOUND",
                    message="context.compound is null for a non-physiological parameter; cannot attribute it to a chemical.",
                    suggested_fix="Infer from paper title/abstract or mark as unknown."
                ))

            # Rule 3: Missing unit when value exists
            unit = qdata.get("unit_standardized") or qdata.get("unit_original")
            value_raw = qdata.get("value")
            value = None
            if value_raw is not None:
                try:
                    value = float(value_raw)
                except (ValueError, TypeError):
                    pass
            value_text = qdata.get("value_text")
            if value_text and not unit:
                flags.append(ParameterFlag(
                    param_index=i, param_name=name,
                    severity="warning", rule="MISSING_UNIT",
                    message=f"value_text='{value_text}' present but unit is null.",
                    suggested_fix="Check if unit appears in a table column header."
                ))

            # Rule 4: value vs value_text mismatch (>5% relative error)
            if value is not None and value_text:
                try:
                    # Handle unicode minus sign and strip trailing letter-footnotes
                    text_normalized = str(value_text).replace("−", "-").split()[0]
                    cleaned = re.sub(r"[^0-9.\-eE+]", "", text_normalized)
                    if cleaned and cleaned != "-":
                        parsed = float(cleaned)
                        if abs(parsed - value) > abs(parsed) * 0.05 + 1e-9:
                            flags.append(ParameterFlag(
                                param_index=i, param_name=name,
                                severity="warning", rule="VALUE_MISMATCH",
                                message=f"value={value} does not match parsed value_text='{value_text}' ({parsed}).",
                                suggested_fix="Re-check the source cell."
                            ))
                except (ValueError, IndexError):
                    pass  # value_text has letters/qualifiers — expected

            # Rule 5: Biologically implausible numeric value
            if value is not None and unit:
                unit_lc = unit.lower().strip()
                name_lc = name.lower()
                sym_lc = symbol.lower()
                for name_frags, unit_frags, lo, hi in _PLAUSIBILITY_RULES:
                    # Use regex with word boundaries for name fragments to avoid 'q' matching 'frequency'
                    name_hit = any(
                        re.search(rf'\b{re.escape(f)}\b', name_lc) or re.search(rf'\b{re.escape(f)}\b', sym_lc)
                        for f in name_frags
                    )
                    unit_hit = any(f in unit_lc for f in unit_frags)
                    if name_hit and unit_hit:
                        if not (lo <= value <= hi):
                            flags.append(ParameterFlag(
                                param_index=i, param_name=name,
                                severity="warning", rule="IMPLAUSIBLE_VALUE",
                                message=(
                                    f"value={value} {unit} is outside the expected "
                                    f"plausible range [{lo}, {hi}] for '{name}'."
                                ),
                                suggested_fix=(
                                    "Verify unit conversion or check for a magnitude "
                                    "error (e.g. mL vs L)."
                                )
                            ))
                        break

            # Rule 5.5: Deterministic Unit Validation based on subclass
            p_subclass = (p.get("parameter_subclass") or "").lower()
            unit_lc = (unit or "").lower()
            
            unit_dictionary = {
                "blood_flow_fraction": ["dimensionless", "fraction", "ratio", "none"],
                "organ_volume_fraction": ["dimensionless", "fraction", "ratio", "none"],
                "partition_coefficient": ["dimensionless", "fraction", "ratio", "none"],
                "fraction_unbound": ["dimensionless", "fraction", "ratio", "none"],
                "cardiac_output": ["l/h", "l/h/kg^0.74", "l/h/kg 0.74", "l/h/kg^0.75", "l/h/kg 0.75", "l/min", "ml/min"],
                "clearance": ["l/h", "ml/min", "μl/h/kg^0.25", "ml/min/kg", "l/h/kg", "l/h/kg^0.74", "l/h/kg 0.74", "l/h/kg^0.75", "l/h/kg 0.75"],
                "rate_constant": ["1/h", "1/min", "h-1", "min-1", "h^-1", "min^-1", "1/h/kg^0.25"],
                "distribution_rate": ["1/h", "1/min", "h-1", "min-1", "h^-1", "min^-1"],
                "absorption_rate": ["1/h", "1/min", "h-1", "min-1", "h^-1", "min^-1"],
                "compartment_volume": ["l", "ml", "l/kg", "ml/kg"],
                "organ_volume": ["l", "ml", "l/kg", "ml/kg", "dimensionless", "fraction", "ratio", "none"],
                "vmax": ["nmol/h/kg^0.75", "pmol/min/mg", "nmol/min/mg", "mg/h", "mg/h/kg", "umol/h/kg", "μmol/h/kg"],
                "km": ["μmol/l", "umol/l", "mg/l", "ng/ml", "μm", "um"]
            }
            
            for required_subclass, allowed_units in unit_dictionary.items():
                if required_subclass in p_subclass:
                    is_valid = False
                    if not unit_lc and "dimensionless" in allowed_units:
                        is_valid = True
                    elif unit_lc and any(allowed in unit_lc for allowed in allowed_units):
                        is_valid = True
                        
                    if not is_valid:
                        flags.append(ParameterFlag(
                            param_index=i, param_name=name,
                            severity="error", rule="INVALID_UNIT_DIMENSION",
                            message=f"Subclass '{p_subclass}' expects dimensional signature like {allowed_units}, but VLM assigned '{unit}'.",
                            suggested_fix="Strip hallucinated unit or force standard dimensional unit."
                        ))
                    break

            # Rule 6: Negative value for inherently positive parameters
            if value is not None and value < 0:
                name_lc = name.lower()
                sym_lc = symbol.lower()
                source_quote = prov.get("source_quote", "").lower()
                inherently_positive = [
                    "volume", "clearance", "half", "auc", "cmax", "rate constant"
                ]
                # If it comes from a sensitivity analysis table, negative coefficients are valid
                is_sensitivity = "sensitivity" in source_quote
                
                if any(k in name_lc or k in sym_lc for k in inherently_positive) and not is_sensitivity:
                    flags.append(ParameterFlag(
                        param_index=i, param_name=name,
                        severity="error", rule="NEGATIVE_VALUE",
                        message=f"value={value} is negative for a parameter that must be positive.",
                        suggested_fix="Check for sign errors or inverted table row."
                    ))

            # Rule 7: Missing uncertainty bound
            unc = qdata.get("uncertainty") or {}
            lower = unc.get("lower")
            upper = unc.get("upper")

            if (lower is not None and upper is None) or (lower is None and upper is not None):
                flags.append(ParameterFlag(
                    param_index=i, param_name=name,
                    severity="warning", rule="INCOMPLETE_UNCERTAINTY",
                    message="One uncertainty/CI bound is populated but the other is null.",
                    suggested_fix="Check if the source has a complete range or if this is a single +/- value."
                ))

            # Rule 8: Placeholder compound strings
            if compound:
                bad_placeholders = [
                    "compound", "chemical", "drug", "substance", "analyte", "xxx", "tbd"
                ]
                if any(bp in compound.lower() for bp in bad_placeholders):
                    flags.append(ParameterFlag(
                        param_index=i, param_name=name,
                        severity="warning", rule="PLACEHOLDER_COMPOUND",
                        message=f"context.compound='{compound}' looks like a placeholder.",
                        suggested_fix="Replace with the actual chemical name from the paper."
                    ))

            # Rule 8.5: Minority Compound in Table (Cross-contamination check)
            tbl = prov.get("source_table")
            if compound and tbl:
                cmpd_counts = table_compounds.get(tbl, {})
                if len(cmpd_counts) > 1:
                    total = sum(cmpd_counts.values())
                    count = cmpd_counts[compound]
                    # If this compound is less than 15% of the table's parameters, flag as suspicious
                    if count / total < 0.15:
                        flags.append(ParameterFlag(
                            param_index=i, param_name=name,
                            severity="warning", rule="MINORITY_COMPOUND_IN_TABLE",
                            message=f"Compound '{compound}' is a minority in '{tbl}' (only {count}/{total} parameters). Possible table/compound cross-contamination.",
                            suggested_fix="Verify if the table genuinely contains multiple compounds or if a footnote caused hallucination."
                        ))

            # Rule 8.6: Missing provenance hierarchy
            row_path = prov.get("row_path", [])
            col_path = prov.get("column_path", [])
            
            if tbl and not row_path and not col_path:
                flags.append(ParameterFlag(
                    param_index=i, param_name=name,
                    severity="warning", rule="MISSING_TABLE_HIERARCHY",
                    message=f"Parameter belongs to '{tbl}' but row_path and column_path are empty.",
                    suggested_fix="Ensure the extraction model is correctly capturing the table cell hierarchy."
                ))
                
            # Rule 8.7: Hierarchy Consistency Check (Compound/Column Conflict)
            all_path_text = " ".join([str(x) for x in (row_path or []) + (col_path or [])]).lower()
            norm_tbl = normalize_table_id(tbl) if tbl else None
            te = (table_evidence_dict.get(tbl) or table_evidence_dict.get(norm_tbl)) if tbl else None
            te_title = (te.get("title") or "").lower() if te else ""
            te_subjects = [str(c).lower() for c in (te.get("subject_compounds") or [])] if te else []
            in_table_meta = bool(compound and (compound.lower() in te_title or any(compound.lower() in sc for sc in te_subjects)))

            if compound and all_path_text and compound.lower() not in all_path_text and not in_table_meta:
                flags.append(ParameterFlag(
                    param_index=i, param_name=name,
                    severity="error", rule="COMPOUND_COLUMN_CONFLICT",
                    message=f"Compound '{compound}' does not appear in the row or column path ({row_path}, {col_path}).",
                    suggested_fix="Check if the compound is legitimately inferred from the table title, or if this is a cross-table leakage hallucination."
                ))

            # Rule 8.8: Source Table Evidence & Cell-Level Verification
            if tbl:
                if not te:
                    flags.append(ParameterFlag(
                        param_index=i, param_name=name,
                        severity="error", rule="SOURCE_TABLE_EVIDENCE_MISSING",
                        message=f"Parameter cites source_table='{tbl}', but no TableEvidence was reconstructed for '{tbl}'.",
                        suggested_fix="Ensure this table was captured in document processing or check for table numbering typos."
                    ))
                elif te.get("evidence_status") == "failed":
                    flags.append(ParameterFlag(
                        param_index=i, param_name=name,
                        severity="error", rule="SOURCE_TABLE_RECONSTRUCTION_FAILED",
                        message=f"Parameter cites source_table='{tbl}', but table reconstruction failed ({te.get('error')}).",
                        suggested_fix="Re-run table reconstruction or review the source table image manually."
                    ))
                else:
                    te_subject_compounds = [normalize_text(c) for c in te.get("subject_compounds", []) if c]
                    te_footnote_compounds = [normalize_text(c) for c in te.get("footnote_compounds", []) if c]
                    te_referenced_compounds = [normalize_text(c) for c in te.get("referenced_compounds", []) if c]

                    if compound:
                        cmpd_norm = normalize_text(compound)
                        if te_subject_compounds and cmpd_norm not in te_subject_compounds:
                            if cmpd_norm in te_footnote_compounds:
                                flags.append(ParameterFlag(
                                    param_index=i, param_name=name,
                                    severity="warning", rule="FOOTNOTE_ONLY_COMPOUND",
                                    message=f"Compound '{compound}' appears only in footnotes of '{tbl}' (subjects: {te.get('subject_compounds')}).",
                                    suggested_fix="Verify if parameter is legitimately an assumed/footnote value or a cross-table error."
                                ))
                            elif cmpd_norm in te_referenced_compounds:
                                flags.append(ParameterFlag(
                                    param_index=i, param_name=name,
                                    severity="warning", rule="REFERENCED_ONLY_COMPOUND",
                                    message=f"Compound '{compound}' appears only as a reference/comparison in '{tbl}' (subjects: {te.get('subject_compounds')}).",
                                    suggested_fix="Verify if parameter belongs to the modeled compound rather than an external reference."
                                ))
                            else:
                                flags.append(ParameterFlag(
                                    param_index=i, param_name=name,
                                    severity="error", rule="SOURCE_TABLE_COMPOUND_MISMATCH",
                                    message=f"Compound '{compound}' does not appear in source table '{tbl}' (subjects: {te.get('subject_compounds')}).",
                                    suggested_fix="Re-attribute parameter to the correct compound or table."
                                ))

                    te_species = [normalize_text(s) for s in te.get("species", []) if s]
                    species = ctx.get("species")
                    if species and te_species:
                        spec_norm = normalize_text(species)
                        if spec_norm not in te_species:
                            flags.append(ParameterFlag(
                                param_index=i, param_name=name,
                                severity="error", rule="SOURCE_TABLE_SPECIES_MISMATCH",
                                message=f"Species '{species}' does not appear in source table '{tbl}' (found species: {te.get('species')}).",
                                suggested_fix="Check if species was mistakenly carried over from another table."
                            ))

                    # Cell-level validation: parameter -> row, compound -> column, value -> cell
                    matched_cell = find_matched_cell(p, te)
                    if matched_cell:
                        c_val = matched_cell.get("numeric_value")
                        if value is not None and c_val is not None:
                            abs_diff = abs(c_val - value)
                            rel_tol = abs(c_val) * 0.05 + 1e-4
                            if abs_diff > rel_tol and abs_diff > 0.005:
                                flags.append(ParameterFlag(
                                    param_index=i, param_name=name,
                                    severity="error", rule="CELL_VALUE_MISMATCH",
                                    message=f"Extracted value {value} differs from matched source cell ({matched_cell.get('cell_id')}) value {c_val}.",
                                    suggested_fix=f"Use cell value {c_val}."
                                ))

                        col_path_text = " ".join([str(x).lower() for x in matched_cell.get("column_path", [])])
                        if compound:
                            cmpd_norm = normalize_text(compound)
                            other_subjects = [sc for sc in te_subject_compounds if sc != cmpd_norm]
                            if any(other in col_path_text for other in other_subjects) and cmpd_norm not in col_path_text:
                                flags.append(ParameterFlag(
                                    param_index=i, param_name=name,
                                    severity="error", rule="CELL_COMPOUND_MISALIGNMENT",
                                    message=f"Context mismatch: Parameter assigns compound '{compound}', but matched cell column path is {matched_cell.get('column_path')}.",
                                    suggested_fix="Re-attribute parameter to the column's compound."
                                ))
                    elif te.get("cells") and value is not None:
                        is_inherited = (
                            prov.get("evidence_directness") == "inherited_cross_species"
                            or "held constant" in str(prov.get("source_quote", "")).lower()
                            or "held constant" in str(prov.get("derivation", "")).lower()
                        )
                        if not is_inherited:
                            flags.append(ParameterFlag(
                                param_index=i, param_name=name,
                                severity="error", rule="CELL_NOT_FOUND_IN_SOURCE_TABLE",
                                message=f"Value {value} ({value_text}) for '{name}' could not be matched to any cell in source table '{tbl}'.",
                                suggested_fix="Check if value was taken from a different table or narrative text."
                            ))

            # Rule 9: High-confidence entry missing source_quote
            source_quote = prov.get("source_quote")
            if not source_quote and prov.get("confidence") == "high":
                flags.append(ParameterFlag(
                    param_index=i, param_name=name,
                    severity="warning", rule="MISSING_QUOTE_HIGH_CONF",
                    message=(
                        "confidence='high' but source_quote is null; "
                        "high confidence requires a direct quote."
                    ),
                    suggested_fix="Add verbatim text from the source cell or sentence."
                ))

            # Rule 10: Semantic composite key duplicate/conflict detection
            comp_key = get_composite_key(p)
            if comp_key in seen_keys:
                j, val_prev = seen_keys[comp_key]
                if value is not None and val_prev is not None and abs(value - val_prev) < 1e-9:
                    flags.append(ParameterFlag(
                        param_index=i, param_name=name,
                        severity="warning", rule="DUPLICATE_ENTRY",
                        message=f"Exact semantic duplicate of parameter at index {j} (key: {comp_key}, value={value}).",
                        suggested_fix="Deduplicate; keep only the entry with higher provenance confidence."
                    ))
                else:
                    flags.append(ParameterFlag(
                        param_index=i, param_name=name,
                        severity="error", rule="CONFLICTING_ENTRY",
                        message=f"Semantic conflict with parameter at index {j}. Same context key: {comp_key}, but values differ ({value} vs {val_prev}).",
                        suggested_fix="Check if context (e.g. formulation or species) is missing, causing them to collide."
                    ))
            else:
                seen_keys[comp_key] = (i, value)

        # Build report
        errors   = [f for f in flags if f.severity == "error"]
        warnings = [f for f in flags if f.severity == "warning"]
        elapsed  = (time.monotonic() - t0) * 1000
        flagged_indices = {f.param_index for f in flags}

        report = VerificationReport(
            tier=1,
            elapsed_ms=elapsed,
            total_parameters=len(params),
            parameters_with_flags=len(flagged_indices),
            total_flags=len(flags),
            error_count=len(errors),
            warning_count=len(warnings),
            flags=flags,
            clean=len(flags) == 0,
        )
        report.summary = _build_summary(report)
        return report



# ---------------------------------------------------------------------------
# Tier 2: LLM Critic — real implementation
# ---------------------------------------------------------------------------
#
# Design goals:
#   • Uses its OWN small CriticVerdict JSON schema — NOT ExtractedPage.
#     This makes constrained decoding 10-20x faster (tiny schema vs large one).
#   • Calls the SGLang /generate endpoint directly via aiohttp.
#     No coupling to SGLangExtractor's ExtractedPage parsing.
#   • Only reviews parameters with severity="error" from Tier 1
#     (warnings are informational — LLM would add little signal).
#   • Patches corrected values back into document["parameters"] in-place
#     so the final JSON already contains the best data.
#   • Emits a concise "llm_verification" block in the document.
# ---------------------------------------------------------------------------

# Compact verdict schema — constrained decoding keeps this fast
_CRITIC_VERDICT_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {
            "type": "string",
            "enum": ["ok", "fix", "reject", "uncertain"],
            "description": (
                "'ok' = verified correct against source evidence. "
                "'fix' = verified incorrect and safely correctable from evidence. "
                "'reject' = verified invalid or hallucinated. "
                "'uncertain' = insufficient source evidence to decide; do not modify."
            )
        },
        "reasoning": {
            "type": "string",
            "description": "One-sentence justification for the verdict."
        },
        "corrected_fields": {
            "type": "object",
            "description": (
                "Flat dict of dot-notation field paths -> corrected values. "
                "Only populate when verdict='fix'."
            ),
            "additionalProperties": True
        }
    },
    "required": ["verdict", "reasoning"]
}

_CRITIC_SYSTEM_PROMPT = """\
You are a pharmacokinetics data quality auditor. You will be given:
  1. An extracted parameter (JSON)
  2. The source table metadata (subject compounds, species, footnotes)
  3. The matched source cell (row path, column path, exact text, value, unit) when available
  4. Automated rule violations detected by Tier 1 verification

Your job: decide if the parameter is correct, needs fixing, or should be rejected.

Rules:
- Answer ONLY with valid JSON matching the CriticVerdict schema.
- verdict="ok"        → Verified correct against source evidence.
- verdict="fix"       → Verified incorrect AND source evidence explicitly supplies the corrected value/context (e.g. matched cell column proves compound was wrong).
- verdict="reject"    → Parameter is hallucinated, cross-contaminated, or not present in source.
- verdict="uncertain" → Insufficient source evidence to make a safe decision. Do not guess.
- A correction is permitted ONLY when the provided source evidence explicitly supports the corrected value.
- NEVER correct a parameter based solely on plausibility, prior knowledge, pattern matching, or the parameter value itself.
"""


def _build_critic_prompt(
    param: dict,
    flags: list,
    table_evidence: dict = None,
    matched_source_cell: dict = None
) -> str:
    """Build the full Qwen3 chat-format prompt for one parameter with grounded cell evidence."""
    import json as _json
    flag_lines = "\n".join(
        f"  [{f.rule}] {f.severity.upper()}: {f.message}"
        for f in flags
    )
    
    critic_input = {
        "extracted_parameter": param,
        "source_table_metadata": {
            "table_id": table_evidence.get("table_id") if table_evidence else None,
            "title": table_evidence.get("title") if table_evidence else None,
            "subject_compounds": table_evidence.get("subject_compounds", []) if table_evidence else [],
            "footnote_compounds": table_evidence.get("footnote_compounds", []) if table_evidence else [],
            "referenced_compounds": table_evidence.get("referenced_compounds", []) if table_evidence else [],
            "species": table_evidence.get("species", []) if table_evidence else [],
            "footnotes": table_evidence.get("footnotes", []) if table_evidence else []
        } if table_evidence else None,
        "matched_source_cell": matched_source_cell,
        "tier1_flags": [
            {"severity": f.severity, "rule": f.rule, "message": f.message}
            for f in flags
        ]
    }
    
    user_content = (
        f"Audit this extracted parameter against the provided source evidence:\n"
        f"```json\n{_json.dumps(critic_input, indent=2)}\n```\n\n"
        f"Tier 1 violations detected:\n{flag_lines or '(none)'}\n\n"
        f"Return a CriticVerdict JSON object strictly adhering to the schema."
    )
    return (
        f"<|im_start|>system\n{_CRITIC_SYSTEM_PROMPT}<|im_end|>\n"
        f"<|im_start|>user\n{user_content}<|im_end|>\n"
        f"<|im_start|>assistant\n"
    )


def _apply_corrected_fields(param: dict, corrected_fields: dict) -> dict:
    """
    Patch dot-notation corrected fields back into the parameter dict using a strict whitelist.
    E.g. {"context.compound": "PFOA"} -> param["context"]["compound"] = "PFOA"
    """
    import copy
    from pk_pipeline.schemas import ExtractedParameter
    
    result = copy.deepcopy(param)
    
    ALLOWED_CORRECTIONS = {
        "context.compound",
        "context.species",
        "context.population",
        "context.life_stage",
        "context.organ",
        "context.formulation",
        "parameter_name_original",
        "parameter_name_standardized",
        "symbol_original",
        "quantitative_data.value",
        "quantitative_data.value_text",
        "quantitative_data.unit_original",
        "quantitative_data.unit_standardized",
        "quantitative_data.uncertainty.type",
        "quantitative_data.uncertainty.lower",
        "quantitative_data.uncertainty.upper",
        "quantitative_data.uncertainty.absolute",
        "quantitative_data.uncertainty.raw_text",
        "provenance.source_table",
        "provenance.row_id",
        "provenance.column_id",
        "provenance.cell_id",
        "provenance.row_path",
        "provenance.column_path",
        "provenance.source_quote",
        "provenance.status",
    }
    
    # Common schema mappings in case LLM forgets the prefix
    key_mappings = {
        "unit": "quantitative_data.unit_original",
        "unit_original": "quantitative_data.unit_original",
        "unit_standardized": "quantitative_data.unit_standardized",
        "value": "quantitative_data.value",
        "value_text": "quantitative_data.value_text",
        "compound": "context.compound",
        "species": "context.species",
        "organ": "context.organ",
        "formulation": "context.formulation",
        "parameter_name": "parameter_name_original",
        "symbol": "symbol_original",
    }
    
    for dotkey, val in corrected_fields.items():
        if dotkey in key_mappings:
            dotkey = key_mappings[dotkey]
            
        if dotkey not in ALLOWED_CORRECTIONS:
            logger.warning(f"Tier 2 LLM attempted to correct non-whitelisted field: {dotkey}. Ignoring.")
            continue
            
        parts = dotkey.split(".")
        obj = result
        for part in parts[:-1]:
            if part not in obj or not isinstance(obj[part], dict):
                obj[part] = {}
            obj = obj[part]
        obj[parts[-1]] = val
        
    try:
        # Revalidate the patched parameter to ensure the LLM didn't break the schema
        valid_param = ExtractedParameter.model_validate(result)
        return valid_param.model_dump()
    except Exception as e:
        logger.error(f"Tier 2 LLM correction broke the schema: {e}")
        return param # Fallback to unpatched parameter if invalid


class Tier2LLMCritic:
    """
    LLM-based critic that reviews parameters flagged by Tier 1.

    Calls the running SGLang server directly (port 30000) using the
    compact CriticVerdict schema — much faster than ExtractedPage decoding.

    This is OPTIONAL. It runs ASYNC and does not block the main pipeline.
    Enable with: --llm-verify flag in main.py, or call verify_document_with_llm().
    """

    def __init__(
        self,
        server_url: str = "http://127.0.0.1:30000",
        max_new_tokens: int = 512,
        concurrency: int = 4,
    ):
        self.server_url = server_url
        self.max_new_tokens = max_new_tokens
        self.concurrency = concurrency

    async def _call_llm(self, prompt: str) -> dict:
        """
        POST to the running SGLang /generate endpoint with the compact
        CriticVerdict schema for constrained decoding. Returns parsed dict.
        """
        import aiohttp
        import json as _json

        payload = {
            "text": prompt,
            "sampling_params": {
                "max_new_tokens": self.max_new_tokens,
                "temperature": 0.0,           # deterministic
                "repetition_penalty": 1.0,
                "json_schema": _json.dumps(_CRITIC_VERDICT_SCHEMA),
            },
        }
        timeout = aiohttp.ClientTimeout(total=120)   # 2-min max per param
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                f"{self.server_url}/generate", json=payload
            ) as resp:
                result = await resp.json()
                raw = result.get("text", "")
                # Strip <think>...</think> if model emits CoT
                if "</think>" in raw:
                    raw = raw.split("</think>")[-1].strip()
                return _json.loads(raw)

    async def audit_flagged(
        self,
        document: dict,
        tier1_report: "VerificationReport",
        max_params: int = 15,
        include_warnings: bool = False,
    ) -> dict:
        """
        Reviews Tier-1-flagged parameters.

        Args:
            document:         The extracted document dict (will be patched in-place).
            tier1_report:     Output of Tier1Verifier.verify().
            max_params:       Hard cap on number of LLM calls (cost/latency guard).
            include_warnings: If True, also reviews warning-level flags (not just errors).

        Returns a summary dict written to document["llm_verification"].
        """
        import json as _json
        import asyncio
        import time as _time

        t0 = _time.monotonic()
        table_evidences = {}
        for te in document.get("table_evidence", []):
            if te.get("table_id"):
                table_evidences[te.get("table_id")] = te
                table_evidences[normalize_table_id(te.get("table_id"))] = te

        # Build a map: param_index -> [flags]
        target_severities = {"error"}
        if include_warnings:
            target_severities.add("warning")

        flags_by_idx: dict[int, list] = {}
        for f in tier1_report.flags:
            if f.severity in target_severities:
                flags_by_idx.setdefault(f.param_index, []).append(f)

        # Sort by error count desc (worst first), cap at max_params
        ranked = sorted(flags_by_idx.items(), key=lambda kv: len(kv[1]), reverse=True)
        ranked = ranked[:max_params]

        if not ranked:
            result = {
                "reviewed": 0,
                "patched": 0,
                "rejected": 0,
                "elapsed_s": 0.0,
                "verdicts": [],
                "skipped_reason": "No error-level flags from Tier 1.",
            }
            document["llm_verification"] = result
            return result

        print(f"\n{'='*65}")
        print(f" TIER 2 LLM CRITIC  (reviewing {len(ranked)} flagged parameters)")
        print(f"{'='*65}")

        sem = asyncio.Semaphore(self.concurrency)
        verdicts = []

        async def _review_one(param_idx: int, flags: list) -> dict:
            async with sem:
                if param_idx >= len(params):
                    return {"param_index": param_idx, "status": "skipped", "reason": "index out of range"}
                param = params[param_idx]
                source_table = (param.get("provenance") or {}).get("source_table")
                te = (table_evidences.get(source_table) or table_evidences.get(normalize_table_id(source_table))) if source_table else None
                matched_cell = find_matched_cell(param, te) if te else None
                prompt = _build_critic_prompt(param, flags, table_evidence=te, matched_source_cell=matched_cell)
                try:
                    verdict_dict = await self._call_llm(prompt)
                    verdict     = verdict_dict.get("verdict", "uncertain")
                    reasoning   = verdict_dict.get("reasoning", "")
                    corrections = verdict_dict.get("corrected_fields", {})

                    icon = {"ok": "OK ", "fix": "FIX", "reject": "DEL"}.get(verdict, "???")
                    name_short = (param.get("parameter_name_original") or param.get("symbol_original") or "?")[:50]
                    print(f"  [{icon}] #{param_idx} '{name_short}' — {reasoning[:70]}")

                    return {
                        "param_index": param_idx,
                        "verdict": verdict,
                        "reasoning": reasoning,
                        "corrected_fields": corrections,
                        "status": "reviewed",
                    }
                except Exception as e:
                    logger.warning(f"Tier2 LLM critic failed for param #{param_idx}: {e}")
                    return {"param_index": param_idx, "status": "failed", "error": str(e)}

        tasks = [_review_one(idx, flgs) for idx, flgs in ranked]
        verdicts = await asyncio.gather(*tasks, return_exceptions=True)
        verdicts = [v for v in verdicts if not isinstance(v, Exception)]

        # --- Apply corrections and rejections back into document ---
        patched_count  = 0
        rejected_count = 0
        rejected_indices = set()

        for v in verdicts:
            idx = v.get("param_index")
            if idx is None or idx >= len(params):
                continue

            if v.get("verdict") == "fix" and v.get("corrected_fields"):
                params[idx] = _apply_corrected_fields(params[idx], v["corrected_fields"])
                params[idx]["needs_review"] = True   # still flag for human check
                params[idx]["llm_corrected"] = True
                patched_count += 1

            elif v.get("verdict") == "reject":
                rejected_indices.add(idx)
                rejected_count += 1

        # Remove rejected parameters (reverse order to preserve indices)
        for idx in sorted(rejected_indices, reverse=True):
            if idx < len(params):
                rejected_param_name = params[idx].get("parameter_name", "?")
                logger.info(f"Tier2: Rejected parameter #{idx} '{rejected_param_name}'")
                del params[idx]

        elapsed = _time.monotonic() - t0
        print(f"  * Reviewed:  {len(verdicts)} parameters")
        print(f"  * Patched:   {patched_count}")
        print(f"  * Rejected:  {rejected_count}")
        print(f"  * Elapsed:   {elapsed:.1f}s")
        print(f"{'='*65}\n")

        summary = {
            "reviewed": len(verdicts),
            "patched": patched_count,
            "rejected": rejected_count,
            "elapsed_s": round(elapsed, 2),
            "verdicts": [
                {k: v for k, v in vd.items() if k != "corrected_fields"}
                for vd in verdicts
                if vd.get("status") == "reviewed"
            ],
        }
        document["llm_verification"] = summary
        return summary


# ---------------------------------------------------------------------------
# Primary entry points for the pipeline
# ---------------------------------------------------------------------------

def verify_document(document: dict, verbose: bool = True) -> "VerificationReport":
    """
    Run Tier 1 verification on an extracted document dict.
    Attaches the report to document['verification'] and returns it.

    Latency: <5ms (pure Python, no GPU, no network).
    """
    verifier = Tier1Verifier()
    report = verifier.verify(document)
    document["verification"] = report.to_dict()

    if verbose:
        _print_verification_summary(report)

    return report


async def verify_document_with_llm(
    document: dict,
    verbose: bool = True,
    server_url: str = "http://127.0.0.1:30000",
    max_params: int = 15,
    include_warnings: bool = False,
) -> tuple:
    """
    Run Tier 1 (instant) + Tier 2 LLM critic (async, on flagged only).

    Returns: (tier1_report, llm_summary_dict)

    The document is patched in-place:
      - document["verification"]     ← Tier 1 report
      - document["llm_verification"] ← Tier 2 verdicts + corrections applied
    """
    # Tier 1 always runs first
    tier1 = verify_document(document, verbose=verbose)

    if tier1.clean:
        logger.info("Tier 1 passed cleanly — skipping Tier 2 LLM critic.")
        llm_summary = {
            "reviewed": 0,
            "patched": 0,
            "rejected": 0,
            "elapsed_s": 0.0,
            "verdicts": [],
            "skipped_reason": "Tier 1 was clean — no LLM review needed.",
        }
        document["llm_verification"] = llm_summary
        return tier1, llm_summary

    critic = Tier2LLMCritic(server_url=server_url)
    llm_summary = await critic.audit_flagged(
        document,
        tier1,
        max_params=max_params,
        include_warnings=include_warnings,
    )

    # Refresh Tier 1 on patched document so the stored report is accurate
    if llm_summary.get("patched", 0) > 0 or llm_summary.get("rejected", 0) > 0:
        logger.info("Re-running Tier 1 on LLM-patched document...")
        tier1_refreshed = Tier1Verifier().verify(document)
        document["verification"] = tier1_refreshed.to_dict()
        document["verification"]["note"] = "Re-run after Tier 2 LLM patching."

    return tier1, llm_summary


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_summary(report: "VerificationReport") -> str:
    if report.clean:
        return (
            f"All {report.total_parameters} parameters passed Tier 1 verification."
        )
    parts = []
    if report.error_count:
        parts.append(f"{report.error_count} error(s)")
    if report.warning_count:
        parts.append(f"{report.warning_count} warning(s)")
    return (
        f"{report.flagged_count}/{report.total_parameters} parameters flagged: "
        + ", ".join(parts)
        + f". Elapsed: {report.elapsed_ms:.1f}ms."
    )


def _print_verification_summary(report: "VerificationReport") -> None:
    print(f"\n{'='*65}")
    print(f" TIER 1 VERIFICATION REPORT")
    print(f"{'='*65}")
    print(f"  * Parameters checked:  {report.total_parameters}")
    print(f"  * Elapsed time:        {report.elapsed_ms:.1f}ms (zero GPU cost)")
    print(f"  * Errors:              {report.error_count}")
    print(f"  * Warnings:            {report.warning_count}")
    if report.clean:
        print(f"  * Status:              CLEAN -- no issues detected")
    else:
        print(f"  * Status:              ISSUES FOUND")
        for f in report.flags[:10]:
            icon = "[ERROR]" if f.severity == "error" else "[WARN] "
            print(f"    {icon} [{f.rule}] #{f.param_index} '{f.param_name[:45]}': {f.message}")
        if len(report.flags) > 10:
            print(
                f"    ... and {len(report.flags) - 10} more. "
                f"See 'verification' key in JSON output."
            )
    print(f"{'='*65}\n")
