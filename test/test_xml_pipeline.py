import sys
import os
import asyncio
import json
import time

import argparse

# Add parent directory to path so we can import pk_pipeline
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pk_pipeline.main import run_pipeline
from pk_pipeline.ingestion.pmc_fetcher import extract_doi_from_pdf, extract_title_from_pdf, resolve_paper
from pk_pipeline.ingestion.xml_parser import parse_jats_xml

async def main():
    parser = argparse.ArgumentParser(description="Test full XML pipeline")
    parser.add_argument("--pdf", required=True, help="Path to PDF file")
    args = parser.parse_args()
    
    pdf_path = args.pdf
    print(f"Testing XML Pipeline on: {pdf_path}", file=sys.stderr)
    
    # 1. Force paper resolution to check if XML is available
    print("Resolving paper...", file=sys.stderr)
    doi = extract_doi_from_pdf(pdf_path)
    title = extract_title_from_pdf(pdf_path, doi=doi)
    res = resolve_paper(doi=doi, title=title, pdf_path=pdf_path)
    
    if not res.get("xml_path"):
        print("❌ Error: No XML could be found for this paper. The XML pipeline cannot run.", file=sys.stderr)
        sys.exit(1)
        
    print(f"✅ XML found at: {res['xml_path']}", file=sys.stderr)
    
    # 1.5 Save debug LLM Inputs to test folder
    parsed_xml = parse_jats_xml(res['xml_path'], filter_narrative=True)
    kept_chunks = [c for c in parsed_xml["chunks"] if c.get("kept")]
    
    debug_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "llm_inputs")
    os.makedirs(debug_dir, exist_ok=True)
    
    pmcid = os.path.splitext(os.path.basename(res['xml_path']))[0]
    debug_path = os.path.join(debug_dir, f"{pmcid}_llm_inputs.json")
    
    with open(debug_path, "w", encoding="utf-8") as f:
        json.dump(kept_chunks, f, indent=2)
    print(f"💾 Saved {len(kept_chunks)} pre-processed chunks (LLM input) to: {debug_path}", file=sys.stderr)
    
    print("Booting SGLangExtractor (lazy load via run_pipeline)...", file=sys.stderr)
    
    start_time = time.time()
    
    # 2. Run the main pipeline. 
    # Because XML is available, run_pipeline will take the fast-path,
    # lazy-loading ONLY the SGLangExtractor and bypassing the visual retriever completely.
    try:
        final_document = await run_pipeline(pdf_path)
    except Exception as e:
        print(f"Pipeline failed: {e}", file=sys.stderr)
        sys.exit(1)
        
    duration = time.time() - start_time
    print(f"\n✅ Extraction complete in {duration:.2f} seconds.", file=sys.stderr)
    print("="*80, file=sys.stderr)
    
    # 3. Output the exact final JSON payload to file
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pk_pipeline", "output")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{base_name}.json")
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(final_document, f, indent=2)
        
    print(f"✅ Saved output to: {output_path}", file=sys.stderr)

if __name__ == "__main__":
    asyncio.run(main())
