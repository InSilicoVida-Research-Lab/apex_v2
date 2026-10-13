import asyncio
import sys
import logging
import json
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

sys.path.insert(0, '/home/gautam/Desktop/project/apex_v2')
from pk_pipeline.main import get_extractor
from bs4 import BeautifulSoup
import re

def parse_table_xml(table_wrap):
    label = table_wrap.find('label')
    t_label = label.get_text(strip=True) if label else 'Table'
    caption = table_wrap.find('caption')
    t_caption = caption.get_text(strip=True) if caption else ''

    table = table_wrap.find('table')
    if not table:
        return f"{t_label}: {t_caption}\n{str(table_wrap)}"

    grid = {}
    curr_r = 0
    max_r, max_c = 0, 0
    thead = table.find('thead')
    thead_tr_count = len(thead.find_all('tr')) if thead else 0

    for tr in table.find_all('tr'):
        curr_c = 0
        for cell in tr.find_all(['th', 'td']):
            while (curr_r, curr_c) in grid:
                curr_c += 1
            try: rowspan = int(cell.get('rowspan', 1))
            except: rowspan = 1
            try: colspan = int(cell.get('colspan', 1))
            except: colspan = 1
            text = re.sub(r'\s+', ' ', cell.get_text(separator=' ', strip=True))
            for dr in range(rowspan):
                for dc in range(colspan):
                    grid[(curr_r + dr, curr_c + dc)] = text
                    if curr_r + dr > max_r: max_r = curr_r + dr
                    if curr_c + dc > max_c: max_c = curr_c + dc
            curr_c += colspan
        curr_r += 1

    num_rows = max(max_r + 1, curr_r)
    num_cols = max_c + 1
    matrix = [['' for _ in range(num_cols)] for _ in range(num_rows)]
    for (r, c), val in grid.items():
        matrix[r][c] = val

    if thead_tr_count > 1:
        combined_headers = []
        for c in range(num_cols):
            hdr_parts = []
            for r in range(thead_tr_count):
                txt = matrix[r][c].strip()
                if txt and (not hdr_parts or txt != hdr_parts[-1]):
                    hdr_parts.append(txt)
            combined_headers.append(' - '.join(hdr_parts) if hdr_parts else f'Col {c+1}')
        data_matrix = matrix[thead_tr_count:]
    else:
        combined_headers = matrix[0] if matrix else []
        data_matrix = matrix[1:] if matrix else []

    md_lines = []
    full_title = f"{t_label}: {t_caption}".strip(': ')
    md_lines.append(full_title)
    md_lines.append('')
    md_lines.append('| ' + ' | '.join(combined_headers) + ' |')
    md_lines.append('|' + '|'.join(['---'] * num_cols) + '|')

    for row in data_matrix:
        non_empty = [x for x in row if x.strip()]
        if non_empty and all(x == non_empty[0] for x in non_empty) and len(non_empty) == num_cols:
            md_lines.append(f'| **[Section: {non_empty[0]}]** |' + '|'.join([''] * (num_cols - 1)) + '|')
        else:
            md_lines.append('| ' + ' | '.join(row) + ' |')

    foot = table_wrap.find('table-wrap-foot')
    if foot:
        md_lines.append('')
        md_lines.append('Footnotes:')
        for fn in foot.find_all('fn'):
            lbl = fn.find('label')
            lbl_str = lbl.get_text(strip=True) if lbl else '*'
            fn_txt = re.sub(r'\s+', ' ', fn.get_text(separator=' ', strip=True))
            if lbl and fn_txt.startswith(lbl_str):
                fn_txt = fn_txt[len(lbl_str):].strip()
            md_lines.append(f'- [{lbl_str}] {fn_txt}')

    return '\n'.join(md_lines)

async def main():
    with open('dean_pmc.xml') as f:
        soup = BeautifulSoup(f.read(), 'xml')
    t1_wrap = soup.find('table-wrap', id='kfaf087-T1')
    t1_md = parse_table_xml(t1_wrap)
    print("Formatted Table 1 Markdown:")
    print(t1_md[:400] + "...\n")

    extractor = get_extractor()
    print("Sending clean Table 1 to SGLang extractor...")
    t0 = time.time()
    res = await extractor.extract_from_text(t1_md, role='table_xml', chunk_title='Table 1.')
    print(f"Extraction completed in {time.time() - t0:.2f}s!")
    print(f"Model classification: {res.model_classification}")
    blocks = res.parameter_blocks or []
    print(f"Parameter blocks: {len(blocks)}")
    total_params = 0
    for b in blocks:
        print(f"\nBlock: {b.block_name} (implied compound={b.implied_compound}, implied species={b.implied_species})")
        for p in b.parameters:
            total_params += 1
            q = p.quantitative_data.value if p.quantitative_data else None
            c = p.context.compound if p.context else None
            s = p.context.species if p.context else None
            print(f"  [{c} | {s}] {p.parameter_name_original} ({p.symbol_original}) = {q} {p.quantitative_data.unit_original if p.quantitative_data else ''}")
    print(f"\nTotal parameters: {total_params}")

if __name__ == '__main__':
    asyncio.run(main())
