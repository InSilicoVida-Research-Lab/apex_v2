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
        print("\n⏳ Loading Retriever Model: vidore/colqwen2.5-v0.2 (this may take a moment)...")
        retriever = ColQwenRetriever()
        print("✅ Retriever model loaded successfully.")
    return retriever

def get_extractor():
    global extractor
    if extractor is None:
        print("\n⏳ Loading Vision-Language Extractor: Qwen3-VL-8B-Instruct (via SGLang)...")
        extractor = SGLangExtractor()
        print("✅ Extractor model loaded successfully.")
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
    print(f"\n🚀 Starting PK Extraction Pipeline for: {os.path.basename(pdf_path)}")
    logger.info(f"Received request to extract PK data from: {pdf_path}")
    
    # 1. Convert PDF to images
    print("📄 Step 1/3: Converting PDF to images...")
    logger.debug("Step 1: Rasterization")
    images = convert_pdf_to_images(pdf_path)
    print(f"   -> Converted PDF into {len(images)} pages.")
    
    # 2. Run ColQwen2.5 filter to find the exact pages
    print("🔎 Step 2/3: Searching for Pharmacokinetic tables across all pages...")
    logger.debug("Step 2: Intra-Document Search")
    
    # Build a dynamic query to allow steering without hardcoding
    search_query = "Pharmacokinetic parameters table"
    if target_compounds:
        search_query += f" for {', '.join(target_compounds)}"
        
    target_images = get_retriever().find_top_pages(
        images, 
        top_k=10, 
        query=search_query
    )
    print(f"   -> Identified {len(target_images)} highly relevant pages.")
    
    # 2.5 Crop table regions from each selected page before VLM extraction
    print("✂️  Step 2.5: Cropping table regions from selected pages...")
    cropper = TableCropper(padding=25)
    cropped_images = cropper.crop_all(target_images)
    cropped_count = sum(1 for orig, crop in zip(target_images, cropped_images) if crop.size != orig.size)
    print(f"   -> Cropped {cropped_count}/{len(cropped_images)} pages (rest were borderless — full page sent).")
    
    # Save cropped images to a debug folder for inspection
    pdf_stem = os.path.splitext(os.path.basename(pdf_path))[0]
    debug_dir = os.path.join(os.path.dirname(pdf_path), f"{pdf_stem}_vlm_inputs")
    os.makedirs(debug_dir, exist_ok=True)
    for idx, img in enumerate(cropped_images):
        img_path = os.path.join(debug_dir, f"page_{idx + 1:02d}.png")
        img.save(img_path)
    print(f"   -> 🖼️  Saved {len(cropped_images)} VLM input images to: {debug_dir}")
    
    # 3. Extract data using SGLang with schema enforcement
    print(f"⚙️  Step 3/3: Running VLM extraction on {len(cropped_images)} cropped images concurrently...")
    logger.debug("Step 3: Targeted Extraction across multiple pages")
    
    final_document = {
        "page_metadata": {"title": None, "authors": None, "journal": None, "year": None},
        "model_classification": {"model_type": "not_applicable", "evidence_quote": None},
        "structure": None,
        "parameters": []
    }
    
    tasks = [get_extractor().extract_data(img) for img in cropped_images]
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

def main():
    parser = argparse.ArgumentParser(description="Run the PK Parameter Extraction Pipeline")
    parser.add_argument("pdf_path", type=str, help="Path to the PDF file to extract")
    parser.add_argument("--compounds", nargs="+", help="Optional: Target compounds to steer search (e.g., PFOS PFOA)")
    parser.add_argument("--output", type=str, help="Optional: Path to save the extracted JSON. Defaults to <pdf_name>.json")
    
    args = parser.parse_args()
    
    try:
        # Pre-load models before starting the extraction timer so we can see the "Cold Start" penalty
        print("\n[SYSTEM] Booting AI models into GPU memory. This is a one-time 'cold start' penalty...")
        load_start = time.time()
        get_retriever()
        get_extractor()
        load_time = time.time() - load_start
        print(f"[SYSTEM] ✅ Models successfully loaded into VRAM in {load_time:.2f} seconds.\n")

        # Now start the actual pipeline timer
        pipeline_start = time.time()
        
        # If output is not specified, name it after the PDF in the current directory
        if not args.output:
            base_name = os.path.splitext(os.path.basename(args.pdf_path))[0]
            args.output = f"{base_name}.json"
            
        result = asyncio.run(run_pipeline(args.pdf_path, args.compounds))
        
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2)
            
        extraction_time = time.time() - pipeline_start
        print(f"\n✅ Pipeline Complete!")
        print(f"   -> 🐢 Model Loading (Cold Start): {load_time:.2f} seconds")
        print(f"   -> ⚡ Actual Extraction Processing: {extraction_time:.2f} seconds")
        print(f"   -> 💾 Results saved to {args.output}")
    except Exception as e:
        print(f"\n❌ Pipeline failed: {e}")

if __name__ == "__main__":
    main()
