import os
import json
import argparse
import asyncio
from pdf2image import convert_from_path

from schemas import ExtractionRequest
from ml_services import ColQwenRetriever, SGLangExtractor
from ingestion.table_cropper import TableCropper
from config import logger

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
    
    # 1. Convert PDF to images
    print("Step 1/3: Converting PDF to images...")
    logger.debug("Step 1: Rasterization")
    images = convert_pdf_to_images(pdf_path)
    print(f"Converted PDF into {len(images)} pages.")
    
    # 2. Run ColQwen2.5 filter to find the exact pages
    print("Step 2/3: Searching for Pharmacokinetic tables across all pages...")
    logger.debug("Step 2: Intra-Document Search")
    
    # Build dynamic queries
    table_query = "Pharmacokinetic parameters table"
    if target_compounds:
        table_query += f" for {', '.join(target_compounds)}"
        
    diagram_query = "Pharmacokinetic model structure diagram mass balance equations"
    
    text_query = "Pharmacokinetic parameters half-life clearance volume of distribution in text"
        
    print("Searching for tables...")
    table_pages = get_retriever().find_top_pages(images, top_k=8, query=table_query, threshold_ratio=0.75)
    
    print("Searching for structure diagrams...")
    diagram_pages = get_retriever().find_top_pages(images, top_k=2, query=diagram_query, threshold_ratio=0.75)

    print("Searching for narrative text parameters...")
    text_pages = get_retriever().find_top_pages(images, top_k=2, query=text_query, threshold_ratio=0.75)
    
    # 2.5 Crop table regions, but leave diagram and text pages uncropped
    print("Step 2.5: Cropping table regions (leaving diagrams and text uncropped)...")
    cropper = TableCropper(padding=25)
    
    # Only crop table pages
    cropped_tables = cropper.crop_all(table_pages)
    
    # Combine table and diagram images (deduplicate if the same page was found in both)
    vlm_inputs = []
    processed_orig_ids = set()
    
    # 1. Add cropped table pages FIRST to guarantee optimal pixel density
    for orig, cropped in zip(table_pages, cropped_tables):
        if id(orig) not in processed_orig_ids:
            vlm_inputs.append(cropped)
            processed_orig_ids.add(id(orig))
            
    # 2. Add diagram pages uncropped
    for orig in diagram_pages:
        if id(orig) not in processed_orig_ids:
            vlm_inputs.append(orig)
            processed_orig_ids.add(id(orig))
            
    # 3. Add narrative text pages uncropped
    for orig in text_pages:
        if id(orig) not in processed_orig_ids:
            vlm_inputs.append(orig)
            processed_orig_ids.add(id(orig))
            
    cropped_count = sum(1 for orig, crop in zip(table_pages, cropped_tables) if crop.size != orig.size)
    print(f"Cropped {cropped_count}/{len(cropped_tables)} table pages.")
    
    # Save images to a debug folder for inspection
    pdf_stem = os.path.splitext(os.path.basename(pdf_path))[0]
    debug_dir = os.path.join(os.path.dirname(pdf_path), f"{pdf_stem}_vlm_inputs")
    os.makedirs(debug_dir, exist_ok=True)
    for idx, img in enumerate(vlm_inputs):
        img_path = os.path.join(debug_dir, f"page_{idx + 1:02d}.png")
        img.save(img_path)
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
    async def bound_extract(img):
        async with sem:
            return await get_extractor().extract_data(img)
            
    tasks = [bound_extract(img) for img in vlm_inputs]
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
            final_document["structure"] = extracted_page.structure.model_dump()
            
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
