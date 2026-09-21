import os
import json
import argparse
import asyncio
import fitz
from pdf2image import convert_from_path

from .schemas import ExtractionRequest
from .ml_services import ColQwenRetriever, SGLangExtractor
from .ingestion.table_cropper import TableCropper
from .config import logger

# Initialize models lazily
retriever = None
extractor = None

def get_retriever():
    global retriever
    if retriever is None:
        print("Loading Retriever Model: vidore/colqwen2.5-v0.2 (this may take a moment)...")
        retriever = ColQwenRetriever()
        print("Retriever model loaded successfully.")
    return retriever

def get_extractor():
    global extractor
    if extractor is None:
        print("Loading Vision-Language Extractor: Qwen3-VL-8B-Instruct (via SGLang)...")
        extractor = SGLangExtractor()
        print("Extractor model loaded successfully.")
    return extractor

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
    from .ingestion.pmc_fetcher import extract_doi_from_pdf, extract_title_from_pdf, resolve_paper
    
    print("Step 0/3: Resolving paper via PMC/EuropePMC/Unpaywall/Semantic Scholar...")
    doi = extract_doi_from_pdf(pdf_path)
    title = extract_title_from_pdf(pdf_path, doi=doi)

    res = {"xml_path": None, "pdf_path": None, "source": None, "source_type": "published"}
    if doi or title:
        res = resolve_paper(doi=doi, title=title, pdf_path=pdf_path)

        if res.get("xml_path"):
            print(f"  -> XML available at {res['xml_path']}! Using JATS XML fast-path...")
            from .ingestion.xml_parser import parse_jats_xml

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
                    pdf_doc = fitz.open(pdf_path)
                    
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
                    from .ingestion.pmc_fetcher import fetch_all_figures
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
    
    # 1. Convert PDF to images
    print("Step 1/3: Converting PDF to images...")
    logger.debug("Step 1: Rasterization")
    images = convert_pdf_to_images(pdf_path)
    print(f"Converted PDF into {len(images)} pages.")
    
    # 2. Run ColQwen2.5 filter to find the exact pages
    print("Step 2/3: Searching for Pharmacokinetic tables across all pages...")
    logger.debug("Step 2: Intra-Document Search")
    # Keep a reference to the original images to find their indices later
    original_images = images.copy()
    
    print("Loading native PDF layer with PyMuPDF...")
    pdf_doc = fitz.open(pdf_path)
    
    # Build dynamic queries
    table_query = "Pharmacokinetic parameters table"
    if target_compounds:
        table_query += f" for {', '.join(target_compounds)}"
        
    diagram_query = "Pharmacokinetic model structure diagram mass balance equations"
    
    text_query = "Pharmacokinetic parameters half-life clearance volume of distribution in text"
        
    print("Searching for tables...")
    table_pages = get_retriever().find_top_pages(images, query=table_query, threshold_ratio=0.75)
    
    print("Searching for structure diagrams...")
    diagram_pages = get_retriever().find_top_pages(images, top_k=2, query=diagram_query, threshold_ratio=0.75)

    print("Searching for narrative text parameters...")
    text_pages = get_retriever().find_top_pages(images, top_k=2, query=text_query, threshold_ratio=0.75)
    
    # 2.5 Crop table regions, but leave diagram and text pages uncropped
    print("Step 2.5: Cropping table regions (leaving diagrams and text uncropped)...")
    cropper = TableCropper()
    
    # Only crop table pages
    cropped_tables = cropper.crop_all(table_pages)
    
    vlm_inputs = []
    
    # 1. Add cropped table pages
    for orig, (cropped, bbox) in zip(table_pages, cropped_tables):
        page_index = original_images.index(orig) + 1 # 1-indexed
        
        # PyMuPDF uses 0-indexed pages
        page = pdf_doc[page_index - 1]
        
        if bbox is None:
            # Full page
            evidence_text = page.get_text("text")
            role = "full_page"
        else:
            # Map 300 DPI bbox to 72 DPI
            scale = 72 / 300
            x1, y1, x2, y2 = bbox
            rect = fitz.Rect(x1 * scale, y1 * scale, x2 * scale, y2 * scale)
            evidence_text = page.get_text("text", clip=rect)
            role = "table_crop"
            
        vlm_inputs.append({"img": cropped, "page_index": page_index, "role": role, "evidence_text": evidence_text})
            
    # 2. Add diagram pages uncropped
    for orig in diagram_pages:
        page_index = original_images.index(orig) + 1
        page = pdf_doc[page_index - 1]
        evidence_text = page.get_text("text")
        vlm_inputs.append({"img": orig, "page_index": page_index, "role": "full_page", "evidence_text": evidence_text})
            
    # 3. Add narrative text pages uncropped
    for orig in text_pages:
        page_index = original_images.index(orig) + 1
        page = pdf_doc[page_index - 1]
        evidence_text = page.get_text("text")
        vlm_inputs.append({"img": orig, "page_index": page_index, "role": "full_page", "evidence_text": evidence_text})
        
    # Deduplicate based on (page_index, role)
    unique_inputs = {}
    for item in vlm_inputs:
        key = (item["page_index"], item["role"])
        if key not in unique_inputs:
            unique_inputs[key] = item
    vlm_inputs = list(unique_inputs.values())
            
    cropped_count = sum(1 for orig, (crop, bbox) in zip(table_pages, cropped_tables) if bbox is not None)
    print(f"Cropped {cropped_count}/{len(cropped_tables)} table pages.")
    
    # Save images to a debug folder for inspection
    pdf_stem = os.path.splitext(os.path.basename(pdf_path))[0]
    debug_dir = os.path.join(os.path.dirname(pdf_path), f"{pdf_stem}_vlm_inputs")
    os.makedirs(debug_dir, exist_ok=True)
    for item in vlm_inputs:
        img_path = os.path.join(debug_dir, f"page_{item['page_index']:02d}_{item['role']}.png")
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
        get_retriever()
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
                with open(output_path, "w") as f:
                    json.dump(result, f, indent=2)
                    
                doc_time = time.time() - doc_start
                print(f"✅ Success! Saved to {output_path} (took {doc_time:.2f}s)")
            except Exception as e:
                print(f"❌ Failed to process {os.path.basename(pdf_path)}: {e}")
                
        batch_time = time.time() - batch_start
        print(f"\n✅ Batch Processing Complete!")
        print(f"   Processed {len(pdf_files)} documents in {batch_time:.2f} seconds.")
        print(f"   Results saved to: {os.path.abspath(args.output_dir)}")
        
    except Exception as e:
        print(f"Fatal Pipeline Error: {e}")

if __name__ == "__main__":
    main()
