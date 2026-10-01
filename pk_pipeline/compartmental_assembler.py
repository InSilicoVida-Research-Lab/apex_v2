import json
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
