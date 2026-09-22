import os
import json
import argparse
import asyncio
import pymupdf
from pdf2image import convert_from_path

from pk_pipeline.schemas import ExtractionRequest
from pk_pipeline.ml_services import SGLangExtractor
from pk_pipeline.config import logger

# Initialize models lazily
extractor = None
tatr_processor = None
tatr_model = None

# Removed ColQwenRetriever as per MinerU migration plan

def get_extractor():
    global extractor
    if extractor is None:
        print("Loading Vision-Language Extractor: Qwen3-VL-8B-Instruct (via SGLang)...")
        extractor = SGLangExtractor()
        print("Extractor model loaded successfully.")
    return extractor

def get_tatr():
    global tatr_processor, tatr_model
    if tatr_processor is None or tatr_model is None:
        print("Loading Table Transformer (TATR) object detection model...")
        from transformers import AutoImageProcessor, TableTransformerForObjectDetection
        tatr_processor = AutoImageProcessor.from_pretrained("microsoft/table-transformer-detection")
        tatr_model = TableTransformerForObjectDetection.from_pretrained("microsoft/table-transformer-detection")
        print("TATR loaded successfully.")
    return tatr_processor, tatr_model

def convert_pdf_to_images(pdf_path: str):
    logger.debug(f"Attempting to convert PDF to images: {pdf_path}")
    if not os.path.exists(pdf_path):
        logger.error(f"File not found: {pdf_path}")
        raise FileNotFoundError(f"File not found: {pdf_path}")
    
    try:
        # 300 DPI for sharper table crops — critical for tiny subscripts (e.g. kg^0.74)
        images = convert_from_path(pdf_path, dpi=300)
        logger.info(f"Successfully converted PDF to {len(images)} images.")
        return images
    except Exception as e:
        logger.error(f"Failed to convert PDF: {str(e)}")
        raise

async def run_pipeline(pdf_path: str, target_compounds: list = None):
    print(f"Starting PK Extraction Pipeline for: {os.path.basename(pdf_path)}")
    logger.info(f"Received request to extract PK data from: {pdf_path}")
    
    # --- NEW: Paper Resolution ---
    from pk_pipeline.ingestion.pmc_fetcher import extract_doi_from_pdf, extract_title_from_pdf, resolve_paper
    
    print("Step 0/3: Resolving paper via PMC/EuropePMC/Unpaywall/Semantic Scholar...")
    doi = extract_doi_from_pdf(pdf_path)
    title = extract_title_from_pdf(pdf_path, doi=doi)

    res = {"xml_path": None, "pdf_path": None, "source": None, "source_type": "published"}
    if doi or title:
        res = resolve_paper(doi=doi, title=title, pdf_path=pdf_path)

        if res.get("xml_path"):
            print(f"  -> XML available at {res['xml_path']}! Using JATS XML fast-path...")
            from pk_pipeline.ingestion.xml_parser import parse_jats_xml

            xml_data = parse_jats_xml(res["xml_path"], filter_narrative=True)

            final_document = {
                "page_metadata": xml_data.get("metadata", {"title": None, "authors": None, "journal": None, "year": None}),
                "model_classification": {"model_type": "not_applicable", "evidence_quote": None},
                "structure": None,
                "parameters": [],
                "ingestion_source": res.get("source"),
                "ingestion_source_type": res.get("source_type", "published"),
            }

            # Filter out chunks that were skipped by the narrative filter
            chunks = [c for c in xml_data.get("chunks", []) if c.get("kept", True)]

            # Separate figure chunks — they may need image download + visual dispatch
            figure_chunks  = [c for c in chunks if c["role"] == "figure_xml"]
            text_chunks    = [c for c in chunks if c["role"] != "figure_xml"]

            diagram_chunks = [c for c in figure_chunks if c.get("is_diagram")]
            caption_chunks = [c for c in figure_chunks if not c.get("is_diagram")]

            # ONLY extract images for chunks that are strictly diagrams
            if diagram_chunks:
                # If we have the local PDF, extract the diagram pages directly from it!
                if pdf_path and os.path.exists(pdf_path):
                    print(f"  -> Extracting {len(diagram_chunks)} diagram images directly from local PDF...")
                    pdf_images = convert_pdf_to_images(pdf_path)
                    pdf_doc = pymupdf.open(pdf_path)
                    
                    for chunk in diagram_chunks:
                        title_to_find = chunk.get("title", "").lower().strip()
                        caption_snippet = chunk.get("caption", "").lower().strip()[:50]
                        best_page_idx = -1
                        
                        for i in range(len(pdf_doc)):
                            page_text = pdf_doc[i].get_text("text").lower()
                            # Prioritize exact caption match
                            if caption_snippet and caption_snippet in page_text:
                                best_page_idx = i
                                break
                            # Fallback to title match
                            elif title_to_find and title_to_find in page_text:
                                best_page_idx = i
                                
                        if best_page_idx != -1:
                            chunk["image_obj"] = pdf_images[best_page_idx]
                            print(f"    - Matched '{title_to_find}' to PDF page {best_page_idx + 1}")
                        else:
                            print(f"    - Could not locate '{title_to_find}' in PDF text.")
                else:
                    # Fallback to PMC downloader if no local PDF was provided
                    from pk_pipeline.ingestion.pmc_fetcher import fetch_all_figures
                    xml_stem = os.path.splitext(os.path.basename(res["xml_path"]))[0]
                    pmcid_for_figs = xml_stem.split("_")[0]
                    print(f"  -> Downloading {len(diagram_chunks)} diagram images from PMC for {pmcid_for_figs}...")
                    diagram_chunks = fetch_all_figures(pmcid_for_figs, diagram_chunks)
                    from PIL import Image
                    for c in diagram_chunks:
                        if c.get("image_path"):
                            try:
                                c["image_obj"] = Image.open(c["image_path"])
                            except Exception as e:
                                print(f"    - Failed to load PMC image {c['image_path']}: {e}")
                
                # Keep only diagrams that have a successfully loaded PIL Image
                diagram_chunks = [c for c in diagram_chunks if "image_obj" in c]

            n_text    = len(text_chunks) + len(caption_chunks)
            n_visual  = len(diagram_chunks)
            print(f"  -> {n_text} text chunks + {n_visual} visual figure chunks queued for LLM.")

            if text_chunks or caption_chunks or diagram_chunks:
                print(f"Step 1/1: Running Extraction ({n_text} text + {n_visual} visual)...")
                # SGLang supports massive continuous batching. Increase concurrency to 10.
                sem = asyncio.Semaphore(10)

                async def bound_extract_text(chunk):
                    async with sem:
                        return await get_extractor().extract_from_text(
                            chunk["content"], 
                            role=chunk["role"], 
                            chunk_title=chunk.get("title", "")
                        )

                async def bound_extract_image(chunk):
                    async with sem:
                        img = chunk["image_obj"]
                        return await get_extractor().extract_data(
                            img,
                            role="figure_crop",
                            evidence_text=f"{chunk['title']}: {chunk['caption']}",
                            chunk_title=chunk.get("title", "")
                        )

                tasks = (
                    [bound_extract_text(c) for c in text_chunks + caption_chunks]
                    + [bound_extract_image(c) for c in diagram_chunks]
                )
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Filter out exceptions and log them
                extracted_chunks = []
                for chunk_idx, res_item in enumerate(results):
                    if isinstance(res_item, Exception):
                        print(f"Warning: Chunk {chunk_idx} failed extraction: {res_item}")
                    else:
                        extracted_chunks.append(res_item)

                for extracted_page in extracted_chunks:
                    if extracted_page and extracted_page.model_classification and extracted_page.model_classification.model_type != "not_applicable":
                        if final_document["model_classification"]["model_type"] == "not_applicable":
                            final_document["model_classification"] = extracted_page.model_classification.model_dump()

                    if extracted_page and extracted_page.structure and not final_document["structure"]:
                        final_document["structure"] = extracted_page.structure.model_dump(by_alias=True, exclude_none=True)

                    if extracted_page.parameters:
                        final_document["parameters"].extend([p.model_dump() for p in extracted_page.parameters])

            logger.info("Successfully completed XML extraction fast-path.")
            return final_document

        if res.get("pdf_path") and res.get("source") in ["unpaywall", "semantic_scholar", "biorxiv", "medrxiv"]:
            print(f"  -> Switching from local PDF to Open Access PDF ({res['source']}): {res['pdf_path']}")
            if res.get("source_type") == "preprint":
                print(f"  -> ⚠️  Source is a PREPRINT — results will carry ingestion_source_type='preprint'.")
            pdf_path = res["pdf_path"]
    else:
        print("  -> Could not extract DOI or Title from local PDF. Proceeding with local file.")
    # -----------------------------
    
    # 1. Look for MinerU Output
    print("Step 1/3: Locating MinerU structured layout output...")
    logger.debug("Step 1: MinerU Parsing")
    
    pdf_dir = os.path.dirname(pdf_path)
    pdf_stem = os.path.splitext(os.path.basename(pdf_path))[0]
    
    mineru_json_path = None
    candidates = [
        os.path.join(pdf_dir, pdf_stem, "auto", "content_list.json"),
        os.path.join(pdf_dir, pdf_stem, "auto", "middle.json"),
        os.path.join(pdf_dir, "output", pdf_stem, "auto", "content_list.json"),
        os.path.join(pdf_dir, "output", pdf_stem, "auto", "middle.json"),
        os.path.join(pdf_dir, pdf_stem, "content_list.json"),
        os.path.join(pdf_dir, pdf_stem, "middle.json")
    ]
    for c in candidates:
        if os.path.exists(c):
            mineru_json_path = c
            break
            
    if not mineru_json_path:
        print(f"  -> MinerU structured output not found. Attempting PyMuPDF4LLM fallback extraction...")
        logger.debug("Falling back to PyMuPDF4LLM extraction.")
        
        import pymupdf4llm
        from PIL import Image
        import io
        
        md_chunks = pymupdf4llm.to_markdown(pdf_path, page_chunks=True)
        pdf_doc = pymupdf.open(pdf_path)
        
        import re
        table_pattern = re.compile(r"(?:^\|.*\|$\n)+(?:^\|[\-\s:|]+\|$\n)(?:^\|.*\|$\n?)*", re.MULTILINE)
        
        llm_payloads = []
        for i, chunk in enumerate(md_chunks):
            page_num = i + 1
            text = chunk.get("text", "")
            has_image = len(pdf_doc[i].get_images()) > 0
            has_table = bool(table_pattern.search(text))
            
            # Generate a full page screenshot if there are tables, to give Qwen visual context
            full_page_img = None
            if has_table:
                page = pdf_doc[i]
                # Keep high-res rendering
                pix = page.get_pixmap(matrix=pymupdf.Matrix(300/72, 300/72))
                full_page_img = Image.open(io.BytesIO(pix.tobytes())).convert("RGB")
                
                # --- NEW: TATR Cropping ---
                print(f"  -> Table detected on page {page_num}. Running TATR to crop...")
                import torch
                t_processor, t_model = get_tatr()
                inputs = t_processor(images=full_page_img, return_tensors="pt")
                with torch.no_grad():
                    outputs = t_model(**inputs)
                
                target_sizes = torch.tensor([full_page_img.size[::-1]])
                results = t_processor.post_process_object_detection(outputs, threshold=0.7, target_sizes=target_sizes)[0]
                
                best_box = None
                best_score = 0
                for score, label, box in zip(results["scores"], results["labels"], results["boxes"]):
                    if label.item() == 0 and score.item() > best_score:  # Class 0 is 'table'
                        best_score = score.item()
                        best_box = [int(i) for i in box.tolist()]
                        
                if best_box:
                    print(f"     - Found table with score {best_score:.3f}. Cropping...")
                    x_min, y_min, x_max, y_max = best_box
                    # Add generous padding (40px) to ensure no text is cut off
                    padding = 40
                    x_min, y_min = max(0, x_min - padding), max(0, y_min - padding)
                    x_max, y_max = min(full_page_img.width, x_max + padding), min(full_page_img.height, y_max + padding)
                    full_page_img = full_page_img.crop((x_min, y_min, x_max, y_max))
                else:
                    print("     - TATR failed to find table. Falling back to full page image.")
                # --------------------------
            
            # 1. If there's an image (diagram/figure), send the full page text as evidence for the image crop
            if has_image:
                page = pdf_doc[i]
                pix = page.get_pixmap(matrix=pymupdf.Matrix(300/72, 300/72))
                img_obj = Image.open(io.BytesIO(pix.tobytes()))
                llm_payloads.append({
                    "role": "figure_crop",
                    "page": page_num,
                    "img_obj": img_obj,
                    "markdown_context": text,
                    "part": "figure"
                })
                
            # 2. Split the page text into separate table and narrative chunks
            last_end = 0
            part_idx = 1
            for match in table_pattern.finditer(text):
                start, end = match.span()
                if start > last_end:
                    narrative = text[last_end:start].strip()
                    if len(narrative) > 50:
                        llm_payloads.append({"role": "narrative_xml", "page": page_num, "part": part_idx, "markdown_context": narrative})
                        part_idx += 1
                table = text[start:end].strip()
                llm_payloads.append({
                    "role": "table_xml", 
                    "page": page_num, 
                    "part": part_idx, 
                    "markdown_context": table,
                    "full_page_img": full_page_img
                })
                part_idx += 1
                last_end = end
                
            if last_end < len(text):
                narrative = text[last_end:].strip()
                if len(narrative) > 50:
                    llm_payloads.append({"role": "narrative_xml", "page": page_num, "part": part_idx, "markdown_context": narrative})
            
        print(f"  -> Separated {len(md_chunks)} pages into {len(llm_payloads)} distinct chunks (tables, figures, text). Running LLM extraction concurrently...")
        
        sem = asyncio.Semaphore(5)
        async def bound_extract(p):
            async with sem:
                role = p.get("role")
                if role == "figure_crop":
                    return await get_extractor().extract_data(
                        p["img_obj"],
                        role="figure_crop",
                        evidence_text=p["markdown_context"],
                        chunk_title=f"Page {p['page']} Figure"
                    )
                elif role == "table_xml" and p.get("full_page_img"):
                    return await get_extractor().extract_data(
                        p["full_page_img"],
                        role="page_with_table",
                        evidence_text=p["markdown_context"],
                        chunk_title=f"Page {p['page']} Part {p.get('part', 1)}"
                    )
                else:
                    return await get_extractor().extract_from_text(
                        p["markdown_context"],
                        role=role,
                        chunk_title=f"Page {p['page']} Part {p.get('part', 1)}"
                    )
                    
        tasks = [bound_extract(p) for p in llm_payloads]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        final_document = {
            "page_metadata": {"title": None, "authors": None, "journal": None, "year": None},
            "model_classification": {"model_type": "not_applicable", "evidence_quote": None},
            "structure": None,
            "parameters": []
        }
        
        for chunk_idx, res_item in enumerate(results):
            if isinstance(res_item, Exception):
                print(f"Warning: Page {chunk_idx+1} failed extraction: {res_item}")
            else:
                extracted_page = res_item
                if extracted_page and extracted_page.model_classification and extracted_page.model_classification.model_type != "not_applicable":
                    if final_document["model_classification"]["model_type"] == "not_applicable":
                        final_document["model_classification"] = extracted_page.model_classification.model_dump()
                if extracted_page and extracted_page.structure and not final_document["structure"]:
                    final_document["structure"] = extracted_page.structure.model_dump(by_alias=True, exclude_none=True)
                if extracted_page and extracted_page.parameters:
                    final_document["parameters"].extend([p.model_dump() for p in extracted_page.parameters])
                    
        logger.info("Successfully completed PyMuPDF fallback extraction.")
        return final_document
        
    print(f"Found MinerU structured output: {mineru_json_path}")
    
    with open(mineru_json_path, "r", encoding="utf-8") as f:
        mineru_data = json.load(f)
        
    # Handle both VLM backend (list of blocks) and Pipeline backend (dict with pdf_info)
    blocks = []
    if isinstance(mineru_data, list):
        blocks = mineru_data
    elif isinstance(mineru_data, dict) and "pdf_info" in mineru_data:
        for page in mineru_data["pdf_info"]:
            blocks.extend(page.get("blocks", []))
    else:
        # Generic fallback if structure differs slightly
        blocks = mineru_data.get("blocks", [])

    print(f"MinerU identified {len(blocks)} total document blocks.")

    # 2. Filter blocks for Tables and Figures using Relevance Keywords
    print("Step 2/3: Filtering for Pharmacokinetic tables and figures...")
    logger.debug("Step 2: Candidate Relevance Filtering")
    
    table_keywords = ["pharmacokinetic", "parameter", "pk", "clearance", "volume of distribution", "half-life"]
    if target_compounds:
        table_keywords.extend([c.lower() for c in target_compounds])
        
    diagram_keywords = ["pharmacokinetic", "model structure", "diagram", "mass balance", "pbpk"]
    
    pdf_doc = pymupdf.open(pdf_path)
    vlm_inputs = []
    
    def normalize_bbox(bbox, page_width, page_height):
        # MinerU bboxes might be [x0, y0, x1, y1]
        return bbox
        
    for block in blocks:
        block_type = block.get("type", "")
        if block_type not in ["table", "image", "figure"]:
            continue
            
        # Extract metadata flexibly
        # VLM backend might use 'page_idx', pipeline might use 'page_no'
        page_idx = block.get("page_idx", block.get("page_no", 0))
        if isinstance(page_idx, str):
            page_idx = int(page_idx)
            
        bbox = block.get("bbox")
        if not bbox or len(bbox) != 4:
            continue
            
        # Extract evidence text via PyMuPDF around the bbox
        try:
            page = pdf_doc[page_idx]
        except IndexError:
            # MinerU might 1-index pages?
            try:
                page = pdf_doc[page_idx - 1]
                page_idx -= 1
            except IndexError:
                continue
                
        # Get caption from MinerU or fallback to extracting text directly around bbox
        caption = block.get("text", block.get("caption", "")).lower()
        
        # PyMuPDF uses points. We assume MinerU bbox is in points. 
        # If it's normalized, this will fail, but we assume points for now.
        x0, y0, x1, y1 = bbox
        rect = pymupdf.Rect(x0, y0, x1, y1)
        evidence_text = page.get_text("text", clip=rect)
        
        # Expand rect slightly to capture nearby caption if MinerU missed it
        expanded_rect = pymupdf.Rect(max(0, x0 - 20), max(0, y0 - 40), x1 + 20, y1 + 40)
        surrounding_text = page.get_text("text", clip=expanded_rect).lower()
        
        search_text = caption + " " + surrounding_text
        
        if block_type == "table":
            if any(kw in search_text for kw in table_keywords):
                # We have a relevant table!
                # Render the crop at 300 DPI
                pix = page.get_pixmap(matrix=pymupdf.Matrix(300/72, 300/72), clip=rect)
                from PIL import Image
                import io
                img = Image.open(io.BytesIO(pix.tobytes()))
                
                vlm_inputs.append({
                    "img": img, 
                    "page_index": page_idx + 1, 
                    "role": "table_crop", 
                    "evidence_text": evidence_text
                })
                
        elif block_type in ["image", "figure"]:
            if any(kw in search_text for kw in diagram_keywords):
                # Render the crop at 300 DPI
                pix = page.get_pixmap(matrix=pymupdf.Matrix(300/72, 300/72), clip=rect)
                from PIL import Image
                import io
                crop_img = Image.open(io.BytesIO(pix.tobytes()))
                
                # We optionally send the full page as well if needed, but for now we send the precise crop
                # The user's plan: "Primary image: a fresh crop... Secondary image: full page (optional)"
                # To keep it simple and avoid modifying SGLang extractor signature, we pass the crop.
                vlm_inputs.append({
                    "img": crop_img, 
                    "page_index": page_idx + 1, 
                    "role": "figure_crop", 
                    "evidence_text": surrounding_text,
                    "chunk_title": caption[:50]
                })

    print(f"Queued {len(vlm_inputs)} filtered regions for LLM extraction.")
    
    # Save images to a debug folder for inspection
    debug_dir = os.path.join(pdf_dir, f"{pdf_stem}_vlm_inputs")
    os.makedirs(debug_dir, exist_ok=True)
    for idx, item in enumerate(vlm_inputs):
        img_path = os.path.join(debug_dir, f"candidate_{idx:02d}_page_{item['page_index']}_{item['role']}.png")
        item['img'].save(img_path)
    print(f"Saved {len(vlm_inputs)} VLM input images to: {debug_dir}")
    
    # 3. Extract data using SGLang with schema enforcement
    print(f"Step 3/3: Running VLM extraction on {len(vlm_inputs)} images concurrently...")
    logger.debug("Step 3: Targeted Extraction across multiple pages")
    
    final_document = {
        "page_metadata": {"title": None, "authors": None, "journal": None, "year": None},
        "model_classification": {"model_type": "not_applicable", "evidence_quote": None},
        "structure": None,
        "parameters": []
    }
    # Use a Semaphore to limit concurrency to 2 pages at a time to prevent GPU OOM deadlocks
    sem = asyncio.Semaphore(2)
    async def bound_extract(item):
        async with sem:
            return await get_extractor().extract_data(item["img"], role=item["role"], evidence_text=item.get("evidence_text", ""))
            
    tasks = [bound_extract(item) for item in vlm_inputs]
    extracted_pages = await asyncio.gather(*tasks)
    
    for extracted_page in extracted_pages:
        
        # Merge metadata
        if extracted_page.page_metadata:
            pm = extracted_page.page_metadata
            if not final_document["page_metadata"]["title"] and pm.title:
                final_document["page_metadata"]["title"] = pm.title
            if not final_document["page_metadata"]["authors"] and pm.authors:
                final_document["page_metadata"]["authors"] = pm.authors
            if not final_document["page_metadata"]["journal"] and pm.journal:
                final_document["page_metadata"]["journal"] = pm.journal
            if not final_document["page_metadata"]["year"] and pm.year:
                final_document["page_metadata"]["year"] = pm.year
        
        # Merge model_classification (take the first meaningful one)
        if extracted_page.model_classification and extracted_page.model_classification.model_type != "not_applicable":
            if final_document["model_classification"]["model_type"] == "not_applicable":
                final_document["model_classification"] = extracted_page.model_classification.model_dump()
        
        # Merge structure (take the first one we find)
        if extracted_page.structure and not final_document["structure"]:
            final_document["structure"] = extracted_page.structure.model_dump(by_alias=True, exclude_none=True)
            
        # Aggregate all parameters
        if extracted_page.parameters:
            final_document["parameters"].extend([p.model_dump() for p in extracted_page.parameters])
    
    logger.info("Successfully completed extraction pipeline.")
    return final_document

import time

import glob

def main():
    parser = argparse.ArgumentParser(description="Run the PK Parameter Extraction Pipeline")
    parser.add_argument("input_paths", type=str, nargs="+", help="Path to one or more PDF files or directories of PDFs to extract")
    parser.add_argument("--compounds", nargs="+", help="Optional: Target compounds to steer search (e.g., PFOS PFOA)")
    parser.add_argument("--output_dir", type=str, default="output", help="Optional: Directory to save the extracted JSONs. Defaults to 'output'.")
    
    args = parser.parse_args()
    
    # Gather all PDF files to process
    pdf_files = []
    for path in args.input_paths:
        if not os.path.exists(path):
            print(f"Warning: The path '{path}' does not exist. Skipping.")
            continue
            
        if os.path.isdir(path):
            found_pdfs = glob.glob(os.path.join(path, "*.pdf"))
            if not found_pdfs:
                print(f"Warning: No PDF files found in directory '{path}'.")
            pdf_files.extend(found_pdfs)
        else:
            if not path.lower().endswith(".pdf"):
                print(f"Warning: Input file '{path}' does not have a .pdf extension.")
            pdf_files.append(path)
            
    # Deduplicate the list to avoid processing the same file twice
    pdf_files = list(set(pdf_files))
            
    if not pdf_files:
        print("Error: No valid PDF files found to process.")
        return
        
    print(f"Found {len(pdf_files)} total PDFs to process...")
        
    os.makedirs(args.output_dir, exist_ok=True)

    try:
        # Pre-load models once for the entire batch
        print("Booting AI models into GPU memory. This is a one-time 'cold start' penalty...")
        load_start = time.time()
        get_extractor()
        load_time = time.time() - load_start
        print(f"Models successfully loaded into VRAM in {load_time:.2f} seconds.\n")

        # Process each PDF sequentially
        batch_start = time.time()
        for idx, pdf_path in enumerate(pdf_files, 1):
            print(f"\n{'='*60}")
            print(f"Processing Document {idx}/{len(pdf_files)}: {os.path.basename(pdf_path)}")
            print(f"{'='*60}")
            
            doc_start = time.time()
            try:
                result = asyncio.run(run_pipeline(pdf_path, args.compounds))
                
                base_name = os.path.splitext(os.path.basename(pdf_path))[0]
                output_path = os.path.join(args.output_dir, f"{base_name}.json")
                
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                    
                doc_time = time.time() - doc_start
                print(f"  Success! Saved to {output_path} (took {doc_time:.2f}s)")
            except Exception as e:
                print(f"  Failed to process {os.path.basename(pdf_path)}: {e}")
                
        batch_time = time.time() - batch_start
        print(f"   Batch Processing Complete!")
        print(f"   Processed {len(pdf_files)} documents in {batch_time:.2f} seconds.")
        print(f"   Results saved to: {os.path.abspath(args.output_dir)}")
        
    except Exception as e:
        print(f"Fatal Pipeline Error: {e}")

if __name__ == "__main__":
    main()
