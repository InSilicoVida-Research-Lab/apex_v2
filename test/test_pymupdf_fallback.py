import pymupdf4llm
import pymupdf
import sys
import os
import json
import asyncio
import time
from PIL import Image

# Add pk_pipeline to path so we can import ml_services
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from pk_pipeline.main import get_extractor

async def test_fallback_extraction(pdf_path):
    start_time = time.time()
    print(f"Testing PyMuPDF fallback logic for {pdf_path}")
    
    out_dir = "output/test_fallback"
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(os.path.join(out_dir, "images"), exist_ok=True)
    
    stem = os.path.splitext(os.path.basename(pdf_path))[0]
    
    print("1. Extracting Markdown via pymupdf4llm...")
    md_chunks = pymupdf4llm.to_markdown(pdf_path, page_chunks=True, write_images=True, image_path=os.path.join(out_dir, "images"))
    
    print("2. Opening PDF with fitz for rendering full-page screenshots...")
    pdf_doc = pymupdf.open(pdf_path)
    
    llm_payloads = []
    
    for i, chunk in enumerate(md_chunks):
        page_num = i + 1
        text = chunk.get("text", "")
        
        has_table = "|---" in text
        has_image = "![" in text or (chunk.get("images") and len(chunk["images"]) > 0)
        
        payload = {
            "page": page_num,
            "has_table": has_table,
            "has_image": has_image,
            "markdown_context": text,
            "image_path": None,
            "img_obj": None
        }
        
        if has_table or has_image:
            # Render a 300 DPI screenshot of the ENTIRE PAGE
            page = pdf_doc[i]
            pix = page.get_pixmap(matrix=pymupdf.Matrix(300/72, 300/72))
            
            img_path = os.path.join(out_dir, f"{stem}_page_{page_num}_screenshot.png")
            pix.save(img_path)
            payload["image_path"] = img_path
            
            import io
            payload["img_obj"] = Image.open(io.BytesIO(pix.tobytes()))
            
            print(f" -> Page {page_num}: Found Table/Image! Saved Markdown AND 300 DPI Screenshot.")
        else:
            print(f" -> Page {page_num}: Text only. Saved Markdown.")
            
        # Save the markdown context to a file for inspection
        md_path = os.path.join(out_dir, f"{stem}_page_{page_num}_context.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(text)
            
        llm_payloads.append(payload)
        
    print(f"\n3. Running LLM Extraction concurrently on {len(llm_payloads)} pages...")
    extractor = get_extractor()
    # Limit concurrency to 3 to prevent GPU OOM on large batches of full pages
    sem = asyncio.Semaphore(3)  
    
    async def process_page(p):
        async with sem:
            if p["has_table"] or p["has_image"]:
                # Send Image + Text
                return await extractor.extract_data(
                    p["img_obj"],
                    role="table_crop" if p["has_table"] else "figure_crop",
                    evidence_text=p["markdown_context"],
                    chunk_title=f"Page {p['page']}"
                )
            else:
                # Send Text Only
                if len(p["markdown_context"].strip()) < 50:
                    return None # Skip empty pages
                return await extractor.extract_from_text(
                    text=p["markdown_context"],
                    role="narrative_xml",
                    chunk_title=f"Page {p['page']} Narrative"
                )
                
    tasks = [process_page(p) for p in llm_payloads]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    final_document = {
        "page_metadata": {"title": None, "authors": None, "journal": None, "year": None},
        "model_classification": {"model_type": "not_applicable", "evidence_quote": None},
        "structure": None,
        "parameters": []
    }
    
    for i, res in enumerate(results):
        if isinstance(res, Exception):
            print(f"Warning: Page {i+1} failed extraction: {res}")
        elif res:
            if res.model_classification and res.model_classification.model_type != "not_applicable":
                if final_document["model_classification"]["model_type"] == "not_applicable":
                    final_document["model_classification"] = res.model_classification.model_dump()
            if res.structure and not final_document["structure"]:
                final_document["structure"] = res.structure.model_dump(by_alias=True, exclude_none=True)
            if res.parameters:
                final_document["parameters"].extend([p.model_dump() for p in res.parameters])
                
    # Save the final extracted JSON
    json_path = os.path.join(out_dir, f"{stem}_final_extracted_data.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(final_document, f, indent=2)
        
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"\n✅ Extraction Complete! Extracted {len(final_document['parameters'])} parameters.")
    print(f"Total time taken: {duration:.2f} seconds ({duration/60:.2f} minutes).")
    print(f"Full LLM output saved to: {json_path}")

if __name__ == "__main__":
    pdf_file = sys.argv[1] if len(sys.argv) > 1 else "pk_pipeline/test_data/s12249-023-02680-y.pdf"
    if not os.path.exists(pdf_file):
        print(f"File not found: {pdf_file}")
    else:
        asyncio.run(test_fallback_extraction(pdf_file))
