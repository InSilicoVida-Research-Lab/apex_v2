from pydantic import BaseModel, Field
from typing import List, Optional, Union

# ─── Request Schema ────────────────────────────────────────────────────────────

class ExtractionRequest(BaseModel):
    pdf_path: str
    target_compounds: Optional[List[str]] = None

# ─── Document-Level Metadata ───────────────────────────────────────────────────

class PageMetadata(BaseModel):
    title: Optional[str] = None
    authors: Optional[List[str]] = None
    journal: Optional[str] = None
    year: Optional[int] = None

class ModelClassification(BaseModel):
    model_type: str = Field(description="Must be 'pbpk', 'simple_empirical_compartmental', or 'not_applicable'")
    evidence_quote: Optional[str] = None

# ─── Enriched Model Structure ──────────────────────────────────────────────────

class Compartment(BaseModel):
    id: str
    label_raw: str
    confidence: Optional[float] = None

class Connection(BaseModel):
    source: str
    target: str
    label_raw: Optional[str] = None
    direction: str = Field(description="Must be 'forward', 'reverse', 'bidirectional', or 'unknown'")
    edge_type: Optional[str] = None
    evidence: Optional[str] = None
    confidence: Optional[float] = None

class UnresolvedTopology(BaseModel):
    description: str
    reason: str

class AbsorptionModel(BaseModel):
    route: Optional[str] = Field(None, description="e.g. 'oral', 'iv', 'inhalation'")
    model_type: Optional[str] = Field(None, description="e.g. 'first_order', 'Weibull', 'mechanistic'")
    site: Optional[str] = Field(None, description="e.g. 'gut', 'stomach'")
    evidence_quote: Optional[str] = None

class MetabolismModel(BaseModel):
    organ: Optional[str] = Field(None)
    enzyme: Optional[str] = Field(None, description="e.g. 'CYP1A2'")
    metabolite: Optional[str] = Field(None)
    kinetics: Optional[str] = Field(None, description="e.g. 'Michaelis-Menten', 'first_order'")
    parameters: Optional[List[str]] = Field(None, description="e.g. ['Vmax', 'Km']")
    evidence_quote: Optional[str] = None

class EliminationModel(BaseModel):
    routes: Optional[List[str]] = Field(None, description="e.g. ['renal', 'fecal', 'biliary']")
    evidence_quote: Optional[str] = None

class Structure(BaseModel):
    reported_compartment_count: Optional[int] = Field(None, description="Compartment count as stated by authors.")
    listed_compartment_count: Optional[int] = Field(None, description="Actual number of compartments found.")
    count_consistency: Optional[str] = Field(None, description="'consistent' or 'inconsistent_in_source'")
    compartments: Optional[List[Compartment]] = None
    connections: Optional[List[Connection]] = None
    absorption: Optional[AbsorptionModel] = None
    metabolism: Optional[MetabolismModel] = None
    elimination: Optional[EliminationModel] = None
    unresolved: Optional[List[UnresolvedTopology]] = None
    source_location: Optional[str] = None

# ─── Nested Parameter Sub-Models ───────────────────────────────────────────────

class BiologicalContext(BaseModel):
    compound: Optional[str] = Field(None, description="Active chemical entity (e.g., 'riluzole', 'PFOS'). NOT a formulation name.")
    formulation: Optional[List[str]] = Field(None, description="Specific formulations (e.g., ['Rilutor', 'ASD']). Separate from compound.")
    species: Optional[str] = Field(None, description="Animal or human subject (e.g., 'rat', 'human').")
    life_stage: Optional[str] = Field(None, description="Age or life stage only if explicitly stated.")
    organ: Optional[str] = Field(None, description="Biological organ (e.g., 'liver', 'plasma').")
    route: Optional[str] = Field(None, description="Route of administration if stated.")
    population: Optional[str] = Field(None, description="Named patient group or population.")

class QuantitativeData(BaseModel):
    value_text: Optional[str] = Field(None, description="Exact printed value text verbatim, e.g. '5a', '0.174', '0.69, 2.19'.")
    value: Optional[float] = Field(None, description="Primary numerical value as a pure float. Null if multi-valued or non-numeric.")
    range_start: Optional[float] = Field(None, description="Start of a range (e.g. '34.5' in '34.5-31.9'). NOT for +/- values.")
    range_end: Optional[float] = Field(None, description="End of a range. Preserves direction (e.g. '31.9').")
    variance: Optional[float] = Field(None, description="Variance/uncertainty numeric value from +/- notation.")
    variance_type: Optional[str] = Field(None, description="Type of variance as printed: 'SD', 'SE', '95% CI', '+/-'.")
    unit_original: Optional[str] = Field(None, description="Unit exactly as printed in the source (e.g., '1/h/kg^0.25'). NEVER convert or interpret.")
    unit_standardized: Optional[str] = Field(None, description="Standardized/normalized unit (e.g., 'h^-1 kg^-0.25'). MUST STRICTLY PRESERVE all SI prefixes (e.g. 'nmol' stays 'nmol', 'μL' stays 'μL', NEVER convert to 'mol' or 'L'). Null if not normalized.")
    normalization_basis: Optional[str] = Field(None, description="E.g., 'cardiac_output', 'body_weight', 'tissue_plasma_ratio'.")

class Derivation(BaseModel):
    method: Optional[str] = Field(None, description="e.g. 'allometric_scaling', 'rodgers_rowland', 'literature', 'optimized'")
    source_species: Optional[str] = Field(None, description="e.g. 'rat' when human value was derived from rat")
    optimization_target: Optional[str] = Field(None, description="e.g. 'experimental_PK_data', 'Liboux et al.'")

class Provenance(BaseModel):
    source_page: Optional[int] = Field(None)
    source_location: Optional[str] = Field(None, description="e.g. 'Table I', 'Figure 2', 'Results paragraph'.")
    source_quote: Optional[str] = Field(None, description="Verbatim quote from the source cell/sentence.")
    reference: Optional[str] = Field(None, description="Literature citation like '[17]'.")
    status: Optional[str] = Field(
        None,
        description=(
            "How the value was obtained. Must be one of: "
            "'experimental', 'calculated', 'literature_derived', 'optimized', "
            "'similar_to_rat', 'assumed_same_as_parent', 'human_specific', "
            "'allometrically_scaled'. Leave null if not stated."
        )
    )
    derivation: Optional[Derivation] = Field(None, description="Detailed derivation metadata when status is 'optimized', 'allometrically_scaled', or 'similar_to_rat'.")
    evidence_directness: Optional[str] = Field(None, description="'direct' or 'inferred'")

class ConfidenceScores(BaseModel):
    value_confidence: Optional[str] = Field(None, description="'high', 'medium', 'low'")
    unit_confidence: Optional[str] = Field(None, description="'high', 'medium', 'low'")
    species_confidence: Optional[str] = Field(None, description="'high', 'medium', 'low'")
    formulation_confidence: Optional[str] = Field(None, description="'high', 'medium', 'low'")
    parameter_class_confidence: Optional[str] = Field(None, description="'high', 'medium', 'low'")
    provenance_confidence: Optional[str] = Field(None, description="'high', 'medium', 'low'")

# ─── Extracted Parameter ───────────────────────────────────────────────────────

class ExtractedParameter(BaseModel):
    parameter_id: Optional[str] = Field(None, description="Unique composite ID (auto-generated post-extraction).")
    parameter_class: Optional[str] = Field(
        None,
        description=(
            "Broad semantic class. Must be exactly one of: "
            "'physiological' (organ volumes, blood flows, GFR - describes the organism), "
            "'biochemical' (partition coefficients, fu, Vmax, Km, clearances - drug-specific properties), "
            "'compound_specific' (physicochemical: MW, logP, solubility, pKa). "
            "Blood flows and organ volumes are ALWAYS 'physiological', never 'compound_specific'."
        )
    )
    parameter_subclass: Optional[str] = Field(
        None,
        description=(
            "Specific sub-category. Common values: "
            "'organ_blood_flow_fraction', 'organ_volume_fraction', "
            "'partition_coefficient', 'fraction_unbound', "
            "'absorption_rate_constant', 'gastric_emptying_rate', 'fecal_elimination_rate_constant', "
            "'maximal_velocity', 'michaelis_menten_constant', "
            "'renal_clearance', 'metabolic_clearance'. "
            "GE = 'gastric_emptying_rate', Kabs = 'absorption_rate_constant', Kfeces = 'fecal_elimination_rate_constant'."
        )
    )
    parameter_name_original: str = Field(..., description="Full descriptive name exactly as printed in the source.")
    parameter_name_standardized: Optional[str] = Field(None, description="Standardized ontology name (e.g., 'liver_blood_flow_fraction'). Mark as derived if not in paper.")
    symbol_original: Optional[str] = Field(None, description="Mathematical symbol exactly as printed.")
    symbol_standardized: Optional[str] = Field(None, description="Standardized symbol (e.g., 'Kp_liver_plasma'). Null if not printed and not derivable.")

    context: BiologicalContext = Field(..., description="Biological and study context.")
    quantitative_data: QuantitativeData = Field(..., description="Numerical values and units.")
    provenance: Provenance = Field(..., description="Source location and status.")
    confidence: ConfidenceScores = Field(default_factory=ConfidenceScores)
    needs_review: bool = Field(False)

# ─── Formulation Characterization (non-PBPK physical measurements) ─────────────

class FormulationMeasurement(BaseModel):
    measurement_type: str = Field(..., description="e.g., 'contact_angle', 'particle_size', 'dissolution_rate'")
    sample_component: Optional[str] = Field(None, description="Sample being measured (e.g., 'PAA', 'RLZ:PVP VA ASD')")
    probe_liquid: Optional[str] = Field(None, description="Probe medium if applicable (e.g., 'water')")
    value: Optional[float] = Field(None)
    variance: Optional[float] = Field(None)
    variance_type: Optional[str] = Field(None, description="'SD', 'SE', '+/-'")
    unit: Optional[str] = Field(None)
    provenance: Optional[Provenance] = None

# ─── Parameter Mention Without Numeric Value ──────────────────────────────────

class ParameterMentionWithoutValue(BaseModel):
    parameter_name: str = Field(..., description="Name as mentioned in text.")
    symbol: Optional[str] = Field(None)
    availability: str = Field(..., description="'mentioned_but_not_numerically_reported', 'supplement_only'")
    source: Optional[str] = Field(None, description="e.g., 'main_text', 'methods'")
    requires_supplement: Optional[bool] = Field(None)
    context_quote: Optional[str] = Field(None)

# ─── Other Extractions ─────────────────────────────────────────────────────────

class ValidationResult(BaseModel):
    metric: str = Field(..., description="e.g., 'Cmax', 'AUC', 'Tmax'")
    formulation: Optional[str] = Field(None)
    species: Optional[str] = Field(None)
    value: Optional[float] = Field(None)
    unit: Optional[str] = Field(None)
    source_type: str = Field(..., description="Must be 'observed' or 'simulated'")
    provenance: Provenance

class QualitativeFinding(BaseModel):
    finding_type: str = Field(..., description="e.g., 'relative_model_output_comparison'")
    metric: Optional[str] = Field(None)
    formulation: Optional[str] = Field(None)
    comparator: Optional[str] = Field(None)
    species: Optional[str] = Field(None)
    relative_change: Optional[str] = Field(None, description="e.g. '2.0-2.5x higher'")
    qualifier: Optional[str] = Field(None, description="e.g. 'about'")
    provenance: Provenance

class DoseEvent(BaseModel):
    compound: Optional[str] = Field(None, description="The chemical being dosed.")
    dose: float = Field(..., description="Amount of dose administered")
    dose_unit: str = Field(..., description="Unit of dose (e.g., 'mg/kg', 'mg', 'mcg/kg')")
    route: str = Field(..., description="Route of administration (e.g., 'Oral', 'IV', 'Inhalation', 'Dermal', 'Drinking Water')")
    schedule: str = Field(..., description="Dosing schedule (e.g., 'single', 'repeated', 'continuous')")
    interval_h: Optional[float] = Field(None, description="Hours between doses (if repeated)")
    n_doses: Optional[int] = Field(None, description="Number of doses (if repeated)")
    body_weight: Optional[float] = Field(None, description="Body weight in kg (if stated in Methods)")
    duration_h: Optional[float] = Field(None, description="Total simulation duration in hours (if stated)")
    source_quote: Optional[str] = Field(None, description="Verbatim quote from Methods section")

class DosingExtraction(BaseModel):
    dosing: List[DoseEvent] = Field(default_factory=list, description="All dosing events described in the text.")

class SensitivityCoefficient(BaseModel):
    parameter_name: str = Field(..., description="Name of the parameter being perturbed.")
    model_output: str = Field(..., description="The model output metric being evaluated (e.g. 'maternal plasma AUC').")
    compound: Optional[str] = Field(None)
    population: Optional[str] = Field(None, description="e.g. 'Fetus', 'Infant'")
    value: float = Field(..., description="The normalized sensitivity coefficient (can be negative).")
    provenance: Optional[Provenance] = None

# ─── Page Output ───────────────────────────────────────────────────────────────

class ParameterBlock(BaseModel):
    block_name: str = Field(..., description="Name of the section/table block (e.g. 'Physiological parameters (Rat)'). Use 'Text' if from narrative.")
    implied_species: Optional[str] = Field(None, description="Species shared by all rows in this block (e.g. 'rat', 'human').")
    implied_unit_original: Optional[str] = Field(None, description="Unit-as-printed shared by all rows in this block (e.g. 'fraction of cardiac output').")
    parameter_class: Optional[str] = Field(None, description="Class shared by all rows: 'physiological', 'biochemical', or 'compound_specific'.")
    parameters: List[ExtractedParameter] = Field(default_factory=list, description="Parameters belonging to this block.")

class ExtractedPage(BaseModel):
    page_metadata: PageMetadata
    model_classification: ModelClassification
    model_structure: Optional[Structure] = Field(None, description="Compartmental model structure.")
    parameter_blocks: List[ParameterBlock] = Field(default_factory=list, description="Parameters grouped by table blocks/sections. PBPK input parameters ONLY.")
    observed_data: List[ValidationResult] = Field(default_factory=list, description="Observed PK metrics (e.g., observed Cmax, AUC).")
    simulated_data: List[ValidationResult] = Field(default_factory=list, description="Simulated PK metrics (e.g., simulated Cmax, AUC).")
    formulation_characterization: List[FormulationMeasurement] = Field(default_factory=list, description="Physicochemical measurements (contact angle, dissolution). NOT model parameters.")
    qualitative_findings: List[QualitativeFinding] = Field(default_factory=list, description="Relative comparisons or qualitative statements.")
    parameter_mentions_without_values: List[ParameterMentionWithoutValue] = Field(default_factory=list, description="Named PBPK parameters mentioned in text but without numerical values.")
    sensitivity_analysis: List[SensitivityCoefficient] = Field(default_factory=list, description="Sensitivity analysis coefficients.")
    dosing: Optional[List[DoseEvent]] = Field(default=None, description="Dosing events extracted from the methods section.")
