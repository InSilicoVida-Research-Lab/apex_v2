import os
import re

schema_file = "/home/gautam/Desktop/project/apex_v2/pk_pipeline/schemas.py"
with open(schema_file, "r") as f:
    content = f.read()

# Replace the imports
content = content.replace("from typing import List, Optional, Union", "from typing import List, Optional, Union, Literal\nfrom enum import Enum")

# Add the new enums and classes
new_classes = """
# ─── OECD GD 331 Context & Evaluation Classes ───────────────────────────────────

class ProvenanceEnum(str, Enum):
    MEASURED_HERE = "measured_here"
    LITERATURE = "literature"
    IN_VITRO_IVIVE = "in_vitro_ivive"
    PREDICTED_QSAR = "predicted_qsar"
    FITTED = "fitted"
    ASSUMED_DEFAULT = "assumed_default"
    NOT_REPORTED = "not_reported"

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

class ModelStructure(BaseModel):
    reported_compartment_count: Union[int, str] = Field(description="Integer count, or 'not_reported'.")
    compartments: List[str] = Field(description="List of all specific compartments modeled.")
    equations_provided: Literal["text", "supplementary_info", "code_repo", "none"] = Field(
        description="Where are the ODEs/equations provided?"
    )
    allometric_scaling_rules: List[str] = Field(description="Explicit scaling rules stated (e.g., 'QC = QCC * BW^0.75'). Empty list if none.")

class MetabolicPathway(BaseModel):
    parent_compound: str = Field(description="The chemical being metabolized.")
    metabolite_produced: str = Field(description="The specific downstream metabolite. Use 'sink' if not explicitly tracked.")
    enzyme: str = Field(description="Enzyme/pathway responsible (e.g., 'CYP1A2', 'glucuronidation'). Use 'unclear' if not stated.")
    location: str = Field(description="Tissue/compartment where metabolism occurs (e.g., 'Liver', 'Gut').")
    kinetics_type: Literal["clearance_based", "michaelis_menten", "michaelis_menten_with_inhibition", "hill", "mixed", "not_reported"] = Field(
        description="The mathematical form of the metabolic kinetics."
    )
    ivive_used: bool = Field(description="True if In Vitro to In Vivo Extrapolation was used for this pathway.")

"""

# Inject before ExtractedPage
if "# ─── Extracted Parameter" in content:
    content = content.replace("# ─── Extracted Parameter", new_classes + "\n# ─── Extracted Parameter")

# Update ExtractedPage definition
extracted_page_mod = """
class ExtractedPage(BaseModel):
    page_metadata: PageMetadata
    model_classification: ModelClassification
    model_context: Optional[ModelContext] = None
    biological_basis: Optional[BiologicalBasis] = None
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
"""

# Replace ExtractedPage
pattern = re.compile(r"class ExtractedPage\(BaseModel\):.*?(?=\n\n|\Z)", re.DOTALL)
content = pattern.sub(extracted_page_mod.strip(), content)

with open(schema_file, "w") as f:
    f.write(content)

print("Updated schemas.py successfully.")
