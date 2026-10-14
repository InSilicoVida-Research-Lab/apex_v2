import asyncio
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

sys.path.insert(0, '/home/gautam/Desktop/project/apex_v2')
from pk_pipeline.main import get_extractor
from pk_pipeline.ingestion.xml_parser import parse_jats_xml

async def main():
    print("1. Parsing XML...", flush=True)
    xml_data = parse_jats_xml('/home/gautam/Desktop/project/apex_v2/dean_pmc.xml', filter_narrative=True)
    chunks = [c for c in xml_data['chunks'] if c.get('title', '').startswith('Table 1')]
    print(f"2. Found {len(chunks)} Table 1 chunks", flush=True)
    if not chunks:
        return
    t1_chunk = chunks[0]
    print(f"3. Table 1 length: {len(t1_chunk['content'])}", flush=True)
    
    extractor = get_extractor()
    print("4. Calling extract_from_text...", flush=True)
    try:
        res = await extractor.extract_from_text(t1_chunk['content'], role='table_xml', chunk_title='Table 1.')
        print("5. Extraction finished!", flush=True)
        print("Model classification:", res.model_classification, flush=True)
        blocks = res.parameter_blocks or []
        print(f"Parameter blocks: {len(blocks)}", flush=True)
        for b in blocks:
            print(f"  Block '{b.block_name}': {len(b.parameters)} params", flush=True)
            for p in b.parameters:
                q = p.quantitative_data.value if p.quantitative_data else None
                c = p.context.compound if p.context else None
                s = p.context.species if p.context else None
                print(f"    - {p.parameter_name_original}: val={q}, compound={c}, species={s}", flush=True)
    except Exception as e:
        print(f"ERROR: {e}", flush=True)
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(main())
