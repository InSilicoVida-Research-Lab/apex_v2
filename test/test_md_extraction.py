import asyncio
import pymupdf4llm
from pk_pipeline.ml_services import get_extractor
from pk_pipeline.schemas import ExtractionRequest
import json

async def main():
    print("Generating markdown...")
    md = pymupdf4llm.to_markdown('/home/gautam/Desktop/project/apex_v2/pk_pipeline/test_data/s12249-023-02680-y.pdf', pages=[5,6,7,8])
    print("Extracting...")
    extractor = get_extractor()
    res = await extractor.extract_from_text(md, role="table_xml", chunk_title="Test Table Markdown")
    
    # Dump to json
    print(f"Extracted {len(res.parameters)} parameters")
    # count how many human/rat
    human = sum(1 for p in res.parameters if p.biological_context.subject_species and "human" in p.biological_context.subject_species.lower())
    rat = sum(1 for p in res.parameters if p.biological_context.subject_species and "rat" in p.biological_context.subject_species.lower())
    print(f"Human: {human}, Rat: {rat}")

asyncio.run(main())
