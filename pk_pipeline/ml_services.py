import torch
from typing import List
from PIL import Image
import json
import os

from schemas import ExtractedPage, ExtractedParameter
from config import logger, Config

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
    
    def find_top_pages(self, images: List[Image.Image], query: str = "Pharmacokinetic parameters table", top_k: int = 10, threshold_ratio: float = 0.85) -> List[Image.Image]:
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
            
            # If the page looks more like a Reference section than a PK Table, penalize it heavily
            penalty = 0
            if n_score > p_score or (n_score > 15.0 and p_score < 18.0):
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
        top_indices = top_indices[:top_k]
        
        # Fallback if somehow empty (ignore penalty in this catastrophic case)
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


from schemas import ExtractedPage, ExtractedParameter

SYSTEM_PROMPT_TEMPLATE = """You are a pharmacokinetic (PK) data extraction system. You are shown an image of a single page from a scientific paper. Your task is to extract pharmacokinetic parameters, model structure, and study metadata that are EXPLICITLY PRESENT on this page, and return them in the exact JSON schema provided below. You are not being asked to know pharmacology — you are being asked to transcribe faithfully what is printed on this page.

## THE SINGLE MOST IMPORTANT RULE

Extract only what is visually present on this page. Never supply a parameter, value, species, compound, or metadata field from general pharmacological knowledge, typical values, or what similar papers usually report. If a piece of information is not legible on this page, the correct output is to omit it or set it to null — not to estimate it, not to infer it, not to borrow a "typical" value from your training data.

Concretely: if this page does not contain the words "cardiac output" (or an unambiguous synonym) attached to a number and a unit, you must not output a cardiac output parameter — even though cardiac output is one of the most common PBPK parameters in the literature. The same applies to every parameter type. You have seen thousands of PBPK papers reporting cardiac output, fraction unbound, and tissue partition coefficients — resist the pull to reproduce that pattern here. This specific paper may not report any of those, and may not even be a physiologically based model at all.

## STEP 0 — CLASSIFY THE MODEL TYPE BEFORE EXTRACTING ANYTHING

Before extracting any parameter, determine from the page text which of the following the paper is describing:

- **pbpk**: A true physiologically based PK (PBPK) model where compartments correspond to real organs or tissues (liver, kidney, fat, muscle, kidney filtrate/tubule). Parameters include organ blood flows, tissue volumes, or tissue:plasma partition coefficients. A renal filtration/resorption model (Tm, Kt, GFR) is a hallmark of PBPK.
- **simple_empirical_compartmental**: The authors explicitly state the model is not physiologically rigorous. Compartments carry generic names ("central", "peripheral", "deep") and parameters are generic first-order rate constants (k10, k12, k21) or apparent volumes (Vd, CL/F) with no physiological meaning assigned. Keywords: "apparent", "not intended to be physiologically rigorous", "empirical".
- **not_applicable**: No PK model on this page at all (discussion, references, abstract only).

IMPORTANT: A model that names compartments after organs AND uses saturable tubular resorption parameters (Tm, Kt, GFR, filtrate volume) IS a PBPK model, even if called a "compartmental" model by the authors for brevity. Do not classify as simple_empirical just because the paper uses the word "compartment".

Watch for explicit author disclaimers. Only classify as simple_empirical if the authors themselves say the structure is not physiologically rigorous.

## STEP 1 — LOCATE PK-RELEVANT CONTENT; EXCLUDE EVERYTHING ELSE

Identify which regions of the page are genuine candidate sources of PK parameter data: results text, a labeled table of model or PK parameters, or a table caption/footnote.

The following regions must NEVER be treated as a source of parameter data, even if they contain numbers that superficially resemble a schema field:

- Author correspondence blocks (address, telephone, fax, email)
- Article identifiers: DOI, PMID, ISSN, page numbers, volume/issue numbers
- Running headers/footers and journal name banners
- Funding statements, conflict-of-interest statements, publisher disclaimers
- The reference list / bibliography
- Any other bibliographic or administrative metadata

If you see a number next to a label like "Fax," "Tel," "DOI," or "Vol.," it is not a pharmacokinetic parameter under any circumstances, regardless of what unit or symbol it superficially resembles.

## STEP 2 — EXTRACT PARAMETERS

For each PK parameter explicitly reported on the page, capture:

- **parameter_name**: The full descriptive name exactly as printed in the table row label or surrounding text (e.g., "Volume of distribution central compartment", "Saturable resorption rate"). If the table only prints the symbol with no accompanying descriptive label, leave this null. Do NOT invent a name.
- **symbol**: transcribed exactly as printed (e.g., "VCC", "Tmc", "k12", "CL/F"). If the parameter is printed ONLY with a descriptive name and NO mathematical symbol (e.g., "Half-life (years)"), leave this field null. Do not expand, standardize, or "clean up" the symbol.
- **value / range_low / range_high**: The primary value and, if printed as "X (low, high)" format, the bracketed bounds go into range_low and range_high as separate fields.
- **value_qualifier**: any qualifier word or phrase printed with the value beyond the number itself (e.g., "Fixed", "Assumed", "Optimized", "Assumed (PFOS)"). Never drop it or fold it into the numeric value.
- **parameter_status**: How the parameter was obtained, using exactly one of these terms if stated by the authors: "Measured", "Fitted", "Optimized", "Fixed", "Assumed", "Scaled", "Literature". Look for this in a dedicated "Source" or "Method" column in the table. If a table column provides a literature citation (e.g., "Wambaugh et al. (2013)") that is the source of the value, set parameter_status to "Literature". If not stated anywhere, leave null.
- **unit**: exactly as printed. If a unit is stated once for a group of rows (e.g., a section header reading "Elimination constants (1/min)"), apply that inherited unit and set unit_inherited to true.
- **compound**: the specific chemical entity exactly as named on the page. **Extract parameters for ALL compounds present — if a table reports data for PFOS, PFOA, and PFHxS, you must capture entries for all three.**
- **subject_species**: only if explicitly stated. Do not default to "human".
- **population**: only if explicitly stated. Leave null otherwise.
- **source_location**: the table, figure, or section (e.g., "Table 1", "Table 3").
- **source_quote**: a short, exact transcription of the specific cell(s). If you cannot produce a directly-traceable quote, omit the parameter.

## STEP 3 — HANDLE TABLE STRUCTURE CAREFULLY

- **Group headers**: a row spanning the full table width and styled differently from data rows (italic, bold, or otherwise set apart) is a group header, not a parameter — e.g., "Fractional constants" or "Elimination constants (1/min)" as its own row above several parameter rows. Never extract the group header itself as a parameter; apply any unit or context it carries down to the rows beneath it.
- **Multi-row column headers**: if column headers span two or more rows, read down through all header rows before interpreting any data row.
- **Split columns**: some tables place a parameter's descriptive name, symbol, and value in three separate columns. Match them strictly by row position.
- **Per-species or per-population columns**: extract each column as a SEPARATE parameter entry with its own species/population field. Never average, merge, or combine values across columns.

## STEP 4 — MODEL STRUCTURE / TOPOLOGY

If the page shows a compartmental diagram (boxes and arrows) or mass-balance equations, extract the compartment names and their connections into the structure field, using the names EXACTLY as labeled — never substitute standard PBPK compartment names ("Central," "Peripheral," "Deep") for whatever the authors actually wrote, even if the topology looks similar in shape. Equations or diagrams containing no explicit numeric values belong in this structure field, not forced into parameter entries with fabricated values.

## STEP 5 — METADATA

Populate title, authors, journal, and year ONLY if clearly legible on this specific page. Never infer the year from context elsewhere, and never substitute a generic placeholder ("Research Team", "Peer-Reviewed Journal") for a field you cannot read — use null instead. If this is not the title page, most or all metadata fields will correctly be null; that is expected, not a failure.

## STEP 6 — CONFIDENCE

Assign confidence using these concrete criteria, not a general impression of certainty:

- **HIGH**: value, unit, and symbol are all printed together, unambiguously, in a single cell or sentence, with no inheritance or inference required.
- **MEDIUM**: part of the entry required inheriting information from elsewhere on the page (a unit from a group header, a compound from table context several rows above).
- **LOW**: any interpretive judgment was required (degraded text, ambiguous cell boundaries, an abbreviation you are not fully certain of).

Never assign HIGH to an entry that required any inference beyond direct transcription.

## STEP 7 — KNOWN FAILURE PATTERNS: DO NOT REPEAT THESE

- Do not extract a fax number, phone number, or DOI as a parameter value.
- Do not invent a cardiac output, fraction-unbound, or any other "typical" PBPK parameter because the page is pharmacokinetics-related — only extract what this page actually states.
- Do not report multiple species (e.g., "Human, Rat") when only one appears on the page.
- Do not rename the paper's own compartment names to generic equivalents.
- Do not fill metadata gaps with a placeholder string — use null.

## STEP 8 — SELF-CHECK BEFORE RETURNING

Re-read every entry you are about to return and confirm you can point to the specific words or numbers on the page that produced it. Delete any entry you cannot directly justify this way. It is correct and expected to return an empty parameters list if the page contains no PK data — do not manufacture content to avoid an empty result.

## OUTPUT FORMAT

Return ONLY valid JSON matching the schema below. No markdown code fences, no commentary, no explanation text before or after the JSON.

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
        
        try:
            quant_mode = "awq" if use_4bit else None
            actual_model = self.model_path
            dtype = "float16" if use_4bit else "auto"
            
            if use_4bit and "AWQ" not in self.model_path:
                if "Qwen3" in self.model_path:
                    logger.warning("Qwen3-VL AWQ version doesn't exist on HF yet, falling back to unquantized bfloat16.")
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

    async def extract_data(self, image) -> ExtractedPage:
        """Extract table data from image strictly enforcing Pydantic schema"""
        logger.debug("SGLang: Extracting data from image with schema enforcement...")
        
        import uuid
        temp_img_path = f"{Config.TEMP_IMAGE_DIR}/sglang_input_{uuid.uuid4().hex}.jpg"
        image.save(temp_img_path, "JPEG")
        
        schema_json = json.dumps(ExtractedPage.model_json_schema(), indent=2)
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(schema=schema_json)
        
        # Construct the conversation for Qwen-VL manually using its chat template
        prompt_text = (
            f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
            f"<|im_start|>user\n<|vision_start|><|image_pad|><|vision_end|>Extract parameters from this image strictly into the JSON schema.<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )
        
        # Use SGLang's async_generate with pydantic schema enforcement via sampling_params
        # We must use async_generate because this is running inside an active asyncio event loop (FastAPI)
        response = await self.engine.async_generate(
            prompt=prompt_text,
            image_data=temp_img_path,
            sampling_params={
                "max_new_tokens": 10240,
                "temperature": 0.0,
                "repetition_penalty": 1.05,
                "json_schema": json.dumps(ExtractedPage.model_json_schema())
            }
        )
        
        # The response text will be a guaranteed valid JSON string matching the ExtractedPage schema
        extracted_text = response["text"] if isinstance(response, dict) else response.text
        
        try:
            json_data = json.loads(extracted_text)
            extracted_page = ExtractedPage(**json_data)
            logger.info(f"SGLang: Extraction complete. Found {len(extracted_page.parameters)} parameters.")
            return extracted_page
        except Exception as e:
            logger.error(f"Failed to parse SGLang output into Pydantic schema: {e}\nRaw Output: {extracted_text}")
            raise
