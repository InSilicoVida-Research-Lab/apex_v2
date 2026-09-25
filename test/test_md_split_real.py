import re
import pymupdf4llm

md_chunks = pymupdf4llm.to_markdown("pk_pipeline/test_data/s12249-023-02680-y.pdf", page_chunks=True)
text = md_chunks[5]["text"] # Page 6

table_pattern = re.compile(r"(?:^\|.*\|$\n)+(?:^\|[\-\s:|]+\|$\n)(?:^\|.*\|$\n?)*", re.MULTILINE)

parts = []
last_end = 0
for match in table_pattern.finditer(text):
    start, end = match.span()
    if start > last_end:
        narrative = text[last_end:start].strip()
        if narrative:
            parts.append(("narrative_xml", narrative))
    table = text[start:end].strip()
    parts.append(("table_xml", table))
    last_end = end

if last_end < len(text):
    narrative = text[last_end:].strip()
    if narrative:
        parts.append(("narrative_xml", narrative))

print(f"Total parts: {len(parts)}")
for i, (role, content) in enumerate(parts):
    print(f"[{i}] {role} ({len(content)} chars)")
    print(content[:60].replace("\n", " ") + "...")
