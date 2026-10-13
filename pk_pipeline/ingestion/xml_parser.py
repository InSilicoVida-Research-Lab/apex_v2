import os
import copy
import re
import requests
from pathlib import Path
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Tuple


# ─────────────────────────────────────────────────────────────
# PK relevance scoring — keyword tiers
# ─────────────────────────────────────────────────────────────

# Tier 1: definitive PK parameter keywords (high signal — any hit = very likely relevant)
_TIER1_KEYWORDS = [
    # Clearance / rate constants
    r"\bclearance\b", r"\bCL\b", r"\bkelim\b", r"\bkel\b", r"\bk_el\b",
    r"\bhalf[\s-]?life\b", r"\bt½\b", r"\bt_½\b", r"\brate constant\b",
    # Volumes
    r"\bvolume of distribution\b", r"\bVd\b", r"\bVss\b", r"\bVc\b",
    r"\bvolume of the\b",
    # Absorption / bioavailability
    r"\bbioavailability\b", r"\babsorption rate\b", r"\bka\b", r"\bkabs\b",
    r"\boral bioavailability\b",
    # Partition / binding
    r"\bpartition coefficient\b", r"\bplasma protein binding\b",
    r"\bfree fraction\b", r"\bfu\b", r"\bblood.to.plasma\b",
    # PK metrics
    r"\bAUC\b", r"\bCmax\b", r"\btmax\b", r"\bMRT\b",
    # Physiology (PBPK specific)
    r"\bpermeability[\s-]?area\b", r"\bPapp\b", r"\bflow rate\b",
    r"\bglomerular filtration\b", r"\bGFR\b", r"\brenal clearance\b",
    r"\bhepatic clearance\b", r"\bmetabolic clearance\b",
    r"\btissue volume\b", r"\btissue blood flow\b",
    r"\bcompartment\b",
]

# Tier 2: supporting context keywords (moderate signal — need 2+ hits)
_TIER2_KEYWORDS = [
    r"\bparameter\b", r"\bmodel\b", r"\bdose\b", r"\bplasma\b",
    r"\bconcentration\b", r"\bblood\b", r"\boral\b", r"\bintravenous\b",
    r"\bIV\b", r"\bPBPK\b", r"\bpharmacokinet\b", r"\bpharmacodyn\b",
    r"\bexponential\b", r"\bequation\b", r"\bfitted\b", r"\bestimated\b",
    r"\bobserved\b", r"\bpredicted\b", r"\bsimulat\b",
]

# Section titles that are almost never relevant — skip entirely
_SKIP_TITLES = {
    "abstract", "acknowledgment", "acknowledgements", "funding",
    "conflict of interest", "abbreviations", "author contribution",
    "data availability", "ethics", "competing interest", "appendix",
    "supplementary", "supporting information",
}

# Figure captions that strongly suggest model diagrams or parameter content
_FIGURE_DIAGRAM_KEYWORDS = [
    r"model structure", r"compartment", r"diagram", r"schematic",
    r"flowchart", r"flow chart", r"pbpk", r"physiologically",
    r"\bode\b", r"differential equation",
    r"parameter", r"scheme",
]

# Figure captions that are mostly results plots — lower priority for text dispatch
_FIGURE_PLOT_KEYWORDS = [
    r"predicted.*observed", r"observed.*predicted",
    r"concentration.*time", r"time.*concentration",
    r"plasma concentration", r"comparison of model",
    r"model.predicted",
]


def _is_diagram_figure(caption: str) -> bool:
    """Return True if a figure caption suggests a model diagram (high-value for VLM)."""
    c = caption.lower()
    return any(re.search(p, c) for p in _FIGURE_DIAGRAM_KEYWORDS)


# Section titles that are almost always relevant — always keep
_KEEP_TITLES = {
    "method", "material", "parameter", "pharmacokinetic", "pbpk",
    "model", "equation", "result", "sensitivity analysis",
    "dose", "clearance", "absorption", "distribution", "elimination",
    "estimation", "fitting", "simulation", "compartment",
}


def _pk_relevance_score(text: str) -> Tuple[int, int]:
    """
    Returns (tier1_hits, tier2_hits) — count of matching PK keywords.
    A chunk is relevant if tier1_hits >= 1 OR tier2_hits >= 3.
    """
    t1 = sum(1 for p in _TIER1_KEYWORDS if re.search(p, text, re.IGNORECASE))
    t2 = sum(1 for p in _TIER2_KEYWORDS if re.search(p, text, re.IGNORECASE))
    return t1, t2


def is_pk_relevant(text: str, title: str = "") -> bool:
    """Return True if a narrative chunk is worth sending to the LLM."""
    title_lower = title.lower()

    # Explicit skip list
    if any(skip in title_lower for skip in _SKIP_TITLES):
        return False

    # Explicit keep list (section title match)
    if any(keep in title_lower for keep in _KEEP_TITLES):
        return True

    # Score the body text
    t1, t2 = _pk_relevance_score(text)
    return t1 >= 1 or t2 >= 3


# ─────────────────────────────────────────────────────────────
# JATS XML Parser
# ─────────────────────────────────────────────────────────────

class JatsXMLParser:
    def __init__(self, xml_path: str):
        if not os.path.exists(xml_path):
            raise FileNotFoundError(f"XML file not found: {xml_path}")
        with open(xml_path, "r", encoding="utf-8") as f:
            self.soup = BeautifulSoup(f, "xml")

    def extract_metadata(self) -> Dict[str, Any]:
        """Extracts title, authors, journal, and year."""
        metadata = {
            "title":   None,
            "authors": [],
            "journal": None,
            "year":    None,
        }

        title_tag = self.soup.find("article-title")
        if title_tag:
            metadata["title"] = title_tag.get_text(strip=True)

        journal_tag = self.soup.find("journal-title")
        if journal_tag:
            metadata["journal"] = journal_tag.get_text(strip=True)

        pub_date = self.soup.find("pub-date")
        if pub_date:
            year_tag = pub_date.find("year")
            if year_tag:
                try:
                    metadata["year"] = int(year_tag.get_text(strip=True))
                except ValueError:
                    pass

        contrib_group = self.soup.find("contrib-group")
        if contrib_group:
            for contrib in contrib_group.find_all("contrib", {"contrib-type": "author"}):
                name_tag = contrib.find("name")
                if name_tag:
                    surname    = name_tag.find("surname")
                    given      = name_tag.find("given-names")
                    if surname and given:
                        metadata["authors"].append(
                            f"{given.get_text(strip=True)} {surname.get_text(strip=True)}"
                        )
                    elif surname:
                        metadata["authors"].append(surname.get_text(strip=True))

        return metadata

    def _parse_table_wrap(self, table_wrap, idx: int) -> Tuple[str, str, Any]:
        """
        Parse a JATS <table-wrap> element into:
        1. full_title: Clean title with label and caption
        2. content_str: Robust, correctly aligned Markdown preserving multi-level headers,
                        rowspans, colspans, section dividers, and all footnotes.
        3. table_evidence: Structured TableEvidence object with cells, columns, rows,
                           subject_compounds, and footnotes.
        """
        label = table_wrap.find("label")
        t_label = label.get_text(strip=True).rstrip(".") if label else f"Table {idx + 1}"
        caption = table_wrap.find("caption")
        t_caption = caption.get_text(separator=" ", strip=True) if caption else ""
        full_title = f"{t_label}: {t_caption}".strip(": ") if t_caption else t_label

        table_node = table_wrap.find("table")
        if table_node is None:
            return full_title, f"{full_title}\n\n{str(table_wrap)}", None

        # 2D Grid reconstruction tracking rowspans and colspans
        grid = {}
        curr_r = 0
        max_r, max_c = 0, 0
        thead = table_node.find("thead")
        thead_tr_count = len(thead.find_all("tr")) if thead else 0

        for tr in table_node.find_all("tr"):
            curr_c = 0
            for cell in tr.find_all(["th", "td"]):
                while (curr_r, curr_c) in grid:
                    curr_c += 1
                try:
                    rowspan = int(cell.get("rowspan", 1))
                except (ValueError, TypeError):
                    rowspan = 1
                try:
                    colspan = int(cell.get("colspan", 1))
                except (ValueError, TypeError):
                    colspan = 1
                text = re.sub(r'\s+', ' ', cell.get_text(separator=" ", strip=True))
                for dr in range(rowspan):
                    for dc in range(colspan):
                        grid[(curr_r + dr, curr_c + dc)] = text
                        if curr_r + dr > max_r:
                            max_r = curr_r + dr
                        if curr_c + dc > max_c:
                            max_c = curr_c + dc
                curr_c += colspan
            curr_r += 1

        num_rows = max(max_r + 1, curr_r)
        num_cols = max_c + 1 if num_rows > 0 else 0
        if num_cols == 0 or num_rows == 0:
            return full_title, f"{full_title}\n\n{str(table_wrap)}", None

        matrix = [["" for _ in range(num_cols)] for _ in range(num_rows)]
        for (r, c), val in grid.items():
            if r < num_rows and c < num_cols:
                matrix[r][c] = val

        # Handle headers: multi-row thead vs single header row
        if thead_tr_count > 1:
            combined_headers = []
            for c in range(num_cols):
                hdr_parts = []
                for r in range(thead_tr_count):
                    txt = matrix[r][c].strip()
                    if txt and (not hdr_parts or txt != hdr_parts[-1]):
                        hdr_parts.append(txt)
                combined_headers.append(" - ".join(hdr_parts) if hdr_parts else f"Col {c+1}")
            data_matrix = matrix[thead_tr_count:]
        else:
            combined_headers = [c.strip() or f"Col {i+1}" for i, c in enumerate(matrix[0])]
            data_matrix = matrix[1:]

        md_lines = []
        md_lines.append(full_title)
        md_lines.append("")
        md_lines.append("| " + " | ".join(combined_headers) + " |")
        md_lines.append("|" + "|".join(["---"] * num_cols) + "|")

        for row in data_matrix:
            non_empty = [x for x in row if x.strip()]
            if non_empty and all(x == non_empty[0] for x in non_empty) and len(non_empty) == num_cols:
                md_lines.append(f"| **[Section: {non_empty[0]}]** |" + "|".join([""] * (num_cols - 1)) + "|")
            else:
                md_lines.append("| " + " | ".join(row) + " |")

        # Extract all footnotes
        footnotes = []
        foot = table_wrap.find("table-wrap-foot")
        if foot:
            md_lines.append("")
            md_lines.append("Footnotes:")
            for fn in foot.find_all("fn"):
                lbl = fn.find("label")
                lbl_str = lbl.get_text(strip=True) if lbl else "*"
                fn_txt = re.sub(r'\s+', ' ', fn.get_text(separator=' ', strip=True))
                if lbl and fn_txt.startswith(lbl_str):
                    fn_txt = fn_txt[len(lbl_str):].strip()
                footnotes.append(f"[{lbl_str}] {fn_txt}")
                md_lines.append(f"- [{lbl_str}] {fn_txt}")

        content_str = "\n".join(md_lines)

        # Build structured TableEvidence object
        table_evidence = None
        try:
            from pk_pipeline.schemas import TableEvidence, TableColumn, TableRow, TableCell

            columns = []
            for c in range(num_cols):
                col_path = []
                for r in range(max(1, thead_tr_count)):
                    txt = matrix[r][c].strip()
                    if txt and (not col_path or txt != col_path[-1]):
                        col_path.append(txt)
                columns.append(TableColumn(column_id=f"c{c+1}", path=col_path or [f"Col {c+1}"], index=c))

            rows = []
            cells = []
            current_section = ""
            start_data_r = thead_tr_count if thead_tr_count > 0 else 1

            for r_idx, r in enumerate(range(start_data_r, num_rows)):
                row_vals = matrix[r]
                non_empty = [x for x in row_vals if x.strip()]
                if non_empty and all(x == non_empty[0] for x in non_empty) and len(non_empty) == num_cols:
                    current_section = non_empty[0]
                    continue

                r_path = [current_section] if current_section else []
                for c in range(min(4, num_cols)):
                    v = row_vals[c].strip()
                    if v and v not in r_path:
                        r_path.append(v)

                row_id = f"r{len(rows)+1}"
                rows.append(TableRow(row_id=row_id, path=r_path, index=len(rows)))

                for c_idx in range(num_cols):
                    cell_txt = row_vals[c_idx].strip()
                    if cell_txt:
                        col_id = f"c{c_idx+1}"
                        cell_id = f"cell_{row_id}_{col_id}"
                        num_val = None
                        m_num = re.search(r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?', cell_txt)
                        if m_num:
                            try:
                                num_val = float(m_num.group(0))
                            except ValueError:
                                pass
                        cells.append(TableCell(
                            cell_id=cell_id,
                            row_id=row_id,
                            column_id=col_id,
                            text=cell_txt,
                            numeric_value=num_val
                        ))

            full_table_text = f"{full_title} " + " ".join(" ".join(r) for r in matrix) + " " + " ".join(footnotes)
            header_and_title_text = f"{full_title} " + " ".join(" ".join(c.path) for c in columns)
            fn_text = " ".join(footnotes)

            known_compounds = ["PFOS", "PFOA", "PFHxS", "PFBS", "PFNA", "PFDA", "GenX", "HFPO-DA"]
            subject_compounds = [
                c for c in known_compounds 
                if re.search(r'\b' + re.escape(c) + r'\b', header_and_title_text)
            ]
            if not subject_compounds:
                subject_compounds = [
                    c for c in known_compounds 
                    if re.search(r'\b' + re.escape(c) + r'\b', full_table_text)
                ]

            footnote_compounds = [
                c for c in known_compounds 
                if re.search(r'\b' + re.escape(c) + r'\b', fn_text) and c not in subject_compounds
            ]

            known_species = ["Nonhuman primate", "Human", "Rat", "Mouse", "Dog", "Monkey", "Cynomolgus monkey"]
            species = [
                s for s in known_species 
                if re.search(r'\b' + re.escape(s) + r'\b', full_table_text, re.IGNORECASE)
            ]

            table_evidence = TableEvidence(
                evidence_status="success",
                needs_review=False,
                table_id=t_label,
                title=full_title,
                columns=columns,
                rows=rows,
                cells=cells,
                subject_compounds=subject_compounds,
                footnote_compounds=footnote_compounds,
                species=species,
                footnotes=footnotes
            )
        except Exception:
            pass

        return full_title, content_str, table_evidence

    def extract_chunks(self, filter_narrative: bool = True) -> List[Dict[str, Any]]:
        chunks: List[Dict[str, Any]] = []

        # 1. Tables — always keep
        for idx, table_wrap in enumerate(self.soup.find_all("table-wrap")):
            t_title, content_str, table_evidence = self._parse_table_wrap(table_wrap, idx)
            chunks.append({
                "role":           "table_xml",
                "content":        content_str,
                "title":          t_title,
                "kept":           True,
                "skip_reason":    "",
                "table_evidence": table_evidence,
            })

        # 2. Equations — always keep
        for idx, formula in enumerate(self.soup.find_all("disp-formula")):
            content = str(formula)
            chunks.append({
                "role":        "equation_xml",
                "content":     f"Equation {idx + 1}:\n{content}",
                "title":       f"Equation {idx + 1}",
                "kept":        True,
                "skip_reason": "",
            })
        # 2.5. Figures — captions as text + image URLs for visual dispatch
        #      Always kept; dispatcher decides whether to use image or caption-only
        for idx, fig in enumerate(self.soup.find_all("fig")):
            label   = fig.find("label")
            caption = fig.find("caption")
            graphic = fig.find("graphic")

            label_txt   = label.get_text(strip=True) if label else f"Figure {idx + 1}"
            caption_txt = caption.get_text(separator=" ", strip=True) if caption else ""
            href        = graphic.get("xlink:href", "") if graphic else ""

            is_diagram = _is_diagram_figure(caption_txt)

            content = f"{label_txt}:\nCaption: {caption_txt}"
            chunks.append({
                "role":        "figure_xml",
                "content":     content,
                "title":       label_txt,
                "caption":     caption_txt,
                "image_href":  href,          # filename from XML (e.g. 'nihms-xxx-f0001.jpg')
                "is_diagram":  is_diagram,    # True → fetch image + send to VLM visually
                "kept":        True,
                "skip_reason": "",
            })

        # 3. Narrative sections — leaf sections only (no child <sec> tags).
        for sec in self.soup.find_all("sec"):
            # Skip if this sec contains child sections — it will be covered by its leaves
            if sec.find("sec"):
                continue

            title_tag = sec.find("title")
            sec_title = title_tag.get_text(strip=True) if title_tag else ""
            sec_title_lower = sec_title.lower()

            # Always skip reference / bibliography sections
            if "reference" in sec_title_lower or "bibliography" in sec_title_lower:
                continue

            sec_copy = copy.copy(sec)
            for tag in sec_copy.find_all(["table-wrap", "disp-formula"]):
                tag.decompose()
            
            # Remove inline citations to save token space (e.g. "[12]" or "(Olsen et al. 2008)")
            for xref in sec_copy.find_all("xref", {"ref-type": "bibr"}):
                xref.decompose()
                
            text = sec_copy.get_text(separator=" ", strip=True)
            
            # Clean up empty brackets/parentheses left behind by citation removal
            text = re.sub(r'\(\s*\)', '', text)
            text = re.sub(r'\[\s*\]', '', text)
            text = re.sub(r'\(\s*;\s*\)', '', text) # empty lists like ( ; )
            # Fix double spaces
            text = re.sub(r'\s{2,}', ' ', text)

            if len(text) < 50:
                continue

            # Determine if we keep this section
            kept        = True
            skip_reason = ""
            if filter_narrative:
                if not is_pk_relevant(text, title=sec_title):
                    kept        = False
                    t1, t2      = _pk_relevance_score(text)
                    skip_reason = f"low relevance (tier1={t1}, tier2={t2})"
                else:
                    # Target specific sentences
                    sentences = re.split(r'(?<=[.!?]) +', text)
                    filtered_sentences = []
                    
                    tier1_regex = re.compile(r'|'.join(_TIER1_KEYWORDS), flags=re.IGNORECASE)
                    
                    for i, sentence in enumerate(sentences):
                        # Sentence must have a number and a PK keyword
                        if any(char.isdigit() for char in sentence) and tier1_regex.search(sentence):
                            # Include the previous sentence for biological context buffer
                            if i > 0 and sentences[i-1] not in filtered_sentences:
                                filtered_sentences.append(sentences[i-1].strip())
                            if sentence not in filtered_sentences:
                                filtered_sentences.append(sentence.strip())
                                
                    if not filtered_sentences:
                        kept = False
                        skip_reason = "No numerical PK sentences found"
                    else:
                        text = "\n".join(filtered_sentences)

            chunks.append({
                "role":        "narrative_xml",
                "content":     text,
                "title":       sec_title,
                "kept":        kept,
                "skip_reason": skip_reason,
            })

        return chunks


# ─────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────

def parse_jats_xml(xml_path: str, filter_narrative: bool = True) -> Dict[str, Any]:
    """
    Parse a JATS XML file into metadata + LLM-ready chunks.

    Args:
        xml_path:         Path to the JATS XML file.
        filter_narrative: If True (default), narrative sections are scored by
                          PK keyword relevance and low-scoring ones are dropped
                          before dispatch to the LLM. Tables and equations are
                          always kept regardless.

    Returns:
        {
          "metadata": {...},
          "chunks":   [only chunks where kept=True]   ← ready for LLM dispatch
          "skipped":  [chunks where kept=False]        ← dropped sections (for inspection)
        }
    """
    parser   = JatsXMLParser(xml_path)
    all_chunks = parser.extract_chunks(filter_narrative=filter_narrative)

    kept_narrative = [c for c in all_chunks if c["kept"] and c["role"] == "narrative_xml"]
    other_kept = [c for c in all_chunks if c["kept"] and c["role"] != "narrative_xml"]
    
    if kept_narrative:
        merged_text = ""
        for c in kept_narrative:
            title_header = f"[{c['title']}]\n" if c['title'] else ""
            merged_text += f"{title_header}{c['content']}\n\n"
            
        merged_chunk = {
            "role": "narrative_xml",
            "content": merged_text.strip(),
            "title": "Combined Relevant Narrative",
            "kept": True,
            "skip_reason": ""
        }
        other_kept.append(merged_chunk)
        
    skipped = [c for c in all_chunks if not c["kept"]]

    return {
        "metadata": parser.extract_metadata(),
        "chunks":   other_kept,
        "skipped":  skipped,
    }
