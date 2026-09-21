import os
import shutil
import sys
import argparse

# Add the project root to sys.path so we can import pk_pipeline
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pk_pipeline.ingestion.pmc_fetcher import resolve_paper, extract_doi_from_pdf, extract_title_from_pdf

def main():
    parser = argparse.ArgumentParser(description="Test PMC Fetcher and save XML")
    parser.add_argument("--pdf", type=str, help="Path to PDF file to extract DOI/Title from")
    parser.add_argument("--pmcid", type=str, help="PMC ID to fetch (e.g. PMC9324546)")
    parser.add_argument("--doi", type=str, help="DOI to fetch (e.g. 10.1371/journal.pone.0271501)")
    parser.add_argument("--title", type=str, help="Title to fetch")
    args = parser.parse_args()

    print(f"Testing PMC Fetcher...")
    
    pmcid = args.pmcid
    doi = args.doi
    title = args.title
    
    if args.pdf:
        print(f"  Extracting metadata from PDF: {args.pdf}")
        doi = extract_doi_from_pdf(args.pdf) or doi
        title = extract_title_from_pdf(args.pdf) or title
        print(f"    -> Extracted DOI: {doi}")
        print(f"    -> Extracted Title: {title}")
    elif not any([pmcid, doi, title]):
        pmcid = "PMC9324546"
        print(f"  No arguments provided, defaulting to PMCID: {pmcid}")
        
    if pmcid: print(f"  Using PMCID: {pmcid}")
    if doi: print(f"  Using DOI: {doi}")
    if title: print(f"  Using Title: {title}")
    
    # Create output directory inside the test folder
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "xml_output")
    os.makedirs(output_dir, exist_ok=True)
    
    # Run the resolver
    result = resolve_paper(doi=doi, title=title, pmcid=pmcid)
    
    print("\nResolution result:")
    for k, v in result.items():
        print(f"  {k}: {v}")
        
    xml_path = result.get("xml_path")
    if xml_path and os.path.exists(xml_path):
        dest_path = os.path.join(output_dir, os.path.basename(xml_path))
        shutil.copy2(xml_path, dest_path)
        print(f"\n✅ Successfully fetched and saved XML to: {dest_path}")
    else:
        print("\n❌ Failed to fetch XML (paper might not be in PMC Open Access subset).")

if __name__ == "__main__":
    main()
