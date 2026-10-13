import asyncio
import sys
import logging
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

sys.path.insert(0, '/home/gautam/Desktop/project/apex_v2')
from pk_pipeline.main import get_extractor
from pk_pipeline.ingestion.xml_parser import parse_jats_xml

async def test():
    print("1. Parsing dean_pmc.xml...")
    xml_data = parse_jats_xml('dean_pmc.xml')
    t1_chunk = next(c for c in xml_data['chunks'] if 'Table 1' in c.get('title', ''))
    print(f"2. Found Table 1: title='{t1_chunk['title']}', evidence={bool(t1_chunk.get('table_evidence'))}")
    te = t1_chunk.get('table_evidence')
    if te:
        print(f"   Subject compounds: {te.subject_compounds}")
        print(f"   Species: {te.species}")
        print(f"   Columns: {[c.path for c in te.columns]}")

    extractor = get_extractor()
    print("3. Calling extract_from_text with table_evidence...")
    t0 = time.time()
    res = await extractor.extract_from_text(
        t1_chunk['content'],
        role=t1_chunk['role'],
        chunk_title=t1_chunk['title'],
        table_evidence=te
    )
    print(f"4. Extraction finished in {time.time() - t0:.2f}s!")
    print(f"Model classification: {res.model_classification}")
    blocks = res.parameter_blocks or []
    print(f"Parameter blocks: {len(blocks)}")
    total_params = 0
    for b in blocks:
        print(f"\nBlock '{b.block_name}':")
        for p in b.parameters:
            total_params += 1
            q = p.quantitative_data.value if p.quantitative_data else None
            c = p.context.compound if p.context else None
            s = p.context.species if p.context else None
            tbl = p.provenance.source_table if p.provenance else None
            print(f"  [{tbl}] [{c} | {s}] {p.parameter_name_original} ({p.symbol_original}) = {q}")
    print(f"\nTotal Table 1 parameters extracted: {total_params}")

if __name__ == '__main__':
    asyncio.run(test())
