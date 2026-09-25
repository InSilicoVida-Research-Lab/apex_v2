import torch
from typing import List
from PIL import Image
import json
import os

from .schemas import ExtractedPage, ExtractedParameter
from .config import logger, Config

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

SYSTEM_PROMPT_TEMPLATE = """You are a pharmacokinetic (PK) data extraction system. You are provided with a section of a scientific paper (which may be a page image, a raw XML/Markdown table, or narrative text). Your task is to extract pharmacokinetic parameters, model structure, and study metadata that are EXPLICITLY PRESENT on this page, and return them in the exact JSON schema provided below. You are not being asked to know pharmacology — you are being asked to transcribe faithfully what is printed on this page.

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
- Sensitivity Analysis, Validation, and Results tables. Extract only intrinsic Model Input Parameters.
- Any other bibliographic or administrative metadata

If you see a number next to a label like "Fax," "Tel," "DOI," or "Vol.," it is not a pharmacokinetic parameter under any circumstances, regardless of what unit or symbol it superficially resembles.

## STEP 2 — EXTRACT PARAMETERS

For each PK parameter explicitly reported on the page, capture:

- **parameter_name**: The full descriptive name exactly as printed in the table row label or surrounding text (e.g., "Volume of distribution central compartment", "Saturable resorption rate"). This field is REQUIRED. If the table only prints the symbol with no accompanying descriptive label, use the symbol as the parameter name. Do NOT invent a name.
- **symbol**: transcribed exactly as printed (e.g., "VCC", "Tmc", "k12", "CL/F"). If the parameter is printed ONLY with a descriptive name and NO mathematical symbol (e.g., "Half-life (years)"), leave this field null. Do not expand, standardize, or "clean up" the symbol.
- **value_text**: The exact printed text of the value, verbatim (e.g., '5a', '0.008b', '<1', '~3'). You MUST always populate this if a value exists.
- **value / range_low / range_high**: The primary value and bounds. ONLY populate `value` if the `value_text` can be safely parsed as a pure float (e.g., '5.0', '0.008'). If it contains letters (e.g. '0.008b') leave `value` null.
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
- **Per-species or per-population columns**: If a table has columns for different groups (e.g., 'Mother' vs 'Fetus', 'Human' vs 'Rat'), extract each column as a SEPARATE parameter entry. Map the column header to the appropriate `subject_species`, `life_stage`, or `population` field in the Biological Context. Never average, merge, or combine values across columns.
- **Multiple Formulations in Columns**: If a column header specifies multiple formulations (e.g., 'Rilutor, ASD') and a cell contains comma-separated values (e.g., '0.69, 2.19'), DO NOT map these to range_low and range_high. Instead, create two distinct ExtractedParameter entries and map the values to their respective formulations in the BiologicalContext.
- **Section Headers**: Pay strict attention to sub-headers spanning the table (e.g., 'Rat' vs. 'Human'). Ensure that all parameters following a species sub-header are assigned the correct subject_species until a new sub-header appears.
- **Footnotes**: Extract specific mathematical constants (e.g., Blood-to-plasma ratio = 1.1) hidden in table footnotes as standalone parameters.

## STEP 4 — MODEL STRUCTURE / TOPOLOGY

If the page shows a compartmental diagram (boxes and arrows) or mass-balance equations, extract the compartment names and their connections into the structure field, using the names EXACTLY as labeled — never substitute standard PBPK compartment names ("Central," "Peripheral," "Deep") for whatever the authors actually wrote, even if the topology looks similar in shape. Equations or diagrams containing no explicit numeric values belong in this structure field, not forced into parameter entries with fabricated values.

## STEP 5 — METADATA

Populate title, authors, journal, and year ONLY if clearly legible on this specific page. Never infer the year from context elsewhere, and never substitute a generic placeholder ("Research Team", "Peer-Reviewed Journal") for a field you cannot read — use null instead. If this is not the title page, most or all metadata fields will correctly be null; that is expected, not a failure.

## STEP 6 — CONFIDENCE

Assign confidence using these concrete criteria, not a general impression of certainty:

- **HIGH**: value, unit, and symbol are all printed together, unambiguously, in a single cell or sentence, with no inheritance or inference required.
- **MEDIUM**: part of the entry required inheriting information from elsewhere on the page (a unit from a group header, a compound from table context several rows above).
- **LOW**: any interpretive judgment was required (degraded text, ambiguous cell boundaries, an abbreviation you are not fully certain of).
- **needs_review**: Set this boolean to `true` if a table cell is merged, if a range is highly ambiguous, if there are multiple conflicting footnotes, or if you are unsure how to bind the value to a specific species/compartment. Otherwise, set it to `false`.

Never assign HIGH to an entry that required any inference beyond direct transcription.

## STEP 7 — KNOWN FAILURE PATTERNS: DO NOT REPEAT THESE
- Do not extract a fax number, phone number, or DOI as a parameter value.
- Do not invent typical PBPK parameters if they are not explicitly printed on the page. However, you MUST extract ALL physiological parameters (e.g., cardiac output, tissue volumes, blood flows, fraction-unbound) that ARE explicitly printed in the table. 
- If a parameter is a physiological constant (like liver volume) and does not specify a chemical compound, extract it and set the compound field to "Physiological".
- Do not report multiple species (e.g., "Human, Rat") when only one appears on the page.
- Do not rename the paper's own compartment names to generic equivalents.
- Do not fill metadata gaps with a placeholder string — use null.

## STEP 8 — SELF-CHECK BEFORE RETURNING

Re-read every entry you are about to return and confirm you can point to the specific words or numbers on the page that produced it. Delete any entry you cannot directly justify this way. It is correct and expected to return an empty parameters list if the page contains no PK data — do not manufacture content to avoid an empty result.

## OUTPUT FORMAT

Return ONLY valid JSON matching the schema below. No markdown code fences, no commentary, no explanation text before or after the JSON.

{schema}
"""

DIAGRAM_PROMPT_TEMPLATE = """You are a pharmacokinetic (PK) model analyzer. You are shown an image of a model structure diagram (e.g., boxes and arrows representing a PBPK or compartmental model) from a scientific paper. 

Your task is strictly to extract the model structure, compartments, and connections shown in this diagram, and return them in the exact JSON schema provided below. 

## INSTRUCTIONS
1. Do NOT attempt to extract numerical pharmacokinetic parameters (like half-life, clearance, or volumes) from this diagram, even if a number is written next to an arrow. 
2. Set the `model_classification` based on the diagram. If the boxes represent physical organs (Liver, Kidney, Gut), it is `pbpk`. If they are generic (Central, Peripheral), it is `simple_empirical_compartmental`.
3. Fill out the `structure` object with `compartments` and `connections`:
   - **compartments**: Extract every box in the diagram as a compartment. Set `label_raw` to exactly what is written in the box (e.g., "Liver", "Fat", "Slowly perfused"). Set `id` to a short unique string (e.g., "liver", "c1").
   - **connections**: Extract every arrow as a connection. Set `source` and `target` to the `id` of the respective compartments. Set `direction` based on the arrowhead ("forward", "bidirectional"). If an arrow goes to/from outside the model (e.g., an excretion arrow leaving the Liver with no target box), use "external" as the missing `id`. If a label is written on the arrow (e.g., "Q_liver", "CL_int", "IV dose"), put it in `label_raw`.
4. Return an EMPTY `parameters` array (`"parameters": []`). Your only goal is to fill out the `structure` field and `model_classification`.
5. Return ONLY valid JSON matching the schema below. No markdown code fences, no commentary.

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

    async def extract_data(self, image: Image.Image, role: str = "table_crop", evidence_text: str = "", chunk_title: str = "") -> ExtractedPage:
        """Extract table data from image strictly enforcing Pydantic schema"""
        if not getattr(self, "is_loaded", False):
            raise RuntimeError("SGLangExtractor failed to load. Ensure the SGLang server is running and accessible.")
            
        import time
        start_t = time.time()
        title_log = f" ({chunk_title})" if chunk_title else ""
        logger.info(f"SGLang: [START] Extracting data from {role} image{title_log}...")
        
        import uuid
        temp_img_path = f"{Config.TEMP_IMAGE_DIR}/sglang_input_{uuid.uuid4().hex}.jpg"
        image.save(temp_img_path, "JPEG")
        
        schema_json = json.dumps(ExtractedPage.model_json_schema(), indent=2)
        
        if role == "figure_crop":
            system_prompt = DIAGRAM_PROMPT_TEMPLATE.format(schema=schema_json)
        else:
            system_prompt = SYSTEM_PROMPT_TEMPLATE.format(schema=schema_json)
        
        user_instruction = "Extract parameters from this image strictly into the JSON schema."
        if role == "table_crop":
            user_instruction += " This is a tightly cropped table image. Focus on exact transcription of table values. BYPASS STEP 0: This is a confirmed PK table, so do NOT classify as 'not_applicable'. Extract the parameters directly."
        elif role == "page_with_table":
            user_instruction += " This is a full page image containing a table. Focus ONLY on extracting the parameters that are present in the provided Markdown text snippet below. Use the image purely for visual layout context to correctly read the table rows/columns."
        elif role == "full_page":
            user_instruction += " This is a full page image. Extract any pharmacokinetic parameters you find in tables, text, or diagrams, using the surrounding text for biological context."

        if evidence_text and evidence_text.strip():
            user_instruction += (
                f"\n\nUse the following native PDF text extracted from this region as evidence hints "
                f"to avoid hallucinating names or values:\n\n{evidence_text.strip()}"
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
            json_data = json.loads(extracted_text)
            extracted_page = ExtractedPage(**json_data)
            duration = time.time() - start_t
            title_log = f" ({chunk_title})" if chunk_title else ""
            logger.info(f"SGLang: [END] Image extraction{title_log} complete in {duration:.2f}s. Found {len(extracted_page.parameters)} parameters.")
            return extracted_page
        except Exception as e:
            logger.error(f"Failed to parse SGLang output into Pydantic schema: {e}\nRaw Output: {extracted_text}")
            raise

    async def extract_from_text(self, text: str, role: str = "table_xml", chunk_title: str = "") -> ExtractedPage:
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
                f"This is a raw HTML/XML table. Focus on exact transcription of table values.\n\n"
                f"CRITICAL INSTRUCTIONS FOR THIS TABLE:\n"
                f"1. For STEP 0, this is a confirmed PK table. You MUST classify `model_type` as either 'pbpk' or 'simple_empirical_compartmental' based on the parameters shown. Do not use 'not_applicable'.\n"
                f"2. If page metadata (Title, Authors, Journal) is not visible in this specific table block, output null for those fields as instructed in Step 5.\n"
                f"3. Map the column headers to their respective parameter entries (e.g., values under 'Mother' get life_stage='Mother').\n\n"
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
        
        if getattr(self, "use_server", False):
            import aiohttp
            # Set a 1-hour timeout to prevent long extractions (like Page 6) from hitting aiohttp's 5-min default timeout
            timeout = aiohttp.ClientTimeout(total=3600)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                payload = {
                    "text": prompt_text,
                    "sampling_params": {
                        "max_new_tokens": 16000,
                        "temperature": 0.0,
                        "repetition_penalty": 1.0
                    }
                }
                async with session.post(f"{self.server_url}/generate", json=payload) as resp:
                    result = await resp.json()
                    extracted_text = result["text"]
        else:
            response = await self.engine.async_generate(
                prompt=prompt_text,
                sampling_params={
                    "max_new_tokens": 16000,
                    "temperature": 0.0,
                    "repetition_penalty": 1.0
                }
            )
            extracted_text = response["text"] if isinstance(response, dict) else response.text
        
        # 1. Strip <think> tags if present
        if "</think>" in extracted_text:
            extracted_text = extracted_text.split("</think>")[-1].strip()
            
        # 2. Extract JSON from markdown blocks if present
        import re
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", extracted_text, re.DOTALL)
        if match:
            extracted_text = match.group(1).strip()
        else:
            # Strip any trailing/leading whitespace just in case
            extracted_text = extracted_text.strip()
            
        try:
            json_data = json.loads(extracted_text)
            extracted_page = ExtractedPage(**json_data)
            duration = time.time() - start_t
            title_log = f" ({chunk_title})" if chunk_title else ""
            logger.info(f"SGLang: [END] Text extraction{title_log} complete in {duration:.2f}s. Found {len(extracted_page.parameters)} parameters.")
            return extracted_page
        except Exception as e:
            logger.error(f"Failed to parse SGLang output into Pydantic schema: {e}\nRaw Output: {extracted_text}")
            raise
