import asyncio
import torch
from typing import List
from PIL import Image
import json
import os

from .schemas import ExtractedPage, ExtractedParameter, TableEvidence, ExtractionResult, TableExtractionPage, DiagramExtractionPage
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

    def score_pages(self, query: str, images: List[Image.Image]) -> List[float]:
        """Score all page images against a query text using ColQwen MaxSim."""
        if not images:
            return []
        if not self.is_loaded:
            raise RuntimeError("ColQwenRetriever model is not loaded. Ensure colpali-engine is installed and GPU is available.")
        with torch.no_grad():
            batch_images = self.processor.process_images(images).to(self.model.device)
            image_embeddings = self.model(**batch_images)
            batch_queries = self.processor.process_queries([query]).to(self.model.device)
            query_embeddings = self.model(**batch_queries)
            scores = self.processor.score_multi_vector(query_embeddings, image_embeddings)[0]
            return [s.item() for s in scores]

    def find_top_pages_ensemble(self, images: List[Image.Image], top_k_per_query: int = 3) -> dict:
        """
        Multi-query ensemble retrieval to ensure prose pages, split tables,
        and compartmental diagrams are all retrieved.
        """
        queries = {
            "tables": "Table of physiological parameters blood flow tissue volumes partition coefficients Vmax Km clearance",
            "narrative": "pharmacokinetic values estimated half-life clearance volume bioavailability body weight cardiac output",
            "diagram": "Pharmacokinetic model structure schematic diagram compartments flow chart arrows"
        }
        selected = {"table_pages": set(), "narrative_pages": set(), "diagram_pages": set()}

        for role, query_text in queries.items():
            scores = self.score_pages(query_text, images)
            ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
            top_indices = ranked_indices[:top_k_per_query]
            if role == "tables":
                selected["table_pages"].update(top_indices)
            elif role == "narrative":
                selected["narrative_pages"].update(top_indices)
            elif role == "diagram":
                if ranked_indices:
                    selected["diagram_pages"].add(ranked_indices[0])

        return selected


PBPK_SYSTEM_PROMPT = """You are an expert PBPK/TK data extraction engine. Extract every physiological, biochemical, physicochemical, and formulation parameter into the required JSON schema.

### STEP 1 — MODEL CLASSIFICATION
- Classify `model_classification` as `'pbpk'` or `'simple_empirical_compartmental'`. Only use `'not_applicable'` if the text/image contains zero PK/PBPK model inputs or structure.

### STEP 2 — MULTI-COLUMN, MULTI-FORMULATION & RANGE RULES (CRITICAL)
1. **Cartesian Column Unrolling (Never Skip Columns)**:
   - If a table has columns for multiple compounds (e.g., `PFOS`, `PFOA`, `PFHxS`), species (`Nonhuman primate`, `Human`, `Rat`), or life stages (`Mother`, `Fetus`, `Infant`), emit a SEPARATE `ExtractedParameter` object for EVERY populated column in that row.
2. **Comma-Separated Formulations (NEVER Map to Ranges)**:
   - If a column header specifies multiple formulations (e.g., `Value in rat for Rilutor, ASD` with cell `0.69, 2.19` or `0.013, 0.011`), emit TWO separate `ExtractedParameter` entries: one with `context.formulation = "Rilutor"` (`value = 0.69`) and one with `context.formulation = "ASD"` (`value = 2.19`). NEVER place comma-separated formulations into `ci_low`/`ci_high` or `start_value`/`end_value`.
3. **Confidence Intervals vs. Time-Varying Physiological Ranges**:
   - **Confidence Intervals**: When a cell reports a point estimate with parentheses like `0.21 (0.18, 0.25)` under a `(95% CI)` header, set `value = 0.21`, `ci_low = 0.18`, `ci_high = 0.25`, `variance_type = "95% CI"`.
   - **Time-Varying Growth Ranges**: When a physiological parameter changes over gestation/lactation/age (e.g., `56.9 - 70 (initial)`, `65.3 - 79.6 (increasing)`, `0 - 3.8`, `3.2 - 2.4`), set `start_value` to the first number (e.g., `56.9` or `3.2`) and `end_value` to the second number (e.g., `70.0` or `2.4`), and record the descriptor in `value_qualifier`.
4. **Dual-Symbol Rows**:
   - If a row defines two symbols for different life stages (e.g., `urinary elimination rate constant, kurinec (/h/kg^-0.25); keliml for infant (/h)`), emit TWO separate parameter entries with their respective symbol, unit, and `context.life_stage` (`Mother` vs. `Infant`).
5. **Footnotes & Inline Numbers with Letters**:
   - Always record the exact string in `value_text` (e.g., `'0.008[b]'` or `'5a'`). Strip the footnote letter to parse the pure float into `value` (`0.008`, `5.0`) and put `'b'` or `'a'` in `footnote_marker`.
   - Read all `Table Footnotes` carefully and extract any numeric constants stated in the footnotes (e.g., `liver:blood partition coefficient = 2.0`, `blood to plasma ratio = 1.1`, or forced bioavailability overrides) as standalone `ExtractedParameter` objects!
6. **Group Headers & Units**:
   - Never emit a spanning group header (e.g., `Blood flow to organ (fraction)`) as a parameter with `value: null`. Prepend the group header to each row below it (e.g., `parameter_name = "Blood flow to organ - Liver"`) and propagate its unit with `unit_inherited = true`.

### STEP 3 — MODEL STRUCTURE / TOPOLOGY
- When given a compartmental diagram or equations, extract all compartment names and directional flow connections into `structure`. Symbolic equations without numbers (e.g., `Vc = Vcc * BW`) belong in `structure.scaling_equations`, never as fake numeric parameters.
"""

def build_table_user_prompt(markdown_table_string: str, source_location: str) -> str:
    return f"""Extract all PBPK/TK parameters from `{source_location}` strictly into the JSON schema.

CRITICAL INSTRUCTIONS FOR THIS TABLE:
1. This is a confirmed PK/PBPK input table. Set `model_classification` to `'pbpk'` or `'simple_empirical_compartmental'`. Do NOT output `'not_applicable'`.
2. Unroll EVERY data column (every compound, species, life stage, and formulation) into its own parameter object.
3. Extract all numeric constants mentioned in the Table Footnotes section at the bottom.

Document Table ({source_location}):
{markdown_table_string}"""


from .schemas import ExtractedPage, ExtractedParameter, TableExtractionPage, DiagramExtractionPage

TABLE_SYSTEM_PROMPT_TEMPLATE = """You are an OECD GD 331 compliant pharmacokinetic (PK) and PBPK table data extraction engine.
Your task is to faithfully extract model parameters, experimental values, and model outputs from scientific tables into the strict JSON schema provided below.

==================================================
1. CORE ANTI-HALLUCINATION & FIDELITY RULES
==================================================
- Extract ONLY what is explicitly printed in the table. Never guess, infer, calculate, or supply parameters from general pharmacological knowledge or typical values.
- Never extract a value in isolation: associate every value with its complete semantic context (compound, species, life stage, formulation, compartment, parameter, unit, and uncertainty).
- Interpret every table independently: NEVER leak context (compounds, species, or units) from other tables or surrounding text unless explicitly shared.
- If a value or context field cannot be identified with high confidence, set needs_review=true rather than guessing.
- Distinguish model input parameters (which belong in `parameter_blocks`) from observed/simulated clinical PK outputs (e.g., observed Cmax, AUC, which belong in `observed_data`).

==================================================
2. PRE-COMPUTED TABLE STRUCTURE & CELL BINDING
==================================================
The document table layout has already been mapped for you (see the markdown table and pre-computed column/row summary in the user prompt).
- Bind every parameter to its `source_table` (e.g. "Table 1", "Table 3"), `row_id` (e.g. "r1"), and `column_id` (e.g. "c1").
- Populate `row_path` and `column_path` reflecting the hierarchical headers.
- Record the exact, unedited printed cell text in `source_quote`.

==================================================
3. CARTESIAN COLUMN UNROLLING & MULTI-CONDITION HEADERS
==================================================
- Multi-Compound / Multi-Species / Multi-Life-Stage Columns: If a table has distinct columns for multiple compounds (e.g. PFOS, PFOA, PFHxS), species (Nonhuman primate, Human), or life stages (Mother, Fetus, Infant), emit a SEPARATE parameter record for EVERY populated cell in that row. Never skip columns or merge compounds.
- Comma-Separated Formulations (Never Map to Ranges): If a cell contains comma-separated values for multiple formulations (e.g. '0.69, 2.19' for 'Rilutor, ASD'), emit separate parameter records: one with context.formulation="Rilutor" (value=0.69) and one with context.formulation="ASD" (value=2.19). NEVER place comma-separated formulations into ranges or confidence intervals.
- Dual-Symbol Rows: If a row defines two symbols for different life stages (e.g. 'kurinec (/h/kg^-0.25); keliml for infant (/h)'), emit separate parameter records with their respective symbol, unit, and life stage ('Mother' vs. 'Infant').

==================================================
4. FOOTNOTES, QUALIFIERS & INLINE NUMBERS WITH LETTERS
==================================================
- Verbatim Transcription: Always capture the exact cell text in `value_text` (e.g. '0.008b', '5a', '4.00E-04').
- Number & Marker Separation: Strip the footnote letter to parse the pure float into `value` (e.g. 0.008, 5.0) and put the isolated symbol/letter into `footnote_marker` ('b', 'a').
- Constants in Footnotes: Inspect all table footnotes. Extract any explicitly stated numeric constants (e.g. 'liver:blood partition coefficient = 2.0', 'bioavailability fixed to 90%') as standalone parameter records!
- Spanning Group Headers: Never emit a spanning group header as a parameter with value=null. Prepend the group header to each child row (e.g. 'Blood flow to organ - Liver') and propagate its unit with `unit_inherited=true`.

==================================================
5. POINT ESTIMATES, UNCERTAINTY & PHYSIOLOGICAL RANGES
==================================================
- Point Estimates with Uncertainty: When a cell reports a point estimate with confidence interval or error (e.g. '0.21 (0.18, 0.25)' under 'Mean (95% CI)'), set `value=0.21`, `ci_low=0.18`, and `ci_high=0.25`.
- Time-Varying Physiological Ranges: When a parameter changes dynamically across gestation or growth (e.g. '56.9 - 70 (initial)', '3.2 - 2.4'), set `start_value` to the initial value (56.9 or 3.2), `end_value` to the final value (70.0 or 2.4), and put the qualifier in `value_qualifier`. Leave `value=null`.

==================================================
6. PARAMETER CLASSIFICATION & PROVENANCE
==================================================
- `parameter_class`: Must be exactly one of:
  * `physiological`: Organisms' biological parameters independent of drug (body weight, organ volumes, blood flows, cardiac output, GFR, hematocrit).
  * `biochemical`: Drug interaction with physiology (partition coefficients Kp, fraction unbound fu, clearances, absorption rate ka, Vmax, Km, distribution volume Vc/Vd, transfer rates, bioavailability, half-life).
  * `compound_specific`: Pure physicochemical properties (MW, logP, solubility, pKa).
- `status`: Must match provenance: `measured_here`, `literature`, `fitted`, `derived`, `assumed_default`, `in_vitro_ivive`, `predicted_qsar`, or `not_reported`.

==================================================
7. OUTPUT FORMAT
==================================================
Return ONLY valid JSON matching the schema below. No markdown code fences, no commentary.

{schema}
"""

SYSTEM_PROMPT_TEMPLATE = """You are an OECD GD 331 compliant pharmacokinetic (PK) and PBPK narrative & document extraction engine.
Your task is to extract scientifically meaningful model parameters, experimental values, model structure, and modeling assumptions from research papers into the strict JSON schema provided below.

==================================================
1. CORE ANTI-HALLUCINATION & FIDELITY RULES
==================================================
- Extract ONLY what is explicitly stated in the document. Never guess, infer, calculate, or supply parameters from general pharmacological knowledge or typical values.
- Never extract a value in isolation: associate every value with its complete semantic context (compound, species, life stage, compartment, parameter, unit, and uncertainty).
- Interpret sections independently: do not carry context from one section into another unless the document explicitly indicates that it is shared.
- If information is absent or ambiguous, use null or set needs_review=true rather than guessing.
- Distinguish model input parameters from observed/simulated experimental outputs.

==================================================
2. MODEL STRUCTURE & BIOLOGICAL ASSUMPTIONS
==================================================
When analyzing narrative text, methods, or model descriptions:
1. Identify explicit modeling assumptions stated by the authors:
   - Compartmental structure (e.g., well-stirred, perfusion-limited, membrane-limited).
   - Distribution kinetics (e.g., instantaneous mixing, deep tissue equilibrium).
   - Clearance & elimination mechanisms (e.g., saturable reabsorption via Michaelis-Menten, biliary excretion).
   - Binding and partitioning (e.g., constant unbound fraction, linear tissue partitioning).
   - Bioavailability and absorption (e.g., 100% absorption, fixed oral bioavailability).
   - Scaling & extrapolations (e.g., allometric exponent 0.75, in vitro to in vivo extrapolation).
2. For each assumption, populate `biological_basis.stated_assumptions`:
   - `description`: Clear summary of the assumption.
   - `evidence_quote`: Exact verbatim quote from the text where the assumption is stated.
   - `source_location`: Section name or paragraph.
3. Populate `biological_basis.adme_determinants` with physiological/physicochemical determinants.
4. Populate `biological_basis.specialized_mechanisms` with non-standard mechanisms (e.g., "saturable_reabsorption").
5. Populate `model_structure` with compartment names, differential equations, and allometric scaling rules.

==================================================
3. CARTESIAN UNROLLING & MULTI-CONDITION HEADERS
==================================================
- If tables or text report parameters across multiple compounds, species, or life stages, emit a SEPARATE parameter record for EVERY condition.
- Comma-Separated Formulations: Emit separate parameter records per formulation; never merge into ranges.
- Dual-Symbol Rows: Emit separate parameter records per life stage with their respective symbol and unit.

==================================================
4. FOOTNOTES, QUALIFIERS & CONSTANTS
==================================================
- Record verbatim cell text in `value_text`. Strip footnote letters to parse pure floats into `value` and isolate markers into `footnote_marker`.
- Extract numeric constants stated in footnotes or methods as standalone parameter records.
- Prepend spanning group headers to child row names (e.g., 'Blood flow - Liver') and set `unit_inherited=true`.

==================================================
5. ESTIMATES, UNCERTAINTY & TIME-VARYING RANGES
==================================================
- Point estimates with uncertainty: `value` = point estimate, `ci_low` = lower bound, `ci_high` = upper bound.
- Time-varying dynamic ranges: `start_value` = initial, `end_value` = final, qualifier in `value_qualifier`. Leave `value=null`.

==================================================
6. PARAMETER CLASSIFICATION & PROVENANCE
==================================================
- `parameter_class`: `physiological`, `biochemical`, or `compound_specific`.
- `status`: `measured_here`, `literature`, `fitted`, `derived`, `assumed_default`, `in_vitro_ivive`, `predicted_qsar`, or `not_reported`.

==================================================
7. OUTPUT FORMAT
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
3. Fill out the `model_structure` object with `compartments` and `connections`:
   - **compartments**: Extract every box in the diagram as a compartment. Set `label_raw` to exactly what is written in the box (e.g., "Liver", "Fat", "Slowly perfused"). Set `id` to a short unique string (e.g., "liver", "c1").
   - **connections**: Extract every arrow as a connection. Set `source` and `target` to the `id` of the respective compartments. Set `direction` based on the arrowhead ("forward", "bidirectional"). If an arrow goes to/from outside the model (e.g., an excretion arrow leaving the Liver with no target box), use "external" as the missing `id`. If a label is written on the arrow (e.g., "Q_liver", "CL_int", "IV dose"), put it in `label_raw`.
4. Return ONLY the `model_classification` and `model_structure` fields matching the schema below.
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

    @staticmethod
    def _repair_truncated_json(text: str) -> dict | None:
        """Deterministic fast-repair for JSON truncated by token limits (e.g. unterminated strings)."""
        if not text:
            return None
        clean = text.strip()
        if clean.startswith("```json"):
            clean = clean[7:]
        elif clean.startswith("```"):
            clean = clean[3:]
        clean = clean.rstrip("`").strip()

        # Progressively backtrack to the last closing brace '}'
        last_brace_idx = len(clean)
        while True:
            last_brace_idx = clean.rfind("}", 0, last_brace_idx)
            if last_brace_idx == -1:
                break
            candidate = clean[:last_brace_idx + 1]

            # Calculate unclosed brackets and braces in candidate
            in_string = False
            escape = False
            open_stack = []
            for ch in candidate:
                if escape:
                    escape = False
                    continue
                if ch == '\\':
                    escape = True
                    continue
                if ch == '"':
                    in_string = not in_string
                    continue
                if not in_string:
                    if ch in ('{', '['):
                        open_stack.append(ch)
                    elif ch in ('}', ']'):
                        if open_stack:
                            top = open_stack[-1]
                            if (top == '{' and ch == '}') or (top == '[' and ch == ']'):
                                open_stack.pop()

            if in_string:
                continue

            # Close all open braces/brackets in reverse order
            closing = "".join("}" if op == "{" else "]" for op in reversed(open_stack))
            test_candidate = candidate + closing
            try:
                parsed = json.loads(test_candidate)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                continue

        return None

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

        try:
            json_data = json.loads(clean_text)
        except json.JSONDecodeError as exc:
            # Deterministic fast-repair: recover all complete parameter blocks before truncation
            repaired = self._repair_truncated_json(clean_text)
            if repaired is not None:
                logger.info(f"SGLang: Successfully repaired truncated JSON locally for '{chunk_title}'.")
                json_data = repaired
            else:
                raise exc

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
        # Check if local repair resolves truncated JSON first
        repaired_dict = self._repair_truncated_json(bad_output)
        if repaired_dict is not None:
            try:
                page = ExtractedPage(**repaired_dict)
                if table_evidence:
                    page.table_evidence.append(table_evidence)
                n_params = sum(len(b.parameters) for b in page.parameter_blocks or [])
                logger.info(f"SGLang: Factor-9 fast local repair SUCCEEDED for '{chunk_title}'. Recovered {n_params} parameters.")
                return page
            except Exception as e:
                logger.debug(f"Factor-9 local repair failed ExtractedPage validation: {e}")

        # Limit bad_output to prevent context window explosion and server deadlock
        clipped_bad = bad_output if len(bad_output) <= 3000 else ("...[earlier records omitted for length]...\n" + bad_output[-2500:])

        repair_msg = (
            f"Your previous JSON output failed schema validation with these specific error(s):\n"
            f"{compact_err}\n\n"
            f"CRITICAL FIX RULES:\n"
            f"1. Fix the indicated fields to strictly comply with the schema.\n"
            f"2. Ensure all numbers in 'quantitative_data.value' are floats; textual ranges or CI belong in 'uncertainty' or 'value_text'.\n"
            f"3. Return the COMPLETE, valid JSON object with all parameter records."
        )
        repair_prompt = (
            f"{base_prompt}{clipped_bad}<|im_end|>\n"
            f"<|im_start|>user\n{repair_msg}<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )
        repaired_text = ""
        if getattr(self, "use_server", False):
            import aiohttp
            # Set a 3-minute timeout for repair to prevent deadlock
            timeout = aiohttp.ClientTimeout(total=180)
            payload = {
                "text": repair_prompt,
                "sampling_params": {
                    "max_new_tokens": 4096,
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
                    "max_new_tokens": 4096,
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
            if role in ("table_crop", "table_xml"):
                schema_cls = TableExtractionPage
                schema_json = json.dumps(schema_cls.model_json_schema(), indent=2)
                system_prompt = TABLE_SYSTEM_PROMPT_TEMPLATE.format(schema=schema_json)
            elif role == "figure_crop":
                schema_cls = DiagramExtractionPage
                schema_json = json.dumps(schema_cls.model_json_schema(), indent=2)
                system_prompt = DIAGRAM_PROMPT_TEMPLATE.format(schema=schema_json)
            else:
                schema_cls = ExtractedPage
                schema_json = json.dumps(schema_cls.model_json_schema(), indent=2)
                system_prompt = SYSTEM_PROMPT_TEMPLATE.format(schema=schema_json)
            
            user_instruction = "Extract parameters from this image strictly into the JSON schema."
            if role == "table_crop":
                user_instruction += " This image contains a table with its title and footnotes. Focus on exact transcription of table values into parameter_blocks. Set model_classification to 'pbpk' or 'simple_empirical_compartmental'."
            elif role == "figure_crop":
                user_instruction = "Extract the compartmental model structure, compartments, and connections from this diagram strictly into the JSON schema."
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
                            "json_schema": json.dumps(schema_cls.model_json_schema())
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
                        "json_schema": json.dumps(schema_cls.model_json_schema())
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
                        schema_json=json.dumps(schema_cls.model_json_schema()),
                        is_image=True,
                        image_path=temp_img_path,
                        chunk_title=chunk_title,
                        table_evidence=table_evidence
                    )
                except Exception as repair_err:
                    logger.error(f"Factor-9 image repair also failed for {role}{title_log}: {repair_err}\nRaw Output: {extracted_text}")
                    if table_evidence:
                        logger.warning(f"Using structured table_evidence fallback for '{chunk_title}' after repair failure.")
                        return ExtractedPage(table_evidence=[table_evidence])
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
        
        if role in ("table_crop", "table_xml"):
            schema_cls = TableExtractionPage
            schema_json = json.dumps(schema_cls.model_json_schema(), indent=2)
            system_prompt = TABLE_SYSTEM_PROMPT_TEMPLATE.format(schema=schema_json)
        else:
            schema_cls = ExtractedPage
            schema_json = json.dumps(schema_cls.model_json_schema(), indent=2)
            system_prompt = SYSTEM_PROMPT_TEMPLATE.format(schema=schema_json)
        
        if role == "table_xml":
            user_instruction = (
                f"Extract parameters from this document section strictly into the JSON schema. "
                f"This is a structured scientific table. Focus on exact transcription of table values into parameter_blocks.\n\n"
                f"CRITICAL INSTRUCTIONS FOR THIS TABLE:\n"
                f"1. This is a confirmed PK table. Classify `model_type` as 'pbpk' or 'simple_empirical_compartmental' based on the parameters shown. Do not use 'not_applicable'.\n"
                f"2. If page metadata (title, authors, journal) is not visible in this specific table, leave it null.\n"
                f"3. Map column headers to their respective parameter entries (e.g., values under 'Mean (95% CI) - PFOS' get compound='PFOS', values under 'Mean (95% CI) - PFOA' get compound='PFOA').\n"
                f"4. Cartesian Column Unrolling: If multiple compounds or species appear in distinct columns, emit separate parameter records for each populated cell.\n"
                f"5. A numerical parameter table MUST produce a non-empty `parameter_blocks` list. Create one record for every numeric parameter-value cell.\n"
                f"6. Use the pre-computed table structure and footnotes below to guide exact provenance and cell binding.\n\n"
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
        
        max_tokens = 16384
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
                    "json_schema": json.dumps(schema_cls.model_json_schema())
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
                    "json_schema": json.dumps(schema_cls.model_json_schema())
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
                    schema_json=json.dumps(schema_cls.model_json_schema()),
                    is_image=False,
                    image_path=None,
                    chunk_title=chunk_title,
                    table_evidence=table_evidence
                )
            except Exception as repair_err:
                logger.error(f"Factor-9 text repair also failed for {role}{title_log}: {repair_err}\nRaw Output: {extracted_text}")
                if table_evidence:
                    logger.warning(f"Using structured table_evidence fallback for '{chunk_title}' after repair failure.")
                    return ExtractedPage(table_evidence=[table_evidence])
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



class PBPKExtractorService:
    def __init__(self, model_id: str = "Qwen/Qwen2.5-VL-7B-Instruct"):
        self.model_id = model_id
        self.use_sglang = False
        self.server_url = "http://127.0.0.1:30000"
        
        # Check if external SGLang server is running
        try:
            import requests
            resp = requests.get(f"{self.server_url}/health", timeout=2)
            if resp.status_code == 200:
                self.use_sglang = True
                logger.info("PBPKExtractorService: Connected to running SGLang server on port 30000.")
        except Exception:
            self.use_sglang = False

        self.llm = None
        self.sampling_params = None
        if not self.use_sglang:
            try:
                from vllm import LLM, SamplingParams
                self.llm = LLM(
                    model=model_id,
                    tensor_parallel_size=1,
                    trust_remote_code=True,
                    max_model_len=16384,
                    enable_prefix_caching=True
                )
                self.sampling_params = SamplingParams(
                    temperature=0.0,
                    repetition_penalty=1.0,
                    max_tokens=8192,
                    guided_json=ExtractionResult.model_json_schema()
                )
            except Exception as e:
                logger.warning(f"PBPKExtractorService: vLLM initialization note: {e}")

    def find_top_pages(self, retriever, pdf_images: list, top_k_per_query: int = 3) -> dict:
        """
        Multi-query ensemble retrieval to ensure prose pages, split tables,
        and compartmental diagrams are all retrieved.
        """
        queries = {
            "tables": "Table of physiological parameters blood flow tissue volumes partition coefficients Vmax Km clearance",
            "narrative": "pharmacokinetic values estimated half-life clearance volume bioavailability body weight cardiac output",
            "diagram": "Pharmacokinetic model structure schematic diagram compartments flow chart arrows"
        }
        selected = {"table_pages": set(), "narrative_pages": set(), "diagram_pages": set()}

        for role, query_text in queries.items():
            if hasattr(retriever, "score_pages"):
                scores = retriever.score_pages(query_text, pdf_images)
            else:
                continue
            ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
            top_indices = ranked_indices[:top_k_per_query]
            if role == "tables":
                selected["table_pages"].update(top_indices)
            elif role == "narrative":
                selected["narrative_pages"].update(top_indices)
            elif role == "diagram":
                if ranked_indices:
                    selected["diagram_pages"].add(ranked_indices[0])

        return selected

    def extract_text_table(self, markdown_table: str, source_location: str) -> dict:
        user_prompt = build_table_user_prompt(markdown_table, source_location)
        full_prompt = (
            f"<|im_start|>system\n{PBPK_SYSTEM_PROMPT}<|im_end|>\n"
            f"<|im_start|>user\n{user_prompt}<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )
        if self.use_sglang:
            import requests
            schema_json = json.dumps(ExtractionResult.model_json_schema())
            payload = {
                "text": full_prompt,
                "sampling_params": {
                    "max_new_tokens": 8192,
                    "temperature": 0.0,
                    "repetition_penalty": 1.0,
                    "json_schema": schema_json
                }
            }
            resp = requests.post(f"{self.server_url}/generate", json=payload, timeout=3600)
            res_data = resp.json()
            raw_text = res_data.get("text", "")
            return ExtractionResult.model_validate_json(raw_text).model_dump()
        elif self.llm is not None:
            outputs = self.llm.generate([{"prompt": full_prompt}], sampling_params=self.sampling_params)
            raw_json = outputs[0].outputs[0].text
            return ExtractionResult.model_validate_json(raw_json).model_dump()
        else:
            raise RuntimeError("Neither SGLang server nor vLLM is available for PBPKExtractorService.")



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
