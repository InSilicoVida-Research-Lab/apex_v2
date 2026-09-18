from pydantic import BaseModel, Field
from typing import List, Optional

# ─── Request Schema ────────────────────────────────────────────────────────────

class ExtractionRequest(BaseModel):
    pdf_path: str
    target_compounds: Optional[List[str]] = None

# ─── Document-Level Metadata (extracted once per paper, not per page) ──────────

class PageMetadata(BaseModel):
    title: Optional[str] = None
    authors: Optional[List[str]] = None
    journal: Optional[str] = None
    year: Optional[int] = None

class ModelClassification(BaseModel):
    model_type: str = Field(description="Must be 'pbpk', 'simple_empirical_compartmental', or 'not_applicable'")
    evidence_quote: Optional[str] = None

class Connection(BaseModel):
    from_comp: str = Field(alias="from")
    to_comp: str = Field(alias="to")

class Structure(BaseModel):
    compartments: Optional[List[str]] = None
    connections: Optional[List[Connection]] = None
    source_location: Optional[str] = None

# ─── Nested Parameter Sub-Models ───────────────────────────────────────────────

class BiologicalContext(BaseModel):
    compound: Optional[str] = Field(
        None,
        description="Chemical or drug being studied exactly as printed (e.g., PFOS, PFOA, BPA). "
                    "Isotopically labeled tracers and metabolites are distinct compounds."
    )
    subject_species: Optional[str] = Field(
        None,
        description="Animal or human subject exactly as printed (e.g., Cynomolgus monkey, Human, Rat). "
                    "Only populate if explicitly stated for this parameter."
    )
    life_stage: Optional[str] = Field(
        None,
        description="Age or life stage only if explicitly stated (e.g., Adult, Infant, Gestation Week 20)."
    )
    compartment: Optional[str] = Field(
        None,
        description="Biological compartment this parameter refers to, exactly as named by the authors "
                    "(e.g., Liver, Plasma, Filtrate). Never substitute generic names."
    )
    route: Optional[str] = Field(
        None,
        description="Route of administration if stated (e.g., Oral, IV, Inhalation)."
    )
    population: Optional[str] = Field(
        None,
        description="Named patient group or population only if explicitly stated "
                    "(e.g., hepatically impaired, pediatric). Leave null otherwise."
    )

class QuantitativeData(BaseModel):
    value: Optional[float] = Field(
        None,
        description="The primary numerical value. If only a range is given, place the bounds in range_low and range_high."
    )
    range_low: Optional[float] = Field(
        None,
        description="Lower bound when the parameter is printed as a range "
                    "(e.g., the '0.18' in '0.23 (0.18, 0.29)' or a time-varying lower bound)."
    )
    range_high: Optional[float] = Field(
        None,
        description="Upper bound when the parameter is printed as a range "
                    "(e.g., the '0.29' in '0.23 (0.18, 0.29)')."
    )
    variance: Optional[float] = Field(
        None,
        description="Standard deviation, standard error, or confidence interval numeric value."
    )
    variance_type: Optional[str] = Field(
        None,
        description="Type of variance exactly as printed: 'SD', 'SE', '95% CI', etc."
    )
    unit: Optional[str] = Field(
        None,
        description="Unit of measurement exactly as printed (e.g., mg/kg, L/h, 1/min). "
                    "If the unit is inherited from a group header rather than printed inline, still record it here."
    )
    unit_inherited: Optional[bool] = Field(
        None,
        description="True if the unit was stated once in a group/section header rather than printed inline with this value."
    )
    value_qualifier: Optional[str] = Field(
        None,
        description="Any qualifier printed alongside the value beyond the number itself "
                    "(e.g., 'Fixed', 'assumed', 'estimated'). Never drop or fold into the numeric value."
    )

class Provenance(BaseModel):
    source_location: Optional[str] = Field(
        None,
        description="Where this parameter was found (e.g., 'Table 1', 'Figure 2', 'Results paragraph 2')."
    )
    source_quote: Optional[str] = Field(
        None,
        description="Short, exact transcription — not a paraphrase — of the specific cell(s) or sentence "
                    "this value came from. If you cannot produce a directly traceable quote, omit the parameter."
    )
    parameter_status: Optional[str] = Field(
        None,
        description="How the parameter was obtained, exactly as described by the authors: "
                    "'Measured', 'Fitted', 'Fixed', 'Assumed', 'Scaled', or 'Literature'. Leave null if not stated."
    )
    confidence: Optional[str] = Field(
        None,
        description="'high' = value, unit, and symbol all printed together unambiguously. "
                    "'medium' = any inheritance from a group header or nearby context was required. "
                    "'low' = any interpretive judgment was needed (degraded text, ambiguous boundary, uncertain abbreviation)."
    )

# ─── Top-Level Parameter and Result ────────────────────────────────────────────

class ExtractedParameter(BaseModel):
    parameter_name: Optional[str] = Field(
        None,
        description="Full descriptive name exactly as printed (e.g., 'Volume of distribution central compartment'). "
                    "Do not invent a name for a bare symbol."
    )
    symbol: Optional[str] = Field(
        None,
        description="Mathematical symbol exactly as printed (e.g., VCC, Tmc, k12, CL/F). "
                    "Do not standardize or expand — transcribe verbatim."
    )
    context: Optional[BiologicalContext] = Field(None, description="Biological and study context for this parameter.")
    quantitative_data: Optional[QuantitativeData] = Field(None, description="Numerical values, ranges, units, and qualifiers.")
    provenance: Optional[Provenance] = Field(None, description="Source location, supporting quote, and confidence.")

class ExtractedPage(BaseModel):
    page_metadata: PageMetadata
    model_classification: ModelClassification
    structure: Optional[Structure] = None
    parameters: List[ExtractedParameter] = Field(
        default_factory=list,
        description="All PK model parameters explicitly present on this page. "
                    "An empty list is correct if the page contains no PK data."
    )
