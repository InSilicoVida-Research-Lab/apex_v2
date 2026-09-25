import re

text = """
Some narrative text here.
It has multiple lines.

| Header 1 | Header 2 |
|---|---|
| Cell 1 | Cell 2 |
| Cell 3 | Cell 4 |

Some more text after the table.
And another table:

| H1 | H2 |
|---|---|
| A | B |

Final text.
"""

# Regex to find markdown tables
table_pattern = re.compile(r"(?:(?:\|.*?)+\|\n)+(?:\|[\-:]+)+\|\n(?:(?:\|.*?)+\|\n*)+", re.MULTILINE)
# Wait, a safer table regex:
# A table starts with a line containing pipes, followed by a separator line `|---|`, followed by more pipe lines.
table_pattern = re.compile(r"(\n?^\|.*\|$\n^\|[\-\s:|]+\|$\n(?:^\|.*\|$\n?)*)", re.MULTILINE)

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

for role, content in parts:
    print(f"ROLE: {role}")
    print(f"CONTENT: {content[:50]}...")
    print("-" * 20)
