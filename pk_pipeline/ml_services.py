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

SYSTEM_PROMPT_TEMPLATE = """You are an OECD GD 331 compliant pharmacokinetic (PK) data extraction system. You are provided with a section of a scientific paper (which may be a page image, a raw XML/Markdown table, or narrative text). Your task is to extract pharmacokinetic parameters, model structure, and study metadata that are EXPLICITLY PRESENT on this page, and return them in the exact JSON schema provided below.

## THE SINGLE MOST IMPORTANT RULE (NULL POLICY)
Extract only what is visually present on this page. Never supply a parameter, value, species, compound, or metadata field from general pharmacological knowledge. If a piece of information is not legible or not explicitly stated on this page, you MUST use 'not_reported', 'unclear', or 'not_applicable'. Do not leave it null if a string is expected, and do not invent a placeholder.

## STEP 0 — CLASSIFY THE MODEL TYPE BEFORE EXTRACTING ANYTHING
Before extracting any parameter, determine from the page text which of the following the paper is describing:
- **pbpk**: A true physiologically based PK (PBPK) model where compartments correspond to real organs or tissues.
- **simple_empirical_compartmental**: The authors explicitly state the model is not physiologically rigorous (e.g. 1, 2, or 3 compartment models).
- **not_applicable**: No PK model on this page at all (discussion, references, abstract only).

## STEP 1 — EXTRACT BIOLOGICAL BASIS AND MODEL STRUCTURE
If the text describes the model structure, extract the following:
- **Model Context:** Origin (new, adapted, reused), purpose, and dose metric.
- **Biological Basis:** Extract explicit quotes for any stated assumptions (e.g., 'well-stirred compartment').
- **Model Structure:** List all compartment names. Specify if ODEs/equations are provided in the text or SI. Extract explicit allometric scaling rules (e.g., 'QC = QCC * BW^0.75').
- **Metabolic Pathways:** Identify the parent compound, enzyme (e.g., CYP1A2), location, and kinetics type (clearance_based, michaelis_menten, etc.).

## STEP 2 — EXTRACT PARAMETERS
For each PK parameter explicitly reported on the page, capture:
- **parameter_name_original**: The full descriptive name exactly as printed.
- **symbol_original**: transcribed exactly as printed.
- **value_text**: The exact printed text of the value, verbatim.
- **value / range_start / range_end**: The primary numeric value and bounds.
- **unit_original**: exactly as printed.
- **compound**: the specific chemical entity exactly as named on the page.
- **subject_species**: ONLY use actual species names like 'human', 'rat', 'mouse'.
- **provenance.status**: MUST be one of 'measured_here', 'literature', 'in_vitro_ivive', 'predicted_qsar', 'fitted', 'assumed_default', or 'not_reported'.

## STEP 3 — HANDLE TABLE STRUCTURE CAREFULLY
- **Group headers and Nested Rows**: Prepend super-headers to row names (e.g., "Blood flow to organ (fraction) - Liver").
- **Per-species/Per-compound Grids**: Extract a SEPARATE record for EVERY populated cell in the grid.
- **Implied Species Transitions**: Group parameters into `parameter_blocks` by species/context.

## OUTPUT FORMAT
Return ONLY valid JSON matching the schema below. No markdown code fences, no commentary.

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
4. Return an EMPTY `parameter_blocks` array (`"parameter_blocks": []`). Your only goal is to fill out the `model_structure` field and `model_classification`.
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
            n_params = sum(len(b.parameters) for b in extracted_page.parameter_blocks) if extracted_page.parameter_blocks else 0
            logger.info(f"SGLang: [END] Image extraction{title_log} complete in {duration:.2f}s. Found {n_params} parameters.")
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
            n_params = sum(len(b.parameters) for b in extracted_page.parameter_blocks) if extracted_page.parameter_blocks else 0
            logger.info(f"SGLang: [END] Text extraction{title_log} complete in {duration:.2f}s. Found {n_params} parameters.")
            return extracted_page
        except Exception as e:
            logger.error(f"Failed to parse SGLang output into Pydantic schema: {e}\nRaw Output: {extracted_text}")
            raise

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
                    "max_new_tokens": 8000,
                    "temperature": 0.0,
                    "repetition_penalty": 1.0
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
                        "repetition_penalty": 1.0
                    }
                }
                async with session.post("http://127.0.0.1:30001/generate", json=payload) as resp:
                    result = await resp.json()
                    extracted_text = result["text"]
        else:
            response = await self.engine.async_generate(
                prompt=prompt_text,
                sampling_params={
                    "max_new_tokens": 8000,
                    "temperature": 0.0,
                    "repetition_penalty": 1.0
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


