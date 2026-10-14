import json
import copy
import hashlib
from typing import Dict, List, Optional
import re

def _clean_name(name: str) -> str:
    """Make parameter name safe for Antimony."""
    clean = re.sub(r"[^A-Za-z0-9_]", "_", str(name)).strip("_")
    return re.sub(r"_+", "_", clean)[:40] or "param"

def _get_val(param: Dict) -> float:
    qd = param.get("quantitative_data", {})
    return qd.get("value", 0.0) if qd else 0.0

def assemble_compartmental_model(params: List[Dict], dosing: List[Dict], model_type: str = "2-compartment") -> str:
    """
    Generates an Antimony model string for a compartmental PK model.
    """
    lines = []
    lines.append("// Compartmental PK Model (Auto-Generated)")
    lines.append("model pk_model()")
    lines.append("")
    
    # Extract parameters and group by logic
    param_dict = {}
    for p in params:
        sym = p.get("symbol") or p.get("parameter_name") or "param"
        val = _get_val(p)
        clean_sym = _clean_name(sym)
        if clean_sym not in param_dict:
            param_dict[clean_sym] = val
        else:
            param_dict[f"{clean_sym}_2"] = val
            
    mapped = {
        "V1": 1.0, "V2": 0.0, "V3": 0.0,
        "CL": 0.0, "Q": 0.0, "Q2": 0.0,
        "ka": 0.0
    }
    
    for k, v in param_dict.items():
        k_upper = k.upper()
        if "V1" in k_upper or "VC" in k_upper: mapped["V1"] = v
        elif ("V2" in k_upper or "VP" in k_upper) and "V3" not in k_upper: mapped["V2"] = v
        elif "V3" in k_upper: mapped["V3"] = v
        elif "CL" in k_upper and "Q" not in k_upper: mapped["CL"] = v
        elif "Q" == k_upper or "Q1" in k_upper or ("Q" in k_upper and "CL" not in k_upper): mapped["Q"] = v
        elif "KA" in k_upper: mapped["ka"] = v

    # Write parameters
    lines.append("  // Parameters")
    for k, v in param_dict.items():
        if v is None: v = 0.0
        lines.append(f"  {k} = {v};")
        
    lines.append("")
    
    # Write compartments
    lines.append("  // Compartments")
    v1_sym = [k for k in param_dict.keys() if k.upper() in ["V1", "VC"]]
    v1_val = v1_sym[0] if v1_sym else str(mapped['V1'])
    lines.append(f"  compartment Central = {v1_val};")
    
    if mapped["V2"] > 0:
        v2_sym = [k for k in param_dict.keys() if k.upper() in ["V2", "VP"]]
        v2_val = v2_sym[0] if v2_sym else str(mapped['V2'])
        lines.append(f"  compartment Peripheral = {v2_val};")
    if mapped["V3"] > 0:
        v3_sym = [k for k in param_dict.keys() if k.upper() in ["V3"]]
        v3_val = v3_sym[0] if v3_sym else str(mapped['V3'])
        lines.append(f"  compartment Peripheral2 = {v3_val};")
    lines.append("  compartment Depot = 1.0;")
    lines.append("")
    
    # Write species
    lines.append("  // Species (Amounts)")
    lines.append("  species A_Central in Central;")
    lines.append("  A_Central = 0.0;")
    if mapped["V2"] > 0:
        lines.append("  species A_Peripheral in Peripheral;")
        lines.append("  A_Peripheral = 0.0;")
    if mapped["V3"] > 0:
        lines.append("  species A_Peripheral2 in Peripheral2;")
        lines.append("  A_Peripheral2 = 0.0;")
    lines.append("  species A_Depot in Depot;")
    lines.append("  A_Depot = 0.0;")
    lines.append("")
    
    # Check dosing to set initial dose
    total_dose = 0.0
    route = "IV"
    if dosing:
        ev = dosing[0]
        total_dose = ev.get("dose", 0.0)
        route = ev.get("route", "IV").upper()
    
    if "ORAL" in route or mapped["ka"] > 0:
        lines.append(f"  A_Depot = {total_dose};")
    else:
        lines.append(f"  A_Central = {total_dose};")
        
    lines.append("")
    
    # Write reactions
    lines.append("  // Reactions")
    if mapped["ka"] > 0:
        ka_sym = [k for k in param_dict.keys() if "KA" in k.upper()][0]
        lines.append(f"  Absorption: A_Depot -> A_Central; {ka_sym} * A_Depot;")
        
    cl_sym = [k for k in param_dict.keys() if "CL" in k.upper()]
    cl_val = cl_sym[0] if cl_sym else "0.0"
    lines.append(f"  Elimination: A_Central -> ; ({cl_val}/Central) * A_Central;")
    
    if mapped["V2"] > 0:
        q_sym = [k for k in param_dict.keys() if k.upper() in ["Q", "Q1", "Q_P", "QP"]]
        q_val = q_sym[0] if q_sym else "0.0"
        lines.append(f"  Distribution1: A_Central -> A_Peripheral; ({q_val}/Central)*A_Central - ({q_val}/Peripheral)*A_Peripheral;")
        
    if mapped["V3"] > 0:
        q2_sym = [k for k in param_dict.keys() if k.upper() in ["Q2", "Q_T"]]
        q2_val = q2_sym[0] if q2_sym else "0.0"
        lines.append(f"  Distribution2: A_Central -> A_Peripheral2; ({q2_val}/Central)*A_Central - ({q2_val}/Peripheral2)*A_Peripheral2;")
    
    lines.append("")
    lines.append("  // Derived Quantities")
    lines.append("  C_Central := A_Central / Central;")
    if mapped["V2"] > 0:
        lines.append("  C_Peripheral := A_Peripheral / Peripheral;")
    
    lines.append("end")
    return "\n".join(lines)


DIMENSIONLESS_KEYWORDS = (
    "partition", "ratio", ":plasma", ":blood", "fraction", "fu", "free",
    "bioav", "bioavailability", "unitless", "hct", "hematocrit", "kp_", "raf"
)

def normalize_and_validate_units(param: dict) -> dict:
    """Fix MISSING_UNIT warnings on dimensionless ratios, fractions, and Kp values."""
    q = param.get("quantitative_data") or {}
    name = param.get("parameter_name") or param.get("parameter_name_original") or ""
    sym = param.get("symbol") or param.get("symbol_original") or ""
    name_sym = f"{name} {sym}".lower()

    unit = q.get("unit") or q.get("unit_original")
    if not unit or str(unit).lower() in ("none", "null", "", "unitless", "-"):
        if any(k in name_sym for k in DIMENSIONLESS_KEYWORDS):
            q["unit"] = "dimensionless"
            q["unit_original"] = "dimensionless"
            q["unit_standardized"] = "dimensionless"
    return param


def backfill_cross_species_inherited_parameters(model_parameters: list[dict]) -> list[dict]:
    """
    When a paper adapts an animal model (e.g., Nonhuman primate / Rat) to Human
    and only tabulates the scaled overrides under Human, clone the held-constant
    parameters from the animal baseline into the Human context.
    """
    out = list(model_parameters)
    by_comp_species: dict[tuple[str, str], dict[str, dict]] = {}

    for p in out:
        ctx = p.get("context") or {}
        comp = (ctx.get("compound") or "SYSTEM").upper()
        sp = (ctx.get("species") or ctx.get("subject_species") or "").strip().lower()
        sym = (p.get("symbol_standardized") or p.get("symbol") or p.get("symbol_original") or p.get("parameter_name_standardized") or p.get("parameter_name_original") or "").strip()
        if sp and sym:
            by_comp_species.setdefault((comp, sp), {})[sym] = p

    compounds = {c for (c, _) in by_comp_species}
    donor_priority = ["nonhuman primate", "monkey", "cynomolgus monkey", "rat", "mouse"]

    for comp in compounds:
        human_dict = by_comp_species.get((comp, "human"))
        donor_dict = None
        donor_sp_name = None
        for dp in donor_priority:
            if by_comp_species.get((comp, dp)):
                donor_dict = by_comp_species[(comp, dp)]
                donor_sp_name = dp
                break

        if not human_dict or not donor_dict:
            continue

        for sym, donor_param in donor_dict.items():
            sym_clean = sym.upper()
            # Do not inherit body weight or compound/species specific overrides that are distinctly tabulated
            if sym_clean in ["BW", "BODY WEIGHT", "BODY_WEIGHT", "T1/2", "HALF_LIFE", "HALF-LIFE"]:
                continue
            if sym not in human_dict:
                cloned = copy.deepcopy(donor_param)
                donor_id = donor_param.get("parameter_id", "param")
                cloned["parameter_id"] = f"{donor_id}_human_inherited"
                cloned_ctx = cloned.setdefault("context", {})
                cloned_ctx["species"] = "human"
                cloned_ctx["subject_species"] = "Human"
                cloned_prov = cloned.setdefault("provenance", {})
                cloned_prov["status"] = "assumed_default"
                cloned_prov["parameter_status"] = "Assumed"
                cloned_prov["derivation"] = {
                    "method": f"Held constant from {donor_sp_name.title()} model",
                    "source_species": donor_sp_name,
                }
                cloned_prov["evidence_directness"] = "inherited_cross_species"
                out.append(cloned)
                human_dict[sym] = cloned

    return out


def apply_pbpk_inheritance(parameters: list[dict]) -> list[dict]:
    """
    1. Cross-Compound Inheritance: If value_qualifier contains 'Assumed (PFOS)',
       link provenance status as 'assumed_same_as_parent' / 'Assumed'.
    2. Cross-Species Inheritance: If a paper defines both an animal baseline
       (e.g., 'Nonhuman primate') and 'Human' for a compound, backfill any
       chemical/physiological parameters omitted from the Human table (e.g., k12, k21, ka, VfilC, QfilC, Free).
    """
    enriched = [normalize_and_validate_units(copy.deepcopy(p)) for p in parameters]

    # Handle 'Assumed (PFOS)' in value_qualifier or reference
    for p in enriched:
        q = p.get("quantitative_data") or {}
        vq = (q.get("value_qualifier") or "").lower()
        prov = p.setdefault("provenance", {})
        ref = (prov.get("reference") or "").lower()
        src = (prov.get("source_quote") or "").lower()
        if "assumed (pfos)" in vq or "assumed from pfos" in vq or "assumed (pfos)" in ref or "assumed (pfos)" in src:
            prov["parameter_status"] = "Assumed"
            prov["status"] = "assumed"

    # Backfill cross-species inherited parameters across all compounds (PFOA, PFOS, PFHxS, etc.)
    enriched = backfill_cross_species_inherited_parameters(enriched)

    return enriched


def deduplicate_and_format_records(parameters: list[dict], ontology_linker=None) -> list[dict]:
    """
    Deduplicates extracted parameters and unpacks ontology linking into clean top-level keys
    instead of serializing a JSON string inside `canonical_name`.
    """
    seen_keys = set()
    final_records = []

    for p in parameters:
        ctx = p.get("context") or {}
        q = p.get("quantitative_data") or {}
        prov = p.get("provenance") or {}

        # Fallback: if value is null but start_value exists (time-varying range), keep both
        primary_val = q.get("value") if q.get("value") is not None else q.get("start_value")

        param_name = p.get("parameter_name") or p.get("parameter_name_original") or ""
        sym = p.get("symbol") or p.get("symbol_original") or ""
        sp = ctx.get("subject_species") or ctx.get("species") or ""
        form = ctx.get("formulation") or ""
        if isinstance(form, list):
            form = ",".join(str(f) for f in form)
        comp_org = ctx.get("compartment") or ctx.get("organ") or ""

        dedup_key = (
            sym.lower(),
            param_name.lower(),
            (ctx.get("compound") or "").lower(),
            sp.lower(),
            (ctx.get("life_stage") or "").lower(),
            str(form).lower(),
            comp_org.lower(),
            primary_val,
            q.get("end_value")
        )
        if dedup_key in seen_keys:
            continue
        seen_keys.add(dedup_key)

        # Unpack ontology fields cleanly (fixes stringified JSON in canonical_name column)
        ont_match = ontology_linker.link(sym or param_name) if ontology_linker else {}
        param_id = p.get("parameter_id")
        if not param_id or not str(param_id).startswith("param_"):
            param_id = "param_" + hashlib.md5(str(dedup_key).encode()).hexdigest()[:16]

        rec = copy.deepcopy(p)
        rec["parameter_id"] = param_id
        rec["parameter_class"] = p.get("parameter_class", "physiological")
        rec["parameter_name_original"] = param_name
        rec["parameter_name"] = param_name
        rec["parameter_name_standardized"] = ont_match.get("canonical_name", p.get("parameter_name_standardized", param_name))
        rec["pbpko_id"] = ont_match.get("pbpko_id", p.get("pbpko_id", ""))
        rec["pbpko_iri"] = ont_match.get("pbpko_iri", p.get("pbpko_iri", ""))
        rec["ontology_match_type"] = ont_match.get("match_type", p.get("ontology_match_type", "unmatched"))
        rec["symbol_original"] = sym
        rec["symbol"] = sym
        rec["symbol_standardized"] = p.get("symbol_standardized") or sym.replace(" ", "")
        rec["context"] = ctx
        rec["quantitative_data"] = q
        rec["provenance"] = prov
        rec["needs_review"] = p.get("needs_review", False)

        final_records.append(rec)

    return final_records

