def make_markdown_table(rows):
    if not rows: return ""
    md = []
    # Header
    md.append("| " + " | ".join(str(x) for x in rows[0]) + " |")
    # Separator
    md.append("|" + "|".join(["---"] * len(rows[0])) + "|")
    # Body
    for row in rows[1:]:
        md.append("| " + " | ".join(str(x) for x in row) + " |")
    return "\n".join(md)

rows = [
    ["Parameter", "Mother", "Fetus", "source"],
    ["Maternal body weight (BW; kg) and fetal weight (VFet; kg)", "56.9 - 70 (initial); 65.3 - 79.6 (increasing)", "0 - 3.8 *", "Clewell, et al 1999 ; Gentry, et al 2003"],
    ["Tissue volumes (fraction of BW or VFet)", "", "", ""]
]
print(make_markdown_table(rows))
