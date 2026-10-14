from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, model_validator, field_validator
from typing import Any, Dict, List, Optional, Union, Literal
from enum import Enum

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

ModelType = Literal[
    "pbpk",
    "simple_empirical_compartmental",
    "nca",
    "not_applicable"
]

class ModelClassification(BaseModel):
    model_type: ModelType = Field(description="Must be 'pbpk', 'simple_empirical_compartmental', 'nca' or 'not_applicable'")
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



# ─── Nested Parameter Sub-Models ───────────────────────────────────────────────

class BiologicalContext(BaseModel):
    compound: Optional[str] = Field(
        None, description="Chemical or drug entity (e.g., PFOS, PFOA, PFHxS, DINCH, MINCH, Riluzole). Leave null for compound-independent physiological parameters."
    )
    species: Optional[str] = Field(
        None, description="Explicitly stated species (e.g., Human, Nonhuman primate, Rat, Monkey)."
    )
    subject_species: Optional[str] = Field(
        None, description="Alias for species (e.g., Human, Nonhuman primate, Rat, Monkey)."
    )
    life_stage: Optional[str] = Field(
        None, description="Life stage or physiological state (e.g., Mother, Fetus, Infant, Gestation, Lactation, Adult)."
    )
    formulation: Optional[Union[str, List[str]]] = Field(
        None, description="Specific drug formulation if stated (e.g., Rilutor, ASD). Never merge two formulations into a numeric range."
    )
    compartment: Optional[str] = Field(
        None, description="Target organ, tissue, or fluid compartment (e.g., Liver, Kidney, Filtrate, Plasma, Gut, Fat, Placenta, Milk)."
    )
    organ: Optional[str] = Field(
        None, description="Biological organ (alias for compartment)."
    )
    route: Optional[str] = Field(
        None, description="Route of administration (e.g., Oral, IV, Dermal)."
    )
    population: Optional[str] = Field(
        None, description="Specific cohort or sub-population if stated."
    )

    @model_validator(mode="before")
    @classmethod
    def sync_context_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        d = dict(data)
        if d.get("subject_species") and not d.get("species"):
            d["species"] = d["subject_species"]
        elif d.get("species") and not d.get("subject_species"):
            d["subject_species"] = d["species"]
        if d.get("compartment") and not d.get("organ"):
            d["organ"] = d["compartment"]
        elif d.get("organ") and not d.get("compartment"):
            d["compartment"] = d["organ"]
        return d

class Uncertainty(BaseModel):
    type: Optional[str] = Field(None, description="e.g., '95% CI', 'SD', 'SE', '+/-'")
    lower: Optional[float] = Field(None, description="Lower bound of CI.")
    upper: Optional[float] = Field(None, description="Upper bound of CI, if applicable.")
    absolute: Optional[float] = Field(None, description="Absolute variance value, e.g. the 2 in '10 +/- 2'.")
    raw_text: Optional[str] = Field(None, description="The original unparsed uncertainty text.")

class QuantitativeData(BaseModel):
    value_text: Optional[str] = Field(
        None, description="Exact verbatim string printed in the table cell or text (e.g., '0.21 (0.18, 0.25)', '56.9 - 70', '0.008b', '4.00E-04')."
    )
    value: Optional[float] = Field(
        None, description="Primary point estimate as a pure float. Leave null if the cell is purely a dynamic start-to-end range or symbolic equation."
    )
    start_value: Optional[float] = Field(
        None, description="Initial numerical value for time-varying physiological parameters (e.g., 56.9 in '56.9 - 70' during gestation)."
    )
    end_value: Optional[float] = Field(
        None, description="Final numerical value for time-varying physiological parameters (e.g., 70.0 in '56.9 - 70' or 2.4 in '3.2 - 2.4')."
    )
    ci_low: Optional[float] = Field(
        None, description="Lower bound of confidence interval or uncertainty range (e.g., 0.18 in '0.21 (0.18, 0.25)')."
    )
    ci_high: Optional[float] = Field(
        None, description="Upper bound of confidence interval or uncertainty range (e.g., 0.25 in '0.21 (0.18, 0.25)')."
    )
    variance: Optional[float] = Field(
        None, description="Standard deviation (SD), standard error (SE), or CV% if reported."
    )
    variance_type: Optional[str] = Field(
        None, description="Type of variance reported (e.g., 'SD', 'SE', 'CV%', '95% CI')."
    )
    uncertainty: Optional[Uncertainty] = Field(
        None, description="Confidence interval, standard deviation, or other uncertainty metrics."
    )
    unit: Optional[str] = Field(
        None, description="Exact unit of measurement (e.g., 'kg', 'L/h/kg^0.74', 'fraction of BW', 'fraction of QC', 'dimensionless')."
    )
    unit_original: Optional[str] = Field(
        None, description="Unit exactly as printed in the source (e.g., '1/h/kg^0.25'). NEVER convert or interpret."
    )
    unit_standardized: Optional[str] = Field(
        None, description="Standardized/normalized unit (e.g., 'h^-1 kg^-0.25')."
    )
    unit_inherited: bool = Field(
        False, description="True if the unit was inherited from a group subheader or table caption."
    )
    value_qualifier: Optional[str] = Field(
        None, description="Qualifier printed with the value (e.g., 'Optimized', 'Assumed (PFOS)', 'Fixed', 'initial', 'increasing across gestation')."
    )
    footnote_marker: Optional[str] = Field(
        None, description="Trailing footnote symbol or letter stripped from the number (e.g., 'a', 'b', '*')."
    )
    normalization_basis: Optional[str] = Field(
        None, description="E.g., 'cardiac_output', 'body_weight', 'tissue_plasma_ratio'."
    )

    @model_validator(mode="before")
    @classmethod
    def sync_quantitative_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        d = dict(data)
        if d.get("unit") and not d.get("unit_original"):
            d["unit_original"] = d["unit"]
        elif d.get("unit_original") and not d.get("unit"):
            d["unit"] = d["unit_original"]
        if (d.get("ci_low") is not None or d.get("ci_high") is not None) and not d.get("uncertainty"):
            d["uncertainty"] = {
                "lower": d.get("ci_low"),
                "upper": d.get("ci_high"),
                "type": d.get("variance_type") or "95% CI"
            }
        elif d.get("uncertainty") and isinstance(d["uncertainty"], dict):
            u = d["uncertainty"]
            if d.get("ci_low") is None and u.get("lower") is not None:
                d["ci_low"] = u.get("lower")
            if d.get("ci_high") is None and u.get("upper") is not None:
                d["ci_high"] = u.get("upper")
            if d.get("variance_type") is None and u.get("type"):
                d["variance_type"] = u.get("type")
        return d

class Derivation(BaseModel):
    method: Optional[str] = Field(None, description="e.g. 'allometric_scaling', 'rodgers_rowland', 'literature', 'optimized'")
    source_species: Optional[str] = Field(None, description="e.g. 'rat' when human value was derived from rat")
    optimization_target: Optional[str] = Field(None, description="e.g. 'experimental_PK_data', 'Liboux et al.'")

    @model_validator(mode="before")
    @classmethod
    def from_string(cls, data: Any) -> Any:
        if isinstance(data, str):
            return {"method": data}
        return data

class ProvenanceStatus(str, Enum):
    """Controlled vocabulary for how a parameter value was obtained."""

    MEASURED_HERE = "measured_here"
    LITERATURE = "literature"
    IN_VITRO_IVIVE = "in_vitro_ivive"
    PREDICTED_QSAR = "predicted_qsar"
    FITTED = "fitted"
    DERIVED = "derived"
    ASSUMED_DEFAULT = "assumed_default"
    NOT_REPORTED = "not_reported"


_LEGACY_PROVENANCE_STATUS_MAP = {
    "experimental": ProvenanceStatus.MEASURED_HERE.value,
    "measured_here": ProvenanceStatus.MEASURED_HERE.value,
    "literature_derived": ProvenanceStatus.LITERATURE.value,
    "literature": ProvenanceStatus.LITERATURE.value,
    "optimized": ProvenanceStatus.FITTED.value,
    "fitted": ProvenanceStatus.FITTED.value,
    "calculated": ProvenanceStatus.DERIVED.value,
    "allometrically_scaled": ProvenanceStatus.DERIVED.value,
    "similar_to_rat": ProvenanceStatus.DERIVED.value,
    "human_specific": ProvenanceStatus.DERIVED.value,
    "assumed_default": ProvenanceStatus.ASSUMED_DEFAULT.value,
    "assumed_same_as_parent": ProvenanceStatus.ASSUMED_DEFAULT.value,
    "predicted_qsar": ProvenanceStatus.PREDICTED_QSAR.value,
    "in_vitro_ivive": ProvenanceStatus.IN_VITRO_IVIVE.value,
    "not_reported": ProvenanceStatus.NOT_REPORTED.value,
}


class Provenance(BaseModel):
    source_table: Optional[str] = Field(None, description="Explicit table ID (e.g., 'Table 1', 'Table 3', 'Table S1'). Crucial for validation.")
    row_id: Optional[str] = Field(None, description="Identifier of the row in TableEvidence (e.g., 'r1').")
    column_id: Optional[str] = Field(None, description="Identifier of the column in TableEvidence (e.g., 'c1').")
    cell_id: Optional[str] = Field(None, description="Identifier of the cell in TableEvidence (e.g., 'cell_r1_c1').")
    row_path: Optional[List[str]] = Field(None, description="The hierarchical row context (e.g. ['Nonhuman primate', 'Chemical-specific']).")
    column_path: Optional[List[str]] = Field(None, description="The hierarchical column context (e.g. ['Mean (95% CI)', 'PFOS']).")
    source_page: Optional[int] = Field(None)
    source_section: Optional[str] = Field(None, description="e.g. 'Results', 'Methods'.")
    source_location: Optional[str] = Field(None, description="e.g. 'Table I', 'Figure 2', 'Results paragraph'.")
    source_quote: Optional[str] = Field(None, description="Verbatim quote from the source cell/sentence.")
    reference: Optional[str] = Field(None, description="Literature citation like '[17]'.")
    status: Optional[ProvenanceStatus] = Field(None, description="Controlled vocabulary describing how the value was obtained.")
    parameter_status: Optional[str] = Field(None, description="How the parameter was obtained ('Measured', 'Fitted', 'Optimized', 'Fixed', 'Assumed', 'Scaled', 'Literature').")
    status_raw: Optional[str] = Field(None, description="Original legacy/source status label before canonical normalization.")
    derivation: Optional[Derivation] = Field(None, description="Detailed derivation metadata when the parameter was fitted or derived.")
    evidence_directness: Optional[str] = Field(None, description="'direct' or 'inferred'")

    @model_validator(mode="before")
    @classmethod
    def normalize_status(cls, data: Any) -> Any:
        """Accept historical output while serializing a single status vocabulary."""
        if not isinstance(data, dict):
            return data
        normalized = dict(data)
        if normalized.get("derivation") and isinstance(normalized["derivation"], str):
            normalized["derivation"] = {"method": normalized["derivation"]}
        if not normalized.get("status") and normalized.get("parameter_status"):
            p_status = str(normalized["parameter_status"]).strip().lower()
            normalized["status"] = _LEGACY_PROVENANCE_STATUS_MAP.get(p_status, p_status)
        elif normalized.get("status") and not normalized.get("parameter_status"):
            st_val = normalized["status"].value if isinstance(normalized["status"], ProvenanceStatus) else str(normalized["status"])
            normalized["parameter_status"] = st_val.replace("_", " ").capitalize()

        status = normalized.get("status")
        if isinstance(status, ProvenanceStatus):
            status = status.value
        if status:
            status = str(status).strip().lower()
            canonical = _LEGACY_PROVENANCE_STATUS_MAP.get(status, status)
            if canonical != status and not normalized.get("status_raw"):
                normalized["status_raw"] = status
            normalized["status"] = canonical
        return normalized

class ConfidenceScores(BaseModel):
    value_confidence: Optional[str] = Field(None, description="'high', 'medium', 'low'")
    unit_confidence: Optional[str] = Field(None, description="'high', 'medium', 'low'")
    species_confidence: Optional[str] = Field(None, description="'high', 'medium', 'low'")
    formulation_confidence: Optional[str] = Field(None, description="'high', 'medium', 'low'")
    parameter_class_confidence: Optional[str] = Field(None, description="'high', 'medium', 'low'")
    provenance_confidence: Optional[str] = Field(None, description="'high', 'medium', 'low'")


# ─── OECD GD 331 Context & Evaluation Classes ───────────────────────────────────

# Backward-compatible public name retained for callers importing the old enum.
ProvenanceEnum = ProvenanceStatus

class TableColumn(BaseModel):
    column_id: str
    path: List[str]
    index: int

class TableRow(BaseModel):
    row_id: str
    path: List[str]
    index: int

class TableCell(BaseModel):
    cell_id: str
    row_id: str
    column_id: str
    text: str
    numeric_value: Optional[float] = None
    unit: Optional[str] = None
    qualifier: Optional[str] = None
    uncertainty_text: Optional[str] = None

class TableEvidence(BaseModel):
    evidence_status: Optional[str] = Field(None, description="'success' or 'failed'")
    needs_review: bool = Field(False)
    error: Optional[str] = Field(None, description="Error message if reconstruction failed.")
    table_id: Optional[str] = Field(None, description="Explicit table ID (e.g., 'Table 1', 'Table 3', 'Table S1').")
    title: Optional[str] = Field(None, description="The complete table title/caption.")
    columns: List[TableColumn] = Field(default_factory=list, description="List of structured column headers.")
    rows: List[TableRow] = Field(default_factory=list, description="List of structured row headers.")
    cells: List[TableCell] = Field(default_factory=list, description="List of individual cells with their locations and values.")
    subject_compounds: List[str] = Field(default_factory=list, description="All primary compounds explicitly the subject of this table.")
    footnote_compounds: List[str] = Field(default_factory=list, description="Compounds mentioned only in footnotes/references (e.g., 'assumed from PFOS').")
    referenced_compounds: List[str] = Field(default_factory=list, description="Compounds mentioned as references or comparisons.")
    species: List[str] = Field(default_factory=list, description="All species explicitly identified in this table's structure.")
    populations: List[str] = Field(default_factory=list, description="All populations explicitly identified in this table's structure.")
    footnotes: List[str] = Field(default_factory=list, description="List of all footnotes attached to this table.")
    source_page: Optional[int] = Field(None)
    source_image_path: Optional[str] = Field(None)

class ModelContext(BaseModel):
    model_origin: str = Field(description="Is this 'new', 'adapted from [cite]', or 'reused unchanged'? Use 'not_reported' if unclear.")
    stated_purpose: str = Field(description="The authors' stated context of use (e.g., risk assessment). Use 'not_reported' if unclear.")
    dose_metric: str = Field(description="What metric links to toxicity? (e.g., liver AUC of metabolite). Use 'not_reported' if unclear.")
    
class Assumption(BaseModel):
    description: str = Field(description="The stated assumption (e.g., 'well-stirred compartment', 'flow-limited kinetics')")
    evidence_quote: str = Field(description="Direct verbatim quote from the text where the assumption is stated.")
    source_location: str = Field(description="Page or section where this assumption is located.")

class BiologicalBasis(BaseModel):
    adme_determinants: List[str] = Field(description="Physiological/physicochemical factors driving kinetics.")
    stated_assumptions: List[Assumption] = Field(description="Explicit list of assumptions stated by the authors with direct quotes.")
    specialized_mechanisms: List[str] = Field(description="e.g., renal reabsorption, enterohepatic recirculation. Or 'not_applicable'.")

class CompartmentConnection(BaseModel):
    source: str = Field(..., description="Origin compartment name exactly as labeled.")
    target: str = Field(..., description="Destination compartment name exactly as labeled.")
    rate_or_flow_symbol: Optional[str] = Field(None, description="Governing rate constant or flow symbol (e.g., 'k12', 'Qfil', 'Tm', 'Kt', 'ka').")
    equation: Optional[str] = Field(None, description="Mathematical expression if shown on diagram (e.g., 'Vc = Vcc * BW').")

class ModelStructure(BaseModel):
    reported_compartment_count: Union[int, str, None] = Field(None, description="Integer count, or 'not_reported'.")
    listed_compartment_count: Optional[int] = Field(None, description="Actual number of compartments found.")
    count_consistency: Optional[str] = Field(None, description="'consistent' or 'inconsistent_in_source'")
    compartments: List[Union[str, Compartment]] = Field(default_factory=list, description="List of all specific compartments modeled.")
    connections: List[Union[CompartmentConnection, Connection]] = Field(default_factory=list, description="List of connections between compartments.")
    absorption: Optional[AbsorptionModel] = None
    metabolism: Optional[MetabolismModel] = None
    elimination: Optional[EliminationModel] = None
    unresolved: Optional[List[UnresolvedTopology]] = None
    source_location: Optional[str] = None
    equations_provided: Literal["text", "supplementary_info", "code_repo", "diagram", "none"] = Field("none", description="Where are the ODEs/equations provided?")
    allometric_scaling_rules: List[str] = Field(default_factory=list, description="Explicit scaling rules stated (e.g., 'QC = QCC * BW^0.75'). Empty list if none.")
    scaling_equations: List[str] = Field(default_factory=list, description="Symbolic scaling equations without numeric values.")

    @field_validator("equations_provided", mode="before")
    @classmethod
    def normalize_equations_provided(cls, v: Any) -> str:
        if not v:
            return "none"
        s = str(v).strip().lower()
        if s in ("text", "supplementary_info", "code_repo", "diagram", "none"):
            return s
        if "diagram" in s or "figure" in s:
            return "diagram"
        if "supp" in s:
            return "supplementary_info"
        if "code" in s or "repo" in s or "github" in s:
            return "code_repo"
        if "text" in s or "article" in s or "paper" in s:
            return "text"
        return "none"

class MetabolicPathway(BaseModel):
    parent_compound: str = Field(description="The chemical being metabolized.")
    metabolite_produced: str = Field(description="The specific downstream metabolite. Use 'sink' if not explicitly tracked.")
    enzyme: str = Field(description="Enzyme/pathway responsible (e.g., 'CYP1A2', 'glucuronidation'). Use 'unclear' if not stated.")
    location: str = Field(description="Tissue/compartment where metabolism occurs (e.g., 'Liver', 'Gut').")
    kinetics_type: Literal["clearance_based", "michaelis_menten", "michaelis_menten_with_inhibition", "hill", "mixed", "not_reported"] = Field(
        description="The mathematical form of the metabolic kinetics."
    )
    ivive_used: bool = Field(description="True if In Vitro to In Vivo Extrapolation was used for this pathway.")

class EvaluatorJudgments(BaseModel):
    author_stated_limitations: List[str] = Field(description="Limitations explicitly noted by authors with quotes.")
    missing_standard_assumptions: List[str] = Field(description="Standard assumptions that should be present but are missing from the text.")
    data_independence_assessment: str = Field(description="Were the evaluation datasets truly independent of the calibration data? Provide rationale.")
    overall_confidence: Literal["high", "medium", "low"] = Field(description="Overall confidence in the reproducibility of this model.")



# ─── Extracted Parameter ───────────────────────────────────────────────────────

class ExtractedParameter(BaseModel):
    parameter_id: Optional[str] = Field(None, description="Unique composite ID (auto-generated post-extraction).")
    parameter_class: Optional[str] = Field(
        None,
        description=(
            "Broad semantic class. Must be exactly one of: "
            "'physiological' (describes the biological organism — body weight, organ volumes, blood flows, cardiac output, GFR, hematocrit, milk flow); "
            "'biochemical' (drug-specific interaction with biology — partition coefficients, fu, Vmax, Km, clearances, absorption rate, half-life, bioavailability, transfer rates, relative activity factors); "
            "'compound_specific' (pure physicochemical properties independent of biology — MW, logP, solubility, pKa). "
            "Blood flows and organ volumes are ALWAYS 'physiological'. "
            "Clearances (renal, metabolic, biliary), half-life, distribution volume, bioavailability, absorption rates are ALWAYS 'biochemical'. "
            "logP is 'compound_specific'."
        )
    )
    parameter_subclass: Optional[str] = Field(
        None,
        description=(
            "Specific sub-category from the canonical vocabulary. Always assign the closest match. "
            "PHYSIOLOGICAL subclasses: "
            "'body_weight' (BW, body weight in kg); "
            "'cardiac_output' (QCC, QCO — cardiac output coefficient); "
            "'organ_blood_flow_fraction' (fractional flow, e.g. QLiv/QC, dimensionless or L/h/kg^x); "
            "'organ_blood_flow' (absolute flow in L/h or mL/min); "
            "'organ_volume_fraction' (fractional volume, e.g. VLiv/BW in L/kg); "
            "'organ_volume' (absolute volume in L or mL); "
            "'glomerular_filtration_rate' (GFR in L/h or mL/min); "
            "'hematocrit' (HCT, fraction); "
            "'milk_flow' (volume of milk produced per time); "
            "'urine_production' (urine flow rate). "
            "BIOCHEMICAL subclasses: "
            "'partition_coefficient' (Kp, tissue:plasma ratio); "
            "'fraction_unbound' (fu, fup, fub — free drug fraction); "
            "'absorption_rate_constant' (ka, Kabs — first-order absorption rate, h^-1); "
            "'gastric_emptying_rate' (GE, kGE — gastric emptying rate constant); "
            "'fecal_elimination_rate_constant' (Kfeces, kfec — fecal elimination rate); "
            "'biliary_elimination_rate' (biliary/bile elimination rate); "
            "'urinary_excretion_rate' (urinary clearance or excretion rate constant); "
            "'renal_clearance' (CLr, GFR-based renal clearance); "
            "'maximal_velocity' (Vmax, Tmc, Tm — maximal transport/metabolic rate); "
            "'michaelis_menten_constant' (Km, Kt — Michaelis constant or affinity constant); "
            "'distribution_volume' (Vd, Vc, Vt, VCC, Vfil — volume of distribution or compartment volume); "
            "'distribution_rate' (k12, k21, inter-compartmental transfer rate constants, h^-1); "
            "'elimination_half_life' (t1/2 — elimination half-life); "
            "'bioavailability' (F, bioAv — oral bioavailability fraction); "
            "'transfer_rate' (placental, lactational or compartmental transfer coefficient); "
            "'relative_activity_factor' (RAF, ISEF); "
            "'microsomal_protein_yield' (MPPGL — microsomal protein per gram liver); "
            "'fraction_metabolized' (fm — fraction of drug metabolized via pathway); "
            "'ptc_protein' (proximal tubule cell protein content). "
            "COMPOUND_SPECIFIC subclasses: "
            "'logP' (octanol-water partition coefficient); "
            "'half_life' (measured/reported half-life as compound property); "
            "'calibration_parameter' (parameter optimized as a tuning/fitting target). "
            "Use null only if no listed subclass applies."
        )
    )
    parameter_name: Optional[str] = Field(
        None, description="Full descriptive parameter name. If under a group header, prepend the group header (e.g., 'Blood flow to organ - Liver')."
    )
    parameter_name_original: Optional[str] = Field(
        None, description="Full descriptive name exactly as printed in the source."
    )
    parameter_name_standardized: Optional[str] = Field(
        None,
        description=(
            "Standardized snake_case name (ALWAYS fill this). Examples: "
            "'body_weight', 'cardiac_output', 'liver_blood_flow_fraction', 'liver_volume_fraction', "
            "'kidney_blood_flow_fraction', 'fat_volume_fraction', "
            "'partition_coefficient_liver', 'partition_coefficient_kidney', "
            "'fraction_unbound_plasma', 'absorption_rate_constant', "
            "'maximal_resorption_rate', 'michaelis_menten_constant', "
            "'central_compartment_volume', 'second_compartment_volume', 'filtrate_compartment_volume', "
            "'intercompartmental_rate_k12', 'intercompartmental_rate_k21', "
            "'oral_bioavailability', 'elimination_half_life', 'glomerular_filtration_rate', "
            "'fraction_cardiac_output_to_filtrate', 'fraction_unbound_in_plasma'. "
            "For organ-specific Kp: 'partition_coefficient_<organ>'. "
            "Derive from parameter_name_original if no standard exists."
        )
    )
    symbol: Optional[str] = Field(
        None, description="Exact mathematical symbol as printed (e.g., 'BW', 'QCC', 'Tmc', 'Kt', 'VGutC', 'Kabs')."
    )
    symbol_original: Optional[str] = Field(None, description="Mathematical symbol exactly as printed (e.g., 'QCC', 'Vmax', 'Kp_liver', 'BW'). Null only if no symbol appears in the source.")
    symbol_standardized: Optional[str] = Field(None, description="Standardized symbol in common PBPK notation (e.g., 'QCC', 'Kp_liver', 'fu', 'BW'). Copy from symbol_original if already standard. Null only if symbol_original is null.")
    pbpko_id: Optional[str] = Field(None, description="Ontology term ID (e.g., PBPKO:0000001).")
    pbpko_iri: Optional[str] = Field(None, description="Ontology IRI.")
    ontology_match_type: Optional[str] = Field(None, description="'exact', 'fuzzy', 'unmatched'.")

    context: BiologicalContext = Field(..., description="Biological and study context.")
    quantitative_data: QuantitativeData = Field(..., description="Numerical values and units.")
    provenance: Provenance = Field(..., description="Source location and status.")
    confidence: Optional[Union[str, ConfidenceScores]] = Field(default_factory=ConfidenceScores)
    needs_review: bool = Field(False)

    @model_validator(mode="before")
    @classmethod
    def sync_parameter_names(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        d = dict(data)
        if d.get("parameter_name") and not d.get("parameter_name_original"):
            d["parameter_name_original"] = d["parameter_name"]
        elif d.get("parameter_name_original") and not d.get("parameter_name"):
            d["parameter_name"] = d["parameter_name_original"]
        if d.get("symbol") and not d.get("symbol_original"):
            d["symbol_original"] = d["symbol"]
        elif d.get("symbol_original") and not d.get("symbol"):
            d["symbol"] = d["symbol_original"]
        return d

class ExtractionResult(BaseModel):
    model_classification: Literal["pbpk", "simple_empirical_compartmental", "not_applicable"]
    parameters: List[ExtractedParameter] = Field(default_factory=list)
    structure: Optional[ModelStructure] = None
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
    page_metadata: PageMetadata = Field(default_factory=PageMetadata)
    model_classification: ModelClassification
    model_context: Optional[ModelContext] = None
    biological_basis: Optional[BiologicalBasis] = None
    table_evidence: List[TableEvidence] = Field(default_factory=list, description="Reconstructed structured representation of tables on this page.")
    model_structure: Optional[ModelStructure] = Field(None, description="Compartmental model structure.")
    metabolic_pathways: List[MetabolicPathway] = Field(default_factory=list)
    parameter_blocks: List[ParameterBlock] = Field(default_factory=list, description="Parameters grouped by table blocks/sections. PBPK input parameters ONLY.")
    observed_data: List[ValidationResult] = Field(default_factory=list, description="Observed PK metrics (e.g., observed Cmax, AUC).")
    simulated_data: List[ValidationResult] = Field(default_factory=list, description="Simulated PK metrics (e.g., simulated Cmax, AUC).")
    formulation_characterization: List[FormulationMeasurement] = Field(default_factory=list, description="Physicochemical measurements (contact angle, dissolution). NOT model parameters.")
    qualitative_findings: List[QualitativeFinding] = Field(default_factory=list, description="Relative comparisons or qualitative statements.")
    parameter_mentions_without_values: List[ParameterMentionWithoutValue] = Field(default_factory=list, description="Named PBPK parameters mentioned in text but without numerical values.")
    sensitivity_analysis: List[SensitivityCoefficient] = Field(default_factory=list, description="Sensitivity analysis coefficients.")
    dosing: Optional[List[DoseEvent]] = Field(default=None, description="Dosing events extracted from the methods section.")


# ─── Lightweight Table Extraction Schema (for Table Prompts) ────────────────────

class ParameterClass(str, Enum):
    PHYSIOLOGICAL = "physiological"
    BIOCHEMICAL = "biochemical"
    COMPOUND_SPECIFIC = "compound_specific"

class TableParameterContext(BaseModel):
    compound: Optional[str] = Field(None, description="Chemical or drug entity (e.g. PFOS, PFOA). Leave null for compound-independent physiological parameters.")
    species: Optional[str] = Field(None, description="Explicitly stated species (e.g. Human, Nonhuman primate, Rat, Monkey).")
    life_stage: Optional[str] = Field(None, description="Life stage or physiological state (e.g. Mother, Fetus, Infant, Gestation, Adult).")
    formulation: Optional[Union[str, List[str]]] = Field(None, description="Specific drug formulation if stated (e.g. Rilutor, ASD). Never merge two formulations into a range.")
    compartment: Optional[str] = Field(None, description="Target organ, tissue, or fluid compartment (e.g. Liver, Kidney, Plasma, Filtrate, Gut, Fat).")
    route: Optional[str] = Field(None, description="Route of administration (e.g. Oral, IV, Dermal).")
    population: Optional[str] = Field(None, description="Specific cohort or sub-population if stated.")

class TableQuantitativeData(BaseModel):
    value_text: Optional[str] = Field(None, description="Exact verbatim text printed in the table cell (e.g. '0.21 (0.18, 0.25)', '5a', '4.00E-04').")
    value: Optional[float] = Field(None, description="Primary point estimate as a pure float.")
    start_value: Optional[float] = Field(None, description="Initial numerical value for time-varying physiological ranges (e.g. 56.9 in '56.9 - 70').")
    end_value: Optional[float] = Field(None, description="Final numerical value for time-varying physiological ranges (e.g. 70.0 in '56.9 - 70').")
    ci_low: Optional[float] = Field(None, description="Lower bound of confidence interval (e.g. 0.18 in '0.21 (0.18, 0.25)').")
    ci_high: Optional[float] = Field(None, description="Upper bound of confidence interval (e.g. 0.25 in '0.21 (0.18, 0.25)').")
    unit: Optional[str] = Field(None, description="Exact unit printed or inherited (e.g. 'L/h/kg^0.74', 'mg/L', 'fraction of BW').")
    unit_inherited: bool = Field(False, description="True if unit was inherited from a group header or table caption.")
    value_qualifier: Optional[str] = Field(None, description="Qualifier printed with value (e.g. 'Optimized', 'Fixed', '<').")
    footnote_marker: Optional[str] = Field(None, description="Trailing footnote symbol or letter stripped from the number (e.g. 'a', 'b', '*').")
    normalization_basis: Optional[str] = Field(None, description="Normalization basis (e.g. 'cardiac_output', 'body_weight').")

class TableProvenance(BaseModel):
    source_table: Optional[str] = Field(None, description="Explicit table ID (e.g. 'Table 1', 'Table 3'). Crucial for verification.")
    row_id: Optional[str] = Field(None, description="Identifier of the row in TableEvidence (e.g. 'r1').")
    column_id: Optional[str] = Field(None, description="Identifier of the column in TableEvidence (e.g. 'c1').")
    cell_id: Optional[str] = Field(None, description="Identifier of the cell in TableEvidence (e.g. 'cell_r1_c1').")
    row_path: Optional[List[str]] = Field(None, description="Hierarchical row context path.")
    column_path: Optional[List[str]] = Field(None, description="Hierarchical column context path.")
    source_quote: Optional[str] = Field(None, description="Verbatim text from source cell.")
    reference: Optional[str] = Field(None, description="Literature citation or reference (e.g. 'Wambaugh et al. (2013)', '[17]').")
    status: Optional[ProvenanceStatus] = Field(None, description="Controlled vocabulary: 'measured_here', 'literature', 'fitted', 'derived', 'assumed_default', 'in_vitro_ivive', 'predicted_qsar', 'not_reported'.")

class TableExtractedParameter(BaseModel):
    parameter_class: Optional[ParameterClass] = Field(None, description="Broad class: 'physiological' (organ volume, blood flow, BW, GFR), 'biochemical' (Kp, fu, clearance, Vmax, Km, Vc, ka, half-life), or 'compound_specific' (logP, MW).")
    parameter_subclass: Optional[str] = Field(None, description="Specific canonical subclass (e.g. 'body_weight', 'cardiac_output', 'organ_blood_flow_fraction', 'organ_volume_fraction', 'partition_coefficient', 'fraction_unbound', 'distribution_volume', 'distribution_rate', 'absorption_rate_constant', 'maximal_velocity', 'michaelis_menten_constant', 'bioavailability', 'elimination_half_life').")
    parameter_name: Optional[str] = Field(None, description="Descriptive parameter name. If under a group header, prepend it (e.g. 'Blood flow - Liver').")
    parameter_name_standardized: Optional[str] = Field(None, description="Standardized snake_case name (e.g. 'body_weight', 'cardiac_output', 'partition_coefficient_liver', 'central_compartment_volume').")
    symbol: Optional[str] = Field(None, description="Mathematical symbol as printed (e.g. 'BW', 'QCC', 'Tmc', 'Kt', 'k12').")
    symbol_standardized: Optional[str] = Field(None, description="Standardized symbol in common PBPK notation (e.g. 'BW', 'QCC', 'Kp_liver').")
    context: TableParameterContext
    quantitative_data: TableQuantitativeData
    provenance: TableProvenance

class TableParameterBlock(BaseModel):
    block_name: str = Field(..., description="Section/block name (e.g. 'Nonhuman primate', 'Physiological parameters').")
    implied_species: Optional[str] = Field(None, description="Species shared across this block.")
    implied_unit: Optional[str] = Field(None, description="Unit shared across this block.")
    parameter_class: Optional[str] = Field(None, description="Class shared across this block.")
    parameters: List[TableExtractedParameter] = Field(default_factory=list, description="Extracted parameters belonging to this block.")

class TableValidationResult(BaseModel):
    metric: str = Field(..., description="Observed PK metric name, e.g. 'Cmax', 'AUC', 'Tmax'")
    value: Optional[float] = None
    unit: Optional[str] = None
    source_type: Literal["observed", "simulated"] = "observed"
    provenance: Optional[TableProvenance] = None

class TableExtractionPage(BaseModel):
    page_metadata: Optional[PageMetadata] = None
    model_classification: ModelClassification = Field(..., description="Model classification: 'pbpk', 'simple_empirical_compartmental', or 'not_applicable'.")
    parameter_blocks: List[TableParameterBlock] = Field(default_factory=list, description="Parameters grouped by table section/blocks. PBPK input parameters ONLY.")
    observed_data: List[TableValidationResult] = Field(default_factory=list, description="Observed clinical PK metrics if reported in the table.")
    simulated_data: List[TableValidationResult] = Field(default_factory=list, description="Simulated PK metrics if reported in the table.")


# ─── Lightweight Diagram Extraction Schema (for Diagram / Figure Prompts) ─────

class DiagramExtractionPage(BaseModel):
    page_metadata: Optional[PageMetadata] = None
    model_classification: ModelClassification = Field(
        ..., description="Model classification: 'pbpk', 'simple_empirical_compartmental', or 'not_applicable'."
    )
    model_structure: Optional[ModelStructure] = Field(
        default_factory=ModelStructure,
        description="Boxes and arrows: compartments, connections, and scaling equations."
    )


# ─── Canonical Document Output ────────────────────────────────────────────────

class ExtractedDocument(BaseModel):
    """Validated, serializable document-level output of the extraction pipeline.

    ``model_parameters`` is canonical. The two category lists are materialized
    views retained for backwards-compatible consumers and must agree exactly
    with the canonical list.
    """

    model_config = ConfigDict(extra="forbid")

    page_metadata: PageMetadata = Field(default_factory=PageMetadata)
    model_classification: ModelClassification = Field(
        default_factory=lambda: ModelClassification(model_type="not_applicable")
    )
    model_context: Optional[ModelContext] = None
    biological_basis: Optional[BiologicalBasis] = None
    model_structure: Optional[ModelStructure] = None
    metabolic_pathways: List[MetabolicPathway] = Field(default_factory=list)
    model_parameters: List[ExtractedParameter] = Field(default_factory=list)
    observed_data: List[ValidationResult] = Field(default_factory=list)
    simulated_data: List[ValidationResult] = Field(default_factory=list)
    formulation_characterization: List[FormulationMeasurement] = Field(default_factory=list)
    qualitative_findings: List[QualitativeFinding] = Field(default_factory=list)
    parameter_mentions_without_values: List[ParameterMentionWithoutValue] = Field(default_factory=list)
    sensitivity_analysis: List[SensitivityCoefficient] = Field(default_factory=list)
    table_evidence: List[TableEvidence] = Field(default_factory=list)
    dosing: List[DoseEvent] = Field(default_factory=list)
    system_specific_parameters: List[ExtractedParameter] = Field(default_factory=list)
    compound_specific_parameters: List[ExtractedParameter] = Field(default_factory=list)
    evaluator_judgments: Optional[EvaluatorJudgments] = None
    verification: Optional[Dict[str, Any]] = None
    llm_verification: Optional[Dict[str, Any]] = None
    laya_filter_summary: Optional[Dict[str, Any]] = None
    wevisdoc_summary: Optional[Dict[str, Any]] = None
    ingestion_source: Optional[str] = None
    ingestion_source_type: Optional[str] = None

    @model_validator(mode="after")
    def validate_canonical_parameter_views(self, info: ValidationInfo) -> "ExtractedDocument":
        parameter_ids = [p.parameter_id for p in self.model_parameters if p.parameter_id]
        if len(parameter_ids) != len(set(parameter_ids)):
            raise ValueError("model_parameters contains duplicate parameter_id values")

        expected_system = [p for p in self.model_parameters if p.parameter_class == "physiological"]
        expected_compound = [p for p in self.model_parameters if p.parameter_class != "physiological"]
        if self.system_specific_parameters != expected_system:
            raise ValueError("system_specific_parameters must exactly match the physiological model_parameters view")
        if self.compound_specific_parameters != expected_compound:
            raise ValueError("compound_specific_parameters must exactly match the non-physiological model_parameters view")

        allow_empty = bool((info.context or {}).get("allow_empty_parameters"))
        if (
            not allow_empty
            and not self.model_parameters
            and self.model_classification.model_type in {"pbpk", "simple_empirical_compartmental"}
        ):
            raise ValueError("a PK/PBPK document cannot be finalized with zero model_parameters")
        return self
