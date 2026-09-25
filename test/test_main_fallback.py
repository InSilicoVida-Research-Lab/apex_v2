import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from pk_pipeline.main import extract_fallback_pymupdf
import json

async def main():
    pdf_path = "pk_pipeline/test_data/s12249-023-02680-y.pdf"
    print(f"Running fallback on {pdf_path}...")
    res = await extract_fallback_pymupdf(pdf_path, {}, [])
    
    with open("output/test_fallback/s12249_main_fallback.json", "w") as f:
        json.dump(res, f, indent=2)
        
    print(f"\nDone! Extracted {len(res['parameters'])} parameters.")

if __name__ == "__main__":
    asyncio.run(main())
