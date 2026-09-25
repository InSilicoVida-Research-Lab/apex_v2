"""
physio_db.py — Built-in Physiological Parameter Database
=========================================================
Reference values for standard PBPK species from:
  - Brown et al. (1997) Toxicol. Sci. 34: 197-247  (rat, mouse, human)
  - ICRP Publication 89 (2002)  (human reference male/female)

All blood flow fractions are fractions of cardiac output (unitless).
Volumes are fractions of body weight (unitless) unless noted.

Usage:
    from physio_db import get_physio_params, list_species
    params = get_physio_params("human")
    params = get_physio_params("rat", bw_kg=0.25)
"""

from typing import Dict, Optional

# ---------------------------------------------------------------------------
# Database — (Brown et al. 1997, Table 1–3; ICRP 89)
# Values are fraction of BW for volumes, fraction of cardiac output for flows
# Cardiac output itself: L/h/kg (allometric: QC = QCC * BW^0.74)
# ---------------------------------------------------------------------------

_DB: Dict[str, Dict] = {

    # ---- Human (70 kg reference adult male) ----
    "human": {
        "BW":          70.0,   # kg, reference body weight
        "QCC":         16.5,   # L/h/kg^0.74, cardiac output coefficient (allometric)

        # Organ volumes (fraction of BW)
        "VLC":         0.026,  # liver
        "VKC":         0.004,  # kidney
        "VFC":         0.214,  # fat
        "VMC":         0.400,  # muscle
        "VBC":         0.079,  # blood
        "VRC":         0.048,  # richly perfused tissue (excluding liver, kidney)
        "VSC":         0.001,  # skin
        "VLuC":        0.010,  # lung
        "VGC":         0.014,  # gut

        # Blood flow fractions (fraction of cardiac output)
        "QLC":         0.227,  # liver (hepatic artery + portal vein)
        "QKC":         0.175,  # kidney
        "QFC":         0.052,  # fat
        "QMC":         0.175,  # muscle
        "QRC":         0.186,  # richly perfused
        "QSC":         0.058,  # skin
        "QGC":         0.181,  # gut (→ portal vein → liver)

        # Renal physiology
        "GFR":         7.5,    # L/h, glomerular filtration rate (reference)
        "VfilC":       0.0003, # filtrate compartment volume fraction of BW

        # Plasma protein binding (generic)
        "Fu_plasma":   0.01,   # fraction unbound in plasma (compound-specific — placeholder)
    },

    # ---- Rat (0.25 kg reference adult male) ----
    "rat": {
        "BW":          0.25,
        "QCC":         15.0,   # L/h/kg^0.74 (allometric)

        "VLC":         0.034,
        "VKC":         0.007,
        "VFC":         0.070,
        "VMC":         0.400,
        "VBC":         0.074,
        "VRC":         0.048,
        "VSC":         0.019,
        "VLuC":        0.005,
        "VGC":         0.021,

        "QLC":         0.183,
        "QKC":         0.141,
        "QFC":         0.071,
        "QMC":         0.278,
        "QRC":         0.183,
        "QSC":         0.058,
        "QGC":         0.155,

        "GFR":         1.0,    # L/h
        "VfilC":       0.0003,
        "Fu_plasma":   0.01,
    },

    # ---- Mouse (0.025 kg reference adult male) ----
    "mouse": {
        "BW":          0.025,
        "QCC":         14.1,

        "VLC":         0.055,
        "VKC":         0.017,
        "VFC":         0.040,
        "VMC":         0.380,
        "VBC":         0.049,
        "VRC":         0.048,
        "VSC":         0.017,
        "VLuC":        0.007,
        "VGC":         0.042,

        "QLC":         0.161,
        "QKC":         0.091,
        "QFC":         0.050,
        "QMC":         0.352,
        "QRC":         0.214,
        "QSC":         0.058,
        "QGC":         0.143,

        "GFR":         0.012,
        "VfilC":       0.0003,
        "Fu_plasma":   0.01,
    },

    # ---- Nonhuman Primate (Macaque, ~5 kg) ----
    "nonhuman primate": {
        "BW":          5.0,
        "QCC":         19.8,   # from Dean et al. 2025

        "VLC":         0.022,
        "VKC":         0.005,
        "VFC":         0.070,
        "VMC":         0.380,
        "VBC":         0.057,
        "VRC":         0.048,
        "VSC":         0.020,
        "VLuC":        0.010,
        "VGC":         0.021,

        "QLC":         0.200,
        "QKC":         0.150,
        "QFC":         0.060,
        "QMC":         0.210,
        "QRC":         0.200,
        "QSC":         0.058,
        "QGC":         0.150,

        "GFR":         0.15,   # L/h (~5 kg NHP estimate)
        "VfilC":       0.0004,
        "Fu_plasma":   0.01,
    },
}

# Species name aliases (for fuzzy matching)
_ALIASES: Dict[str, str] = {
    "homo sapiens": "human",
    "h. sapiens": "human",
    "human adult": "human",
    "adult human": "human",
    "rattus norvegicus": "rat",
    "sprague-dawley": "rat",
    "wistar": "rat",
    "mus musculus": "mouse",
    "rhesus macaque": "nonhuman primate",
    "macaca mulatta": "nonhuman primate",
    "cynomolgus": "nonhuman primate",
    "nhp": "nonhuman primate",
}


def list_species() -> list:
    """Return list of canonical species names in the database."""
    return sorted(_DB.keys())


def get_physio_params(
    species: str,
    bw_kg: Optional[float] = None,
) -> Dict[str, float]:
    """
    Return physiological parameter dict for a given species.

    Parameters
    ----------
    species : str
        Species name (case-insensitive). Aliases are supported.
    bw_kg : float, optional
        Override reference body weight (kg). Volumes are scaled accordingly.

    Returns
    -------
    dict
        Mapping of symbol → value (all floats).
        Returns empty dict if species not found.
    """
    key = species.strip().lower()
    key = _ALIASES.get(key, key)

    if key not in _DB:
        return {}

    params = dict(_DB[key])  # copy

    # Override BW if provided
    if bw_kg is not None:
        params["BW"] = float(bw_kg)

    return params


def describe_param(symbol: str) -> str:
    """Return a brief description of a physiological parameter symbol."""
    _DESC = {
        "BW": "Body weight (kg)",
        "QCC": "Cardiac output coefficient — allometric (L/h/kg^0.74)",
        "VLC": "Liver volume fraction (fraction of BW)",
        "VKC": "Kidney volume fraction (fraction of BW)",
        "VFC": "Fat volume fraction (fraction of BW)",
        "VMC": "Muscle volume fraction (fraction of BW)",
        "VBC": "Blood volume fraction (fraction of BW)",
        "VRC": "Richly perfused tissue volume fraction (fraction of BW)",
        "VSC": "Skin volume fraction (fraction of BW)",
        "VLuC": "Lung volume fraction (fraction of BW)",
        "VGC": "Gut volume fraction (fraction of BW)",
        "QLC": "Hepatic blood flow fraction (fraction of cardiac output)",
        "QKC": "Renal blood flow fraction (fraction of cardiac output)",
        "QFC": "Fat blood flow fraction (fraction of cardiac output)",
        "QMC": "Muscle blood flow fraction (fraction of cardiac output)",
        "QRC": "Richly perfused blood flow fraction (fraction of cardiac output)",
        "QSC": "Skin blood flow fraction (fraction of cardiac output)",
        "QGC": "Gut blood flow fraction (fraction of cardiac output)",
        "GFR": "Glomerular filtration rate (L/h)",
        "VfilC": "Filtrate compartment volume fraction (fraction of BW)",
        "Fu_plasma": "Fraction unbound in plasma (compound-specific placeholder)",
    }
    return _DESC.get(symbol, f"Physiological parameter: {symbol}")


if __name__ == "__main__":
    print("Available species:", list_species())
    print("\nHuman physiological parameters:")
    for k, v in get_physio_params("human").items():
        print(f"  {k:15s} = {v:>10.5f}   ({describe_param(k)})")
