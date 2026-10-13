import torch
from typing import List
from PIL import Image
import json
import os

from .schemas import ExtractedPage, ExtractedParameter, TableEvidence
from .config import logger, Config
from pydantic import ValidationError

# Note: These imports will require a GPU environment with sglang and colpali_engine installed.
try:
    from colpali_engine.models import ColQwen2_5, ColQwen2_5_Processor
except ImportError:
    logger.warning("colpali_engine not found. Please install `colpali-engine`.")

try:
    import sglang as sgl
except ImportError:
    logger.warning("sglang not found. Please install `sglang`.")


class ColQwenRetriever:
    """
    Implementation of ColQwen2.5-7B Intra-Document Retriever.
    Embeds document pages into visual patches and performs a MaxSim vector search.
    """
    def __init__(self):
        logger.info("Initializing ColQwenRetriever...")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_name = "vidore/colqwen2.5-v0.2"
        
        try:
            # Load the model and processor in FP16 as per the architecture spec
            logger.info(f"Loading {self.model_name} in FP16 precision...")
            self.model = ColQwen2_5.from_pretrained(
                self.model_name, 
                torch_dtype=torch.float16, 
                device_map="auto"
            ).eval()
            self.processor = ColQwen2_5_Processor.from_pretrained(self.model_name)
            self.is_loaded = True
        except Exception as e:
            logger.error(f"Failed to load ColQwen2.5: {e}")
            self.is_loaded = False
    
    def find_top_pages(self, images: List[Image.Image], query: str = "Pharmacokinetic parameters table", top_k: int = 10, threshold_ratio: float = 0.50) -> List[Image.Image]:
        logger.debug(f"ColQwen: Finding top pages for query '{query}' among {len(images)} images.")
        
        if not images:
            raise ValueError("No images provided to ColQwenRetriever.")

        if not self.is_loaded:
            raise RuntimeError("ColQwenRetriever model is not loaded. Ensure colpali-engine is installed and GPU is available.")

        # 1. Embed all page images
        with torch.no_grad():
            batch_images = self.processor.process_images(images).to(self.model.device)
            image_embeddings = self.model(**batch_images)

        # 2. Embed the text queries (positive and negative)
        negative_query = "References Bibliography"
        with torch.no_grad():
            batch_queries = self.processor.process_queries([query, negative_query]).to(self.model.device)
            query_embeddings = self.model(**batch_queries)

        # 3. Calculate MaxSim for both queries
        # query_embeddings[0] is positive query, query_embeddings[1] is negative query
        pos_query_emb = query_embeddings[0:1]
        neg_query_emb = query_embeddings[1:2]
        
        pos_scores = self.processor.score_multi_vector(pos_query_emb, image_embeddings)[0]
        neg_scores = self.processor.score_multi_vector(neg_query_emb, image_embeddings)[0]
        
        all_scores = []
        for i in range(len(images)):
            p_score = pos_scores[i].item()
            n_score = neg_scores[i].item()
            
            # If the page is highly confident as a Reference section (n_score > p_score)
            # BUT it also has a strong positive score for being a table (p_score > 10.0),
            # do NOT penalize it. It's likely a table embedded inside the references.
            penalty = 0
            if n_score > p_score and p_score < 10.0:
                penalty = 10.0  # massive penalty to push it out of the top-k
                
            final_score = p_score - penalty
            all_scores.append((i, final_score, p_score, n_score))
            
        max_score = max(s for _, s, _, _ in all_scores)
        
        # Log every page score so we can see exactly what ColQwen thinks
        for i, s, p, n in sorted(all_scores, key=lambda x: x[1], reverse=True):
            logger.info(f"  Page {i+1:>2}: final={s:.4f} (pos={p:.4f}, neg={n:.4f})")
        
        # 4. Dual threshold: must pass BOTH a relative AND absolute floor
        #    - relative: must be within 85% of the top-scoring page
        #    - absolute: absolute minimum to reject clearly irrelevant pages (logos, refs)
        #      Set empirically — ColQwen MaxSim scores for PK tables are typically > 15.0
        relative_cutoff = max_score * threshold_ratio
        absolute_floor = max_score * 0.60  # hard floor: never go below 60% of max
        cutoff = max(relative_cutoff, absolute_floor)
        
        top_indices = [
            i for i, s, _, _ in all_scores
            if s >= cutoff
        ]
                
        # Sort by score descending and limit to top_k
        top_indices.sort(key=lambda i: all_scores[i][1], reverse=True)
        
        # Fallback: guarantee at least 4 pages (or all pages if fewer than 4) are kept for tables
        min_pages = min(4, len(all_scores))
        if len(top_indices) < min_pages:
            sorted_all = sorted(range(len(all_scores)), key=lambda i: all_scores[i][1], reverse=True)
            top_indices = sorted_all[:min_pages]
            
        top_indices = top_indices[:top_k]
        
        # Fallback if somehow empty
        if not top_indices:
            best_idx = max(range(len(all_scores)), key=lambda i: all_scores[i][2])
            top_indices = [best_idx]
            
        logger.info(
            f"ColQwen: Max={max_score:.4f}, cutoff={cutoff:.4f} "
            f"(ratio={threshold_ratio}). Selected pages: {[i+1 for i in top_indices]}"
        )
        print(f"   -> 📊 ColQwen scores — Max: {max_score:.2f}, Cutoff: {cutoff:.2f}. "
              f"Keeping pages: {[i+1 for i in top_indices]}")
        
        return [images[i] for i in top_indices]


from .schemas import ExtractedPage, ExtractedParameter

SYSTEM_PROMPT_TEMPLATE = """You are a scientific literature extraction engine.

Your task is to extract scientifically meaningful model parameters, experimental values,
and model outputs from research papers while preserving the exact context in which
each value is reported.

ACCURACY IS MORE IMPORTANT THAN COMPLETENESS.

Never guess, infer, merge, relocate, or reinterpret a value when its context is unclear.
If a value cannot be assigned confidently to the correct parameter, compound,
species, population, compartment, route, table, or model context, mark it as
needs_review=true rather than guessing.

==================================================
1. CORE EXTRACTION PRINCIPLE
==================================================

A numerical value MUST NEVER be extracted by itself.

Every extracted value must be associated with its complete semantic path:

Document
→ Section
→ Table/Figure
→ Table title
→ Row group / hierarchical row headers
→ Column group / hierarchical column headers
→ Parameter
→ Compound
→ Species
→ Life stage / population
→ Route / formulation
→ Value
→ Unit
→ Uncertainty
→ Estimation/status
→ Provenance

Treat the table structure as part of the scientific meaning of the value.

A value is not considered correctly extracted unless its complete context is also
correctly identified.

==================================================
2. TABLE STRUCTURE MUST BE RECONSTRUCTED FIRST
==================================================

Before extracting individual parameters from a table:

1. Identify the table number or identifier.
2. Identify the complete table title/caption.
3. Identify all column headers.
4. Identify merged and multi-level column headers.
5. Identify all row groups and hierarchical row headers.
6. Identify species, compound, population, treatment, dose, time, compartment,
   endpoint, or other contextual groups.
7. Identify units and whether units apply to an entire column or individual rows.
8. Identify footnotes and determine exactly what rows/cells they modify.
9. Reconstruct the logical table grid before extracting values.

Do NOT assume that the text order produced by PDF extraction represents the visual
table order.

Do NOT use proximity in extracted text as a substitute for table structure.

==================================================
3. HIERARCHICAL TABLES
==================================================

Many scientific tables contain hierarchical information such as:

Species
  → Variable type
      → Parameter
          → Compound A value
          → Compound B value

or:

Treatment
  → Dose
      → Time
          → Biomarker

or:

Population
  → Sex
      → Parameter

Preserve every level of the hierarchy.

A value inherits context only from the row/column/group hierarchy that actually
contains it.

Never carry a context from one row group, species group, compound group, or table
section into another unless the document explicitly indicates that the context is
shared.

==================================================
4. MULTIPLE COMPOUNDS OR CONDITIONS IN COLUMNS
==================================================

If a table contains multiple compound-specific or condition-specific columns,
each value must be mapped to the correct column header.

For example:

Parameter | Compound A | Compound B

must become two independent parameter records:

Parameter + Compound A + Value A
Parameter + Compound B + Value B

Never combine multiple compounds into a single parameter record.

For multi-level headers such as:

Mean (95% CI)
    Compound A
    Compound B

the complete column path must be preserved.

Example:

column_path = ["Mean (95% CI)", "Compound A"]

and

column_path = ["Mean (95% CI)", "Compound B"]

Never assign a value to a compound merely because that compound is mentioned
elsewhere in the row, footnote, citation, or surrounding paragraph.

==================================================
5. TABLE TITLE VS LOCAL TEXT / FOOTNOTES
==================================================

Determine the subject of the table from the table title, caption, and header
structure.

A compound, species, or condition mentioned in a footnote, source column,
citation, parenthetical note, or explanatory sentence MUST NOT automatically
replace the table-level context.

A local mention can describe:

- the source of a value
- an assumption
- a comparator
- a reference compound
- a methodological basis
- a previously published parameter
- a condition under which a value was derived

Do not treat such a mention as the identity of the extracted value unless the
table explicitly establishes that relationship.

==================================================
6. FOOTNOTES
==================================================

Read all footnotes associated with the table.

Determine whether each footnote:

- modifies a specific cell
- modifies a row
- modifies a column
- modifies a species
- modifies a compound
- defines a symbol
- explains an assumption
- explains a transformation
- provides a source
- describes an exception

Do not discard footnotes.

Do not allow a footnote to overwrite the primary table hierarchy unless the
footnote explicitly states that it changes the interpretation of the value.

==================================================
7. ESTIMATES, RANGES, AND UNCERTAINTY
==================================================

Preserve the reported numerical structure exactly.

Examples:

10
0.24 (0.20, 0.30)
10 ± 2
< 5
> 10
10–20
10 [95% CI: 8–12]

Do not reduce:

0.24 (0.20, 0.30)

to only:

0.24

Store:

estimate = 0.24
uncertainty_type = "95% CI"
lower = 0.20
upper = 0.30

Similarly preserve qualifiers such as:

<, >, approximately, median, mean, geometric mean, range, SD, SE, CI, IQR,
credible interval, confidence interval, etc.

Do not convert a range into a point estimate unless explicitly required by the
schema.

==================================================
8. UNITS
==================================================

Extract the original unit exactly as reported before standardizing it.

Never guess a unit.

Be careful with:

- mg/kg
- mg/kg/day
- mg/L
- L/kg
- L/h
- L/h/kg^0.74
- h^-1
- years
- fraction
- %
- ng/mL
- µg/mL

Distinguish:

0.9 as a fraction

from:

90%

unless the paper explicitly establishes their equivalence.

Preserve both original and standardized units where possible.

==================================================
9. SPECIES AND POPULATION CONTEXT
==================================================

Every parameter must retain the correct biological context.

Examples:

human
rat
mouse
nonhuman primate
cynomolgus monkey
male rat
female rat
adult human
pediatric population

Do not generalize a species-specific value to another species.

Do not infer species from the source citation.

==================================================
10. MODEL-SPECIFIC CONTEXT
==================================================

For PBPK, PBTK, TK, compartmental, PK, PD, QSP, or related models, preserve:

- model type
- model version/name
- compartment
- organ/tissue
- physiological parameter
- chemical-specific parameter
- absorption parameter
- distribution parameter
- elimination parameter
- binding parameter
- metabolic process
- renal process
- transfer rate
- clearance parameter
- fitted/fixed/assumed status
- scaling method
- species-scaling method
- calibration target
- estimation method

Do not classify a process as metabolism merely because it occurs in an elimination
compartment.

Use the terminology used by the paper.

==================================================
11. FITTED VS ASSUMED VS LITERATURE VS SCALED
==================================================

Do not treat all reported values as equivalent.

Determine whether each parameter was:

- experimentally measured
- fitted/optimized
- estimated
- assumed
- fixed
- taken from literature
- calculated
- derived
- scaled from another species
- recalibrated
- used as a default
- model output

Preserve the distinction.

For example:

status = "fitted"

is not equivalent to:

status = "literature"

and is not equivalent to:

status = "assumed_default"

==================================================
12. SOURCE PROVENANCE
==================================================

For every extracted value, record the strongest available provenance:

- table number
- figure number
- page
- section
- row/column context
- source quote
- reference/citation if relevant

If a value comes directly from a table, prefer the table as the provenance source.

If a value is derived or calculated from another reported value, explicitly mark it
as derived and preserve the derivation.

Do not present a derived value as if it were directly reported.

==================================================
13. TEXT VS TABLE CONSISTENCY
==================================================

Use surrounding narrative text to interpret table context, but do not silently
replace a table value with a value found elsewhere.

When the text and table appear inconsistent:

1. Preserve the directly reported values separately.
2. Record the apparent discrepancy.
3. Do not reconcile them by guessing.
4. Mark needs_review=true when necessary.

==================================================
14. DUPLICATES
==================================================

Do not automatically treat repeated values as duplicates.

Two identical numerical values may legitimately represent:

- different compounds
- different species
- different populations
- different routes
- different model versions
- different studies
- different tables
- different estimation methods

A record can only be merged when its complete semantic context is identical.

==================================================
15. MISSING INFORMATION
==================================================

If information is absent, use null or the schema's explicit missing-value marker.

Never infer:

- a missing compound
- a missing species
- a missing unit
- a missing uncertainty interval
- a missing route
- a missing parameter value
- a missing model structure

Do not use nearby text to invent missing information.

==================================================
16. AMBIGUOUS TABLES
==================================================

If a table's structure cannot be reconstructed reliably:

- extract what can be established with high confidence
- preserve the raw table context
- set needs_review=true for ambiguous records
- explain the ambiguity in an extraction note

NEVER guess column alignment.

NEVER guess compound assignment.

NEVER guess species assignment.

NEVER guess which parameter belongs to which value.

A partial but correct extraction is preferable to a complete but incorrectly
contextualized extraction.

==================================================
17. MODEL OUTPUTS VS PARAMETERS
==================================================

Distinguish between:

A. Model parameters
such as Vc, Q, ka, k12, k21, CL, Km, Vmax, etc.

B. Physiological parameters
such as body weight, cardiac output, organ volume, blood flow, etc.

C. Experimental/observed data

D. Model predictions/simulations

E. Risk-assessment outputs
such as HED, POD, RfD, BMD, etc.

Do not place model outputs into the parameter list unless the schema explicitly
requires them.

==================================================
18. NO CROSS-TABLE CONTEXT LEAKAGE
==================================================

This is a critical rule.

A value extracted from Table N MUST NOT inherit:

- compound
- species
- population
- parameter
- unit
- model context

from Table N-1, Table N+1, or surrounding text unless the document explicitly
states that the context is shared.

Every table must be independently interpreted.

==================================================
19. CROSS-REFERENCE CHECK
==================================================

Before finalizing an extraction, perform an internal consistency check:

For every record ask:

1. What table/figure does this value come from?
2. What is the table title?
3. What row does it belong to?
4. What column does it belong to?
5. What compound does that column represent?
6. What species/group does the row represent?
7. What unit applies?
8. Is the value fitted, assumed, measured, derived, or calculated?
9. Is uncertainty reported?
10. Could this value plausibly belong to another row/column/group?

If any answer is uncertain, set needs_review=true.

==================================================
20. FINAL QUALITY RULE
==================================================

Never optimize for the number of extracted records.

Optimize for:

context correctness
+ numerical correctness
+ unit correctness
+ provenance correctness
+ biological correctness
+ model-context correctness.

It is better to return 8 completely reliable records than 12 records containing
incorrect compound/species/table assignments.

==================================================
21. MODEL ASSUMPTIONS & BIOLOGICAL BASIS
==================================================

When analyzing narrative text, methods, or model descriptions:

1. Identify explicit modeling assumptions stated by the authors regarding:
   - Compartmental structure (e.g. well-stirred, perfusion-limited, membrane-limited)
   - Distribution kinetics (e.g. instantaneous mixing, deep tissue equilibrium)
   - Clearance & elimination mechanisms (e.g. saturable reabsorption, Michaelis-Menten kinetics, biliary secretion)
   - Binding and partitioning (e.g. constant unbound fraction, linear tissue partitioning)
   - Bioavailability and absorption (e.g. 100% absorption, fixed oral bioavailability)
   - Scaling & extrapolations (e.g. allometric exponent 0.75, in vitro to in vivo extrapolation)

2. For each assumption, populate `biological_basis.stated_assumptions`:
   - `description`: Clear summary of the assumption.
   - `evidence_quote`: Exact verbatim quote from the text where the assumption is stated.
   - `source_location`: Section name or paragraph where stated.

3. Populate `biological_basis.adme_determinants` with key kinetic determinants identified.
4. Populate `biological_basis.specialized_mechanisms` with non-standard mechanisms (e.g. "saturable_reabsorption").

==================================================
22. PARAMETER CLASSIFICATION VOCABULARY
==================================================

For every extracted parameter, assign `parameter_class` and `parameter_subclass` from the
canonical vocabulary below. Always assign the closest match from this list.

PARAMETER CLASS (must be one of three values):

- `physiological`: Describes the biological organism, not the drug.
  Examples: body weight, organ volumes, blood flows, cardiac output, GFR, hematocrit.

- `biochemical`: Drug-specific interaction with physiology.
  Examples: partition coefficients (Kp), free fraction (fu), clearances, absorption rates,
  Vmax, Km, distribution volume, half-life, bioavailability.

- `compound_specific`: Pure physicochemical properties independent of biology.
  Examples: logP, molecular weight, solubility, pKa.

IMPORTANT RULES:
- Blood flows and organ volumes → ALWAYS `physiological`
- Partition coefficients, fu, Vmax, Km, clearances → ALWAYS `biochemical`
- Compartment volumes (Vc, Vt, Vfil) → `biochemical` / `distribution_volume`
- Inter-compartmental rates (k12, k21) → `biochemical` / `distribution_rate`
- logP → `compound_specific` / `logP`

PARAMETER SUBCLASS canonical values:

PHYSIOLOGICAL subclasses:
  body_weight          → BW, body weight in kg
  cardiac_output       → QCC, QCO (cardiac output coefficient, L/h/kg^0.74)
  organ_blood_flow_fraction → Fractional blood flow (e.g. QLiv/QC, dimensionless)
  organ_blood_flow     → Absolute flow (e.g. QLiv in L/h)
  organ_volume_fraction → Fractional volume (e.g. VLiv/BW, L/kg)
  organ_volume         → Absolute volume (e.g. VLiv in L)
  glomerular_filtration_rate → GFR (L/h or mL/min/kg)
  hematocrit           → HCT (fraction)
  milk_flow            → Milk production volume per time
  urine_production     → Urine flow rate

BIOCHEMICAL subclasses:
  partition_coefficient  → Kp, tissue:plasma ratio (dimensionless)
  fraction_unbound       → fu, fup, fub (free fraction in plasma/blood)
  absorption_rate_constant → ka, Kabs (first-order absorption, h^-1)
  gastric_emptying_rate  → GE, kGE (gastric emptying rate constant)
  fecal_elimination_rate_constant → Kfeces, kfec
  biliary_elimination_rate → Bile/biliary excretion rate
  urinary_excretion_rate → Urinary clearance or excretion rate
  renal_clearance        → CLr (GFR-based, L/h)
  maximal_velocity       → Vmax, Tmc, Tm (max transport/metabolic rate, mg/h or nmol/min)
  michaelis_menten_constant → Km, Kt (Michaelis constant or affinity constant)
  distribution_volume    → Vd, Vc, Vt, VCC, Vfil (volume of distribution, L or L/kg)
  distribution_rate      → k12, k21 (inter-compartmental transfer rate, h^-1)
  elimination_half_life  → t1/2 (elimination half-life, years or h or days)
  bioavailability        → F, bioAv (oral bioavailability fraction 0–1)
  transfer_rate          → Placental, lactational or compartmental transfer coefficient
  relative_activity_factor → RAF, ISEF
  microsomal_protein_yield → MPPGL (mg protein/g liver)
  fraction_metabolized   → fm (fraction of drug cleared via specific pathway)
  ptc_protein            → Proximal tubule cell protein content

COMPOUND_SPECIFIC subclasses:
  logP                   → Octanol-water partition coefficient
  half_life              → Reported half-life as compound property
  calibration_parameter  → Optimization target or fitted tuning parameter

For `parameter_name_standardized`, use snake_case. Examples:
  "liver_blood_flow_fraction", "kidney_volume_fraction", "partition_coefficient_liver",
  "fraction_unbound_plasma", "central_compartment_volume", "filtrate_compartment_volume",
  "fraction_cardiac_output_to_filtrate", "oral_bioavailability", "maximal_resorption_rate"

For `symbol_standardized`, use the paper's own symbol if standard; otherwise use the
canonical symbol from the list above. Copy from `symbol_original` if already standard.

==================================================
23. OUTPUT FORMAT
==================================================

Return ONLY valid JSON matching the schema below. No markdown code fences, no commentary.

{schema}
"""

DIAGRAM_PROMPT_TEMPLATE = """You are a pharmacokinetic (PK) model analyzer. You are shown an image of a model structure diagram (e.g., boxes and arrows representing a PBPK or compartmental model) from a scientific paper. 

Your task is strictly to extract the model structure, compartments, and connections shown in this diagram, and return them in the exact JSON schema provided below. 

## INSTRUCTIONS
1. Do NOT attempt to extract numerical pharmacokinetic parameters (like half-life, clearance, or volumes) from this diagram, even if a number is written next to an arrow. 
2. Classify the model using the paper's explicit terminology whenever available. Do not infer PBPK solely from compartment names.
   - If the paper explicitly describes physiological organ-based compartments, blood flows, tissue volumes, or physiologically based scaling, classify as `pbpk`.
   - If the paper explicitly describes an empirical 1-, 2-, or 3-compartment model, classify as `simple_empirical_compartmental`.
   - If classification cannot be established, return `not_applicable`.
3. Fill out the `structure` object with `compartments` and `connections`:
   - **compartments**: Extract every box in the diagram as a compartment. Set `label_raw` to exactly what is written in the box (e.g., "Liver", "Fat", "Slowly perfused"). Set `id` to a short unique string (e.g., "liver", "c1").
   - **connections**: Extract every arrow as a connection. Set `source` and `target` to the `id` of the respective compartments. Set `direction` based on the arrowhead ("forward", "bidirectional"). If an arrow goes to/from outside the model (e.g., an excretion arrow leaving the Liver with no target box), use "external" as the missing `id`. If a label is written on the arrow (e.g., "Q_liver", "CL_int", "IV dose"), put it in `label_raw`.
4. Return an EMPTY `parameter_blocks` array (`"parameter_blocks": []`). Your only goal is to fill out the `model_structure` field and `model_classification`.
5. Return ONLY valid JSON matching the schema below. No markdown code fences, no commentary.

{schema}
"""

TABLE_RECONSTRUCTION_PROMPT_TEMPLATE = """You are a scientific table structural and data cell parser. 
Your task is to reconstruct the explicit visual structure and cell-level data of the table provided in the image and markdown into a strict JSON schema.

## INSTRUCTIONS
1. Extract the full table title into `title` and table identifier into `table_id` (e.g. "Table 1", "Table 3").
2. Categorize all compounds mentioned in the table:
   - `subject_compounds`: All primary chemical substances that this table's columns/rows measure or model.
   - `footnote_compounds`: Chemicals mentioned only in footnotes, citations, or assumptions (e.g. "assumed from PFOS").
   - `referenced_compounds`: Chemicals listed for external comparison or secondary references.
3. Extract all distinct species and populations explicitly mentioned in the table structure.
4. Parse the column headers hierarchically with `column_id` (e.g. "c1", "c2") and `path` (e.g. ["PFHxS", "Mean"]).
5. Parse the row headers hierarchically with `row_id` (e.g. "r1", "r2") and `path` (e.g. ["Nonhuman primate", "Tmc"]).
6. Extract every table cell required to establish an auditable mapping into `cells: List[TableCell]`.
   For every populated data cell record:
   - `cell_id`: Unique identifier (e.g., "cell_r1_c1")
   - `row_id`: Corresponding row ID
   - `column_id`: Corresponding column ID
   - `text`: Exact printed text verbatim (e.g., "0.21 (0.18–0.25)")
   - `numeric_value`: Numeric estimate as float when numeric (e.g., 0.21)
   - `unit`: Unit if explicitly attached to cell or header (e.g., "mg/L")
   - `qualifier`: Qualifiers like '<', '~', 'Fixed', 'Optimized'
   - `uncertainty_text`: Uncertainty substring if present (e.g., "0.18–0.25", "+/- 0.04")
   Do NOT calculate or normalize values.
   Do NOT infer missing values.
   Preserve the cell text exactly.
7. Extract all footnotes verbatim into the `footnotes` array.
8. Return ONLY valid JSON matching the schema below. No markdown code fences, no commentary.

{schema}
"""

class SGLangExtractor:
    """
    Implementation of Qwen3-VL-8B served via SGLang inference engine.
    Enforces structured JSON generation via FSM-constrained decoding (json_schema).
    Uses nested ExtractedParameter schema: BiologicalContext, QuantitativeData, Provenance.
    """
    def __init__(self, use_4bit=True):
        logger.info("Initializing SGLangExtractor...")
        self.use_4bit = use_4bit
        self.model_path = "Qwen/Qwen3-VL-8B-Instruct"
        
        # Check if an external SGLang server is already running
        try:
            import requests
            # Use 127.0.0.1 instead of localhost to avoid IPv6 resolution issues in requests
            resp = requests.get("http://127.0.0.1:30000/health", timeout=2)
            if resp.status_code == 200:
                logger.info("Detected running SGLang server on port 30000. Will use server instead of loading embedded engine.")
                self.use_server = True
                self.server_url = "http://127.0.0.1:30000"
                self.is_loaded = True
                return
        except Exception as e:
            logger.info(f"External SGLang server not detected or unreachable: {e}")
            self.use_server = False
        
        try:
            quant_mode = "awq" if use_4bit else None
            actual_model = self.model_path
            dtype = "float16" if use_4bit else "auto"
            
            if use_4bit and "AWQ" not in self.model_path:
                if "Qwen3" in self.model_path:
                    logger.warning("AWQ version doesn't exist on HF yet, falling back to unquantized bfloat16.")
                    actual_model = self.model_path
                    quant_mode = None
                    dtype = "bfloat16"
                else:
                    logger.warning(f"For SGLang with 4-bit, switching to AWQ model.")
                    actual_model = f"{self.model_path}-AWQ"
                
            logger.info(f"Loading SGLang Engine for {actual_model}...")
            # SGLang Engine configuration with memory limits
            self.engine = sgl.Engine(
                model_path=actual_model,
                quantization=quant_mode,
                dtype=dtype,
                mem_fraction_static=0.5 # Restrict KV cache to 50% to leave room for ColQwen
            )
            self.is_loaded = True
        except Exception as e:
            logger.error(f"Failed to load SGLang engine: {e}")
            self.is_loaded = False

    async def extract_table_evidence(self, image: Image.Image, markdown_context: str, chunk_title: str = "") -> TableEvidence:
        """Pass 1: Extract structural TableEvidence from table crop and markdown."""
        if not getattr(self, "is_loaded", False):
            raise RuntimeError("SGLangExtractor failed to load.")
            
        import time
        start_t = time.time()
        logger.info(f"SGLang: [START] Pass 1 - Table Reconstruction for {chunk_title}...")
        
        import uuid
        import os
        temp_img_path = f"{Config.TEMP_IMAGE_DIR}/sglang_evidence_{uuid.uuid4().hex}.png"
        image.save(temp_img_path, "PNG")
        
        try:
            schema_json = json.dumps(TableEvidence.model_json_schema(), indent=2)
            system_prompt = TABLE_RECONSTRUCTION_PROMPT_TEMPLATE.format(schema=schema_json)
            
            user_instruction = (
                f"Reconstruct this table into the JSON schema. "
                f"Extract all metadata, column headers, row headers, and every individual populated data cell. "
                f"Use the Markdown text provided below as primary transcription evidence and the image as authoritative layout source.\n\n"
                f"Markdown:\n{markdown_context}"
            )
            
            prompt_text = (
                f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
                f"<|im_start|>user\n<|vision_start|><|image_pad|><|vision_end|>{user_instruction}<|im_end|>\n"
                f"<|im_start|>assistant\n"
            )
            
            try:
                debug_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "test", "llm_inputs", "prompts")
                os.makedirs(debug_dir, exist_ok=True)
                safe_title = "".join(c for c in chunk_title if c.isalnum() or c in (' ', '_')).strip()[:30] or "evidence"
                with open(os.path.join(debug_dir, f"{int(time.time()*1000)}_evidence_{safe_title}.txt"), "w", encoding="utf-8") as f:
                    f.write(prompt_text)
            except Exception:
                pass
                
            if getattr(self, "use_server", False):
                import aiohttp
                timeout = aiohttp.ClientTimeout(total=1800)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    payload = {
                        "text": prompt_text,
                        "image_data": temp_img_path,
                        "sampling_params": {
                            "max_new_tokens": 8000,
                            "temperature": 0.0,
                            "repetition_penalty": 1.0,
                            "json_schema": schema_json
                        }
                    }
                    async with session.post(f"{self.server_url}/generate", json=payload) as resp:
                        result = await resp.json()
                        extracted_text = result["text"]
            else:
                response = await self.engine.async_generate(
                    prompt=prompt_text,
                    image_data=temp_img_path,
                    sampling_params={
                        "max_new_tokens": 8000,
                        "temperature": 0.0,
                        "repetition_penalty": 1.0,
                        "json_schema": schema_json
                    }
                )
                extracted_text = response["text"] if isinstance(response, dict) else response.text

            if "</think>" in extracted_text:
                extracted_text = extracted_text.split("</think>")[-1].strip()
            import re
            m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", extracted_text, re.DOTALL)
            if m:
                extracted_text = m.group(1).strip()
            else:
                extracted_text = extracted_text.strip()

            try:
                json_data = json.loads(extracted_text)
                table_evidence = TableEvidence(**json_data)
                table_evidence.evidence_status = "success"
                logger.info(f"SGLang: [END] Pass 1 complete in {time.time() - start_t:.2f}s.")
                return table_evidence
            except Exception as e:
                logger.error(f"Failed to parse TableEvidence: {e}\nRaw Output: {extracted_text}")
                return TableEvidence(evidence_status="failed", needs_review=True, table_id=None, error=str(e))
        except Exception as e:
            logger.error(f"Error during extract_table_evidence: {e}")
            return TableEvidence(evidence_status="failed", needs_review=True, table_id=None, error=str(e))
        finally:
            if os.path.exists(temp_img_path):
                try:
                    os.remove(temp_img_path)
                except Exception:
                    pass

    def _compact_validation_error(self, exc: Exception) -> str:
        """Format validation errors into a compact, actionable prompt instruction (Factor 9)."""
        if isinstance(exc, ValidationError):
            err_lines = []
            for e in exc.errors()[:5]:
                loc = " -> ".join(str(p) for p in e.get("loc", []))
                msg = e.get("msg", "")
                inp = e.get("input", "")
                inp_str = f" (received: '{str(inp)[:40]}')" if inp is not None and not isinstance(inp, (dict, list)) else ""
                err_lines.append(f"- Location '{loc}': {msg}{inp_str}")
            return "\n".join(err_lines)
        elif isinstance(exc, json.JSONDecodeError):
            return f"- JSON syntax error at line {exc.lineno}, column {exc.colno}: {exc.msg}"
        else:
            return f"- Error: {str(exc)[:200]}"

    def _parse_and_validate_page(self, text: str, table_evidence: TableEvidence = None, chunk_title: str = "", start_t: float = None) -> ExtractedPage:
        """Sanitize output, parse JSON, and validate against ExtractedPage schema."""
        if "</think>" in text:
            text = text.split("</think>")[-1].strip()
        import re
        m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if m:
            clean_text = m.group(1).strip()
        else:
            clean_text = text.strip()

        json_data = json.loads(clean_text)
        extracted_page = ExtractedPage(**json_data)
        if table_evidence:
            extracted_page.table_evidence.append(table_evidence)
        if start_t:
            import time
            duration = time.time() - start_t
            title_log = f" ({chunk_title})" if chunk_title else ""
            n_params = sum(len(b.parameters) for b in extracted_page.parameter_blocks or [])
            logger.info(f"SGLang: Extraction{title_log} complete in {duration:.2f}s. Found {n_params} parameters.")
        return extracted_page

    async def _attempt_repair(
        self,
        base_prompt: str,
        bad_output: str,
        compact_err: str,
        schema_json: str,
        is_image: bool = False,
        image_path: str = None,
        chunk_title: str = "",
        table_evidence: TableEvidence = None
    ) -> ExtractedPage:
        """Factor 9: Feed compacted validation error back into context window for a 1-turn repair."""
        repair_msg = (
            f"Your previous JSON output failed schema validation with these specific error(s):\n"
            f"{compact_err}\n\n"
            f"CRITICAL FIX RULES:\n"
            f"1. Fix the indicated fields to strictly comply with the schema.\n"
            f"2. Ensure all numbers in 'quantitative_data.value' are floats; textual ranges or CI belong in 'uncertainty' or 'value_text'.\n"
            f"3. Return the COMPLETE, valid JSON object with all parameter records."
        )
        repair_prompt = (
            f"{base_prompt}{bad_output}<|im_end|>\n"
            f"<|im_start|>user\n{repair_msg}<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )
        repaired_text = ""
        if getattr(self, "use_server", False):
            import aiohttp
            timeout = aiohttp.ClientTimeout(total=1800)
            payload = {
                "text": repair_prompt,
                "sampling_params": {
                    "max_new_tokens": 12000,
                    "temperature": 0.0,
                    "repetition_penalty": 1.0,
                    "json_schema": schema_json
                }
            }
            if is_image and image_path:
                payload["image_data"] = image_path

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(f"{self.server_url}/generate", json=payload) as resp:
                    result = await resp.json()
                    repaired_text = result.get("text", "")
        else:
            gen_kwargs = {
                "prompt": repair_prompt,
                "sampling_params": {
                    "max_new_tokens": 12000,
                    "temperature": 0.0,
                    "repetition_penalty": 1.0,
                    "json_schema": schema_json
                }
            }
            if is_image and image_path:
                gen_kwargs["image_data"] = image_path
            response = await self.engine.async_generate(**gen_kwargs)
            repaired_text = response["text"] if isinstance(response, dict) else response.text

        repaired_page = self._parse_and_validate_page(repaired_text, table_evidence=table_evidence, chunk_title=chunk_title)
        n_params = sum(len(b.parameters) for b in repaired_page.parameter_blocks or [])
        logger.info(f"SGLang: Factor-9 self-healing SUCCEEDED for '{chunk_title}'. Recovered {n_params} parameters.")
        return repaired_page

    async def extract_data(self, image: Image.Image, role: str = "table_crop", evidence_text: str = "", chunk_title: str = "", table_evidence: TableEvidence = None) -> ExtractedPage:
        """Extract table data from image strictly enforcing Pydantic schema"""
        if not getattr(self, "is_loaded", False):
            raise RuntimeError("SGLangExtractor failed to load. Ensure the SGLang server is running and accessible.")
            
        import time
        start_t = time.time()
        title_log = f" ({chunk_title})" if chunk_title else ""
        logger.info(f"SGLang: [START] Extracting data from {role} image{title_log}...")
        
        import uuid
        import os
        temp_img_path = f"{Config.TEMP_IMAGE_DIR}/sglang_input_{uuid.uuid4().hex}.png"
        image.save(temp_img_path, "PNG")
        
        try:
            schema_json = json.dumps(ExtractedPage.model_json_schema(), indent=2)
            
            if role == "figure_crop":
                system_prompt = DIAGRAM_PROMPT_TEMPLATE.format(schema=schema_json)
            else:
                system_prompt = SYSTEM_PROMPT_TEMPLATE.format(schema=schema_json)
            
            user_instruction = "Extract parameters from this image strictly into the JSON schema."
            if role == "table_crop":
                user_instruction += " This image contains a table with its title and footnotes. Focus on exact transcription of table values. BYPASS STEP 0: This is a confirmed PK table, so do NOT classify as 'not_applicable'. Extract the parameters directly."
            elif role == "page_with_table":
                user_instruction += " This is a full page image containing a table. Use the Markdown text provided below as the primary transcription evidence and the image as the authoritative visual-layout source. If the Markdown and image differ, inspect the image and flag the discrepancy rather than silently ignoring it."
            elif role == "full_page":
                user_instruction += " This is a full page image. Extract any pharmacokinetic parameters you find in tables, text, or diagrams, using the surrounding text for biological context."

            if evidence_text and evidence_text.strip():
                user_instruction += (
                    f"\n\nUse the following native PDF text extracted from this region as evidence hints "
                    f"to avoid hallucinating names or values:\n\n{evidence_text.strip()}"
                )
                
            if table_evidence:
                user_instruction += (
                    f"\n\nCRITICAL: Use the following pre-computed table structure to guide your extraction. "
                    f"Ensure that compounds and species match this structure. "
                    f"All extracted parameters MUST trace back to these row/column headers:\n"
                    f"{table_evidence.model_dump_json(indent=2)}"
                )

            # Construct the conversation for Qwen-VL manually using its chat template
            prompt_text = (
                f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
                f"<|im_start|>user\n<|vision_start|><|image_pad|><|vision_end|>{user_instruction}<|im_end|>\n"
                f"<|im_start|>assistant\n"
            )
            
            # Debug: Save the exact prompt to the test folder
            try:
                debug_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "test", "llm_inputs", "prompts")
                os.makedirs(debug_dir, exist_ok=True)
                safe_title = "".join(c for c in chunk_title if c.isalnum() or c in (' ', '_')).strip()[:30] or "image"
                debug_file = os.path.join(debug_dir, f"{int(time.time()*1000)}_{role}_{safe_title.replace(' ', '_')}.txt")
                with open(debug_file, "w", encoding="utf-8") as f:
                    f.write(prompt_text)
            except Exception as e:
                logger.warning(f"Failed to save debug prompt: {e}")
            
            if getattr(self, "use_server", False):
                import aiohttp
                timeout = aiohttp.ClientTimeout(total=3600)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    payload = {
                        "text": prompt_text,
                        "image_data": temp_img_path,
                        "sampling_params": {
                            "max_new_tokens": 16000,
                            "temperature": 0.0,
                            "repetition_penalty": 1.0,
                            "json_schema": json.dumps(ExtractedPage.model_json_schema())
                        }
                    }
                    async with session.post(f"{self.server_url}/generate", json=payload) as resp:
                        result = await resp.json()
                        extracted_text = result["text"]
            else:
                response = await self.engine.async_generate(
                    prompt=prompt_text,
                    image_data=temp_img_path,
                    sampling_params={
                        "max_new_tokens": 16000,
                        "temperature": 0.0,
                        "repetition_penalty": 1.0,
                        "json_schema": json.dumps(ExtractedPage.model_json_schema())
                    }
                )
                extracted_text = response["text"] if isinstance(response, dict) else response.text
            
            try:
                return self._parse_and_validate_page(extracted_text, table_evidence=table_evidence, chunk_title=chunk_title, start_t=start_t)
            except Exception as e:
                compact_err = self._compact_validation_error(e)
                logger.warning(f"SGLang: Image schema validation failed on {role}{title_log}: {compact_err}. Attempting Factor-9 self-healing retry...")
                try:
                    return await self._attempt_repair(
                        base_prompt=prompt_text,
                        bad_output=extracted_text,
                        compact_err=compact_err,
                        schema_json=json.dumps(ExtractedPage.model_json_schema()),
                        is_image=True,
                        image_path=temp_img_path,
                        chunk_title=chunk_title,
                        table_evidence=table_evidence
                    )
                except Exception as repair_err:
                    logger.error(f"Factor-9 image repair also failed for {role}{title_log}: {repair_err}\nRaw Output: {extracted_text}")
                    raise e
        finally:
            if os.path.exists(temp_img_path):
                try:
                    os.remove(temp_img_path)
                except Exception:
                    pass

    async def extract_from_text(self, text: str, role: str = "table_xml", chunk_title: str = "", table_evidence: TableEvidence = None) -> ExtractedPage:
        """Extract table data from text/XML strictly enforcing Pydantic schema"""
        if not getattr(self, "is_loaded", False):
            raise RuntimeError("SGLangExtractor failed to load. Ensure the SGLang server is running and accessible.")
            
        import time
        start_t = time.time()
        title_log = f" ({chunk_title})" if chunk_title else ""
        logger.info(f"SGLang: [START] Extracting data from {role}{title_log}...")
        
        schema_json = json.dumps(ExtractedPage.model_json_schema(), indent=2)
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(schema=schema_json)
        
        if role == "table_xml":
            user_instruction = (
                f"Extract parameters from this document section strictly into the JSON schema. "
                f"This is a structured scientific table. Focus on exact transcription of table values.\n\n"
                f"CRITICAL INSTRUCTIONS FOR THIS TABLE:\n"
                f"1. For STEP 0, this is a confirmed PK table. You MUST classify `model_type` as either 'pbpk' or 'simple_empirical_compartmental' based on the parameters shown. Do not use 'not_applicable'.\n"
                f"2. If page metadata (Title, Authors, Journal) is not visible in this specific table block, output null for those fields as instructed in Step 5.\n"
                f"3. Map the column headers to their respective parameter entries (e.g., values under 'Mean (95% CI) - PFOS' get compound='PFOS', values under 'Mean (95% CI) - PFOA' get compound='PFOA').\n"
                f"4. If multiple compounds appear in distinct columns, generate separate parameter records for each compound.\n"
                f"5. A numerical parameter table MUST produce a non-empty `parameter_blocks` list. Create one record for every numeric parameter-value cell; do not return only `table_evidence`.\n\n"
                f"Document Text:\n{text.strip()}"
            )
            if table_evidence:
                col_summaries = [" > ".join(c.path) for c in table_evidence.columns]
                struct_summary = {
                    "table_id": table_evidence.table_id or chunk_title,
                    "title": table_evidence.title,
                    "subject_compounds": table_evidence.subject_compounds,
                    "species": table_evidence.species,
                    "columns": col_summaries,
                    "footnotes": table_evidence.footnotes,
                }
                user_instruction += (
                    f"\n\nCRITICAL: Use the following pre-computed table structure to guide your extraction. "
                    f"Ensure that compounds and species match this structure. "
                    f"All extracted parameters MUST trace back to these row/column headers:\n"
                    f"{json.dumps(struct_summary, indent=2)}"
                )
        elif role in ["narrative_xml", "narrative"]:
            user_instruction = (
                f"Extract PK model information, parameters, and modeling assumptions from this narrative text strictly into the JSON schema.\n\n"
                f"CRITICAL INSTRUCTIONS FOR NARRATIVE/METHODS SECTIONS:\n"
                f"1. MODEL ASSUMPTIONS: Identify all explicit assumptions stated by the authors about model structure, distribution, absorption, binding, clearance, or kinetics. Populate `biological_basis.stated_assumptions` with:\n"
                f"   - `description`: Clear statement of the assumption (e.g., 'Instantaneous distribution in central compartment', 'Saturable renal reabsorption via Michaelis-Menten kinetics', 'Oral bioavailability fixed to 90%').\n"
                f"   - `evidence_quote`: Direct verbatim quote from the text where the assumption is stated.\n"
                f"   - `source_location`: Section title or paragraph.\n"
                f"2. BIOLOGICAL BASIS & ADME: List physiological/physicochemical factors driving kinetics in `biological_basis.adme_determinants` and specialized processes in `biological_basis.specialized_mechanisms`.\n"
                f"3. MODEL STRUCTURE & SCALING: If compartment names, connections, differential equations, or allometric scaling rules (e.g., scaling exponent 0.75) are stated, populate `model_structure`.\n"
                f"4. MODEL PARAMETERS: Extract any explicitly reported numerical parameters, baseline physiological values, or fitted values mentioned in the text.\n\n"
                f"Document Text:\n{text.strip()}"
            )
        else:
            user_instruction = f"Extract parameters from this document text strictly into the JSON schema:\n\n{text.strip()}"

        prompt_text = (
            f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
            f"<|im_start|>user\n{user_instruction}<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )
        
        # Debug: Save the exact prompt to the test folder
        try:
            debug_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "test", "llm_inputs", "prompts")
            os.makedirs(debug_dir, exist_ok=True)
            safe_title = "".join(c for c in chunk_title if c.isalnum() or c in (' ', '_')).strip()[:30] or "text"
            debug_file = os.path.join(debug_dir, f"{int(time.time()*1000)}_{role}_{safe_title.replace(' ', '_')}.txt")
            with open(debug_file, "w", encoding="utf-8") as f:
                f.write(prompt_text)
        except Exception as e:
            logger.warning(f"Failed to save debug prompt: {e}")
        
        max_tokens = 6000 if role == "table_xml" else 16000
        extracted_text = ""
        if getattr(self, "use_server", False):
            import aiohttp
            # Set a 1-hour timeout to prevent long extractions from hitting default timeout
            timeout = aiohttp.ClientTimeout(total=3600)
            payload = {
                "text": prompt_text,
                "sampling_params": {
                    "max_new_tokens": max_tokens,
                    "temperature": 0.0,
                    "repetition_penalty": 1.0,
                    "json_schema": schema_json
                }
            }
            max_retries = 2
            for attempt in range(max_retries + 1):
                try:
                    async with aiohttp.ClientSession(timeout=timeout) as session:
                        async with session.post(f"{self.server_url}/generate", json=payload) as resp:
                            result = await resp.json()
                            extracted_text = result["text"]
                            break
                except (aiohttp.ClientError, asyncio.TimeoutError) as err:
                    if attempt < max_retries:
                        logger.warning(f"SGLang text extraction connection error on attempt {attempt+1}: {err}. Retrying in 2s...")
                        await asyncio.sleep(2.0)
                    else:
                        raise
        else:
            response = await self.engine.async_generate(
                prompt=prompt_text,
                sampling_params={
                    "max_new_tokens": max_tokens,
                    "temperature": 0.0,
                    "repetition_penalty": 1.0,
                    "json_schema": schema_json
                }
            )
            extracted_text = response["text"] if isinstance(response, dict) else response.text
        
        try:
            return self._parse_and_validate_page(extracted_text, table_evidence=table_evidence, chunk_title=chunk_title, start_t=start_t)
        except Exception as e:
            compact_err = self._compact_validation_error(e)
            logger.warning(f"SGLang: Text schema validation failed on {role}{title_log}: {compact_err}. Attempting Factor-9 self-healing retry...")
            try:
                return await self._attempt_repair(
                    base_prompt=prompt_text,
                    bad_output=extracted_text,
                    compact_err=compact_err,
                    schema_json=schema_json,
                    is_image=False,
                    image_path=None,
                    chunk_title=chunk_title,
                    table_evidence=table_evidence
                )
            except Exception as repair_err:
                logger.error(f"Factor-9 text repair also failed for {role}{title_log}: {repair_err}\nRaw Output: {extracted_text}")
                raise e

    async def extract_dosing_from_text(self, text: str) -> "DosingExtraction":
        """Extract dosing events from methods section strictly enforcing Pydantic schema"""
        from pk_pipeline.schemas import DosingExtraction
        if not getattr(self, "is_loaded", False):
            raise RuntimeError("SGLangExtractor failed to load. Ensure the SGLang server is running and accessible.")
            
        import time
        start_t = time.time()
        logger.info(f"SGLang: [START] Extracting dosing from Methods text...")
        
        schema_json = json.dumps(DosingExtraction.model_json_schema(), indent=2)
        system_prompt = (
            "You are an expert pharmacokinetic data extractor. Your task is to extract the dosing administration details "
            "from the provided Methods section text into a strict JSON format.\n"
            "Extract every distinct dosing event mentioned (e.g., if there are multiple doses, routes, or compounds).\n"
            f"You MUST output valid JSON matching this schema:\n```json\n{schema_json}\n```\n"
            "Output ONLY the JSON object, with no markdown formatting or extra text."
        )
        
        user_instruction = f"Extract dosing parameters from this document text strictly into the JSON schema:\n\n{text.strip()}"

        prompt_text = (
            f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
            f"<|im_start|>user\n{user_instruction}<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )
        
        if getattr(self, "use_server", False):
            import aiohttp
            timeout = aiohttp.ClientTimeout(total=3600)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                payload = {
                    "text": prompt_text,
                    "sampling_params": {
                        "max_new_tokens": 8000,
                        "temperature": 0.0,
                        "repetition_penalty": 1.0,
                        "json_schema": schema_json
                    }
                }
                async with session.post(f"{self.server_url}/generate", json=payload) as resp:
                    result = await resp.json()
                    extracted_text = result["text"]
        else:
            response = await self.engine.async_generate(
                prompt=prompt_text,
                sampling_params={
                    "max_new_tokens": 8000,
                    "temperature": 0.0,
                    "repetition_penalty": 1.0,
                    "json_schema": schema_json
                }
            )
            extracted_text = response["text"] if isinstance(response, dict) else response.text
        
        if "</think>" in extracted_text:
            extracted_text = extracted_text.split("</think>")[-1].strip()
            
        import re
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", extracted_text, re.DOTALL)
        if match:
            extracted_text = match.group(1).strip()
        else:
            extracted_text = extracted_text.strip()
            
        try:
            json_data = json.loads(extracted_text)
            dosing_data = DosingExtraction(**json_data)
            duration = time.time() - start_t
            logger.info(f"SGLang: [END] Dosing extraction complete in {duration:.2f}s. Found {len(dosing_data.dosing)} events.")
            return dosing_data
        except Exception as e:
            logger.error(f"Failed to parse SGLang dosing output: {e}\nRaw Output: {extracted_text}")
            raise

    async def evaluate_extracted_model(self, full_document_json: str) -> "EvaluatorJudgments":
        """Tier 2 Pass: Evaluates the extracted JSON to derive regulatory judgments."""
        from pk_pipeline.schemas import EvaluatorJudgments
        if not getattr(self, "is_loaded", False):
            raise RuntimeError("SGLangExtractor failed to load. Ensure the SGLang server is running and accessible.")
            
        import time
        start_t = time.time()
        logger.info(f"SGLang: [START] Running Tier 2 Evaluation Pass...")
        
        schema_json = json.dumps(EvaluatorJudgments.model_json_schema(), indent=2)
        system_prompt = (
            "You are an expert pharmacokinetic (PK) model evaluator working for a regulatory agency (like the FDA or EPA). "
            "Your task is to evaluate the provided extracted PBPK model data (JSON format) and derive expert judgments "
            "about the model's quality, assumptions, limitations, and reproducibility based on the OECD GD 331 framework.\n"
            f"You MUST output valid JSON matching this schema:\n```json\n{schema_json}\n```\n"
            "Output ONLY the JSON object, with no markdown formatting or extra text."
        )
        
        user_instruction = f"Evaluate the following extracted PBPK model data strictly into the EvaluatorJudgments JSON schema:\n\n{full_document_json}"

        prompt_text = (
            f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
            f"<|im_start|>user\n{user_instruction}<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )
        
        if getattr(self, "use_server", False):
            import aiohttp
            timeout = aiohttp.ClientTimeout(total=3600)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                payload = {
                    "text": prompt_text,
                    "sampling_params": {
                        "max_new_tokens": 8000,
                        "temperature": 0.0,
                        "repetition_penalty": 1.0,
                        "json_schema": schema_json
                    }
                }
                async with session.post("http://127.0.0.1:30000/generate", json=payload) as resp:
                    result = await resp.json()
                    extracted_text = result["text"]
        else:
            response = await self.engine.async_generate(
                prompt=prompt_text,
                sampling_params={
                    "max_new_tokens": 8000,
                    "temperature": 0.0,
                    "repetition_penalty": 1.0,
                    "json_schema": schema_json
                }
            )
            extracted_text = response["text"] if isinstance(response, dict) else response.text
        
        if "</think>" in extracted_text:
            extracted_text = extracted_text.split("</think>")[-1].strip()
            
        import re
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", extracted_text, re.DOTALL)
        if match:
            extracted_text = match.group(1).strip()
        else:
            extracted_text = extracted_text.strip()
            
        try:
            json_data = json.loads(extracted_text)
            judgments = EvaluatorJudgments(**json_data)
            duration = time.time() - start_t
            logger.info(f"SGLang: [END] Tier 2 Evaluation complete in {duration:.2f}s.")
            return judgments
        except Exception as e:
            logger.error(f"Failed to parse SGLang Tier 2 evaluation output: {e}\nRaw Output: {extracted_text}")
            raise



class LayaFilter:
    """
    Fast System-1 decision model (convaiinnovations/laya) for triage,
    narrative chunk filtering, and document routing.
    Runs non-autoregressively in ~20-30ms.
    """
    def __init__(self, device: str = None, threshold: float = 0.25):
        self.threshold = threshold
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        try:
            from laya import Router
            logger.info("Initializing LayaFilter router...")
            self.router = Router(preload=False, device=self.device)
            self.is_loaded = True
            logger.info("LayaFilter initialized successfully.")
        except Exception as e:
            logger.warning(f"Could not initialize LayaFilter: {e}")
            self.is_loaded = False

    def is_pk_relevant(self, text: str) -> tuple[bool, float, str]:
        """
        Evaluates whether a text excerpt contains numerical PK model parameters,
        rate constants, partition coefficients, or physiological parameters.
        Returns: (keep_boolean, confidence_score, model_type_choice)
        """
        if not self.is_loaded or len(text.strip()) < 50:
            return True, 1.0, "unknown"

        questions = {
            "has_pk_parameters": {
                "type": "noul",
                "instructions": (
                    "Does this specific text excerpt contain numerical pharmacokinetic parameter values, "
                    "equations, rate constants, partition coefficients, half-lives, clearance values, "
                    "or physiological blood flows and volumes?"
                )
            },
            "model_type": {
                "type": "choice",
                "instructions": "What type of pharmacokinetic modeling or data is described?",
                "criteria": {
                    "pbpk": "physiologically based pharmacokinetic model with multiple organ compartments and blood flows",
                    "compartmental": "classical 1, 2, or 3 empirical compartment PK model",
                    "nca": "non-compartmental analysis (AUC, Cmax, Tmax only)",
                    "not_applicable": "no pharmacokinetic modeling or parameter estimation"
                }
            }
        }
        try:
            # truncate to 3500 chars to avoid exceeding token limit
            truncated_text = text[:3500]
            res = self.router.predict(truncated_text, questions)
            score = float(res["answers"]["has_pk_parameters"]["noul"])
            choice = res["answers"]["model_type"]["choice"]

            # Keep only if probability meets threshold
            keep = (score >= self.threshold)
            return keep, score, choice
        except Exception as e:
            logger.warning(f"Laya filter error: {e}. Defaulting to keep chunk.")
            return True, 1.0, "unknown"

    def classify_model_type(self, text: str) -> str:
        """
        Quickly classifies paper or section into: 'pbpk', 'compartmental', 'nca', or 'not_applicable'.
        """
        if not self.is_loaded:
            return "not_applicable"

        questions = {
            "model_type": {
                "type": "choice",
                "instructions": "What type of pharmacokinetic modeling or study is this?",
                "criteria": {
                    "pbpk": "physiologically based pharmacokinetic model with multiple organ compartments",
                    "compartmental": "empirical 1, 2, or 3 compartment PK model",
                    "nca": "non-compartmental analysis (AUC, Cmax only)",
                    "not_applicable": "no pharmacokinetic modeling data"
                }
            }
        }
        try:
            truncated = text[:3500]
            res = self.router.predict(truncated, questions)
            return res["answers"]["model_type"]["choice"]
        except Exception as e:
            logger.warning(f"Laya classification error: {e}")
            return "not_applicable"


class WeVisDocParser:
    """
    Tencent/WeVisDoc-4B Vision-to-Markdown Document Parser.
    Fine-tuned from Qwen3-VL to convert PDF document/table images into structured Markdown
    with LaTeX math formulas and standard HTML tables (preserving rowspan, colspan, hierarchical headers).
    Reference: https://huggingface.co/tencent/WeVisDoc-4B
    """
    DEFAULT_SYSTEM_PROMPT = (
        "You are an AI assistant specialized in converting PDF images to Markdown format. "
        "Please follow these instructions for the conversion:\n\n"
        "1. Text Processing:\n"
        "- Accurately recognize all text content in the PDF image without guessing or inferring.\n"
        "- Convert the recognized text into Markdown format.\n"
        "- Maintain the original document structure, including headings, paragraphs, lists, etc.\n\n"
        "2. Mathematical Formula Processing:\n"
        "- Convert all mathematical formulas to LaTeX format.\n"
        "- Enclose inline formulas with \\( \\). For example: \\( E = mc^2 \\)\n"
        "- Enclose block formulas with \\[ \\]. For example: \\[ \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a} \\]\n\n"
        "3. Table Processing:\n"
        "- Convert all tables to standard HTML format using <table>, <thead>, <tbody>, <tr>, <th>, <td>.\n"
        "- Use rowspan and colspan appropriately for merged headers or cells.\n"
        "- Preserve exact numerical and textual values in table cells."
    )

    DEFAULT_USER_PROMPT = "Please transcribe this page image into clean Markdown following the system instructions."

    def __init__(self, model_id: str = "Tencent/WeVisDoc-4B", device: str = None):
        self.model_id = model_id
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.processor = None
        self.model = None
        self.is_loaded = False

    def load(self):
        """Loads processor and model weights into VRAM lazily."""
        if self.is_loaded:
            return

        logger.info(f"Loading WeVisDocParser ({self.model_id}) on {self.device}...")
        dtype = torch.bfloat16 if (self.device and "cuda" in self.device) else torch.float32

        from transformers import AutoProcessor
        self.processor = AutoProcessor.from_pretrained(self.model_id, trust_remote_code=True)

        device_map = {"": self.device} if (self.device and self.device != "cpu") else None
        try:
            from transformers import Qwen3VLForConditionalGeneration
            self.model = Qwen3VLForConditionalGeneration.from_pretrained(
                self.model_id,
                torch_dtype=dtype,
                device_map=device_map,
                trust_remote_code=True
            ).eval()
        except Exception as e:
            logger.warning(f"WeVisDoc Qwen3VL direct load note ({e}), falling back to AutoModelForVision2Seq...")
            from transformers import AutoModelForVision2Seq
            self.model = AutoModelForVision2Seq.from_pretrained(
                self.model_id,
                torch_dtype=dtype,
                device_map=device_map,
                trust_remote_code=True
            ).eval()

        self.is_loaded = True
        logger.info("WeVisDocParser loaded successfully into VRAM.")

    def parse_image(
        self,
        image: Image.Image,
        max_new_tokens: int = 4096,
        user_prompt: str = None,
        system_prompt: str = None
    ) -> str:
        """
        Transcribes a PIL Image into structured Markdown with HTML tables and LaTeX math.
        """
        self.load()
        sys_prompt = system_prompt or self.DEFAULT_SYSTEM_PROMPT
        u_prompt = user_prompt or self.DEFAULT_USER_PROMPT

        messages = [
            {"role": "system", "content": sys_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": u_prompt}
                ]
            }
        ]

        prompt_text = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.processor(
            text=[prompt_text],
            images=[image],
            padding=True,
            return_tensors="pt"
        ).to(self.model.device)

        with torch.no_grad():
            generated_ids = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=False
            )

        generated_ids_trimmed = [
            out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
        ]
        output_text = self.processor.batch_decode(
            generated_ids_trimmed,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False
        )[0]
        return output_text.strip()
