import sys
import os
import json
import argparse

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pk_pipeline.ingestion.pmc_fetcher import extract_doi_from_pdf, extract_title_from_pdf, resolve_paper
from pk_pipeline.ingestion.xml_parser import parse_jats_xml

def main():
    parser = argparse.ArgumentParser(description="Test XML parsing and extraction (No LLM)")
    parser.add_argument("--pdf", required=False, help="Path to PDF file")
    parser.add_argument("--doi", required=False, help="Direct DOI (bypass PDF parsing)")
    args = parser.parse_args()
    
    if not args.pdf and not args.doi:
        print("❌ Error: Must provide either --pdf or --doi", file=sys.stderr)
        sys.exit(1)
        
    title = None
    if args.doi:
        doi = args.doi
        pdf_path = None
        print(f"Testing XML Input Generation on DOI: {doi}", file=sys.stderr)
    else:
        pdf_path = args.pdf
        print(f"Testing XML Input Generation on PDF: {pdf_path}", file=sys.stderr)
        print("Resolving paper...", file=sys.stderr)
        doi = extract_doi_from_pdf(pdf_path)
        title = extract_title_from_pdf(pdf_path, doi=doi)
        
    res = resolve_paper(doi=doi, title=title, pdf_path=pdf_path)
    
    if not res.get("xml_path"):
        print("❌ Error: No XML could be found for this paper.", file=sys.stderr)
        sys.exit(1)
        
    print(f"✅ XML found at: {res['xml_path']}", file=sys.stderr)
    
    parsed_xml = parse_jats_xml(res['xml_path'], filter_narrative=True)
    kept_chunks = [c for c in parsed_xml["chunks"] if c.get("kept")]
    
    # Output directly to stdout so it can be piped or inspected
    print(json.dumps(kept_chunks, indent=2))
    
    print(f"✅ Generated {len(kept_chunks)} LLM input chunks.", file=sys.stderr)

if __name__ == "__main__":
    main()
