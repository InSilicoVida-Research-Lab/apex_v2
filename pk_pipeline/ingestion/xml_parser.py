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
# PBPK Table Gating, Group Header Preprocessing & Extraction
# ─────────────────────────────────────────────────────────────

NON_VALUE_COL_NAMES = {
    "species", "type of variable", "variable", "name", "symbol",
    "source", "reference", "parameter", "tissue", "organ", "description"
}

def parse_cell_numeric(text: str, col_path: List[str]) -> Tuple[float | None, str | None, str | None]:
    """
    Only parse numeric values in actual value columns.
    Returns (numeric_value, footnote_marker, uncertainty_or_range_text).
    """
    col_str = " ".join(col_path).lower()
    if any(k in col_str for k in NON_VALUE_COL_NAMES):
        return None, None, None

    clean = (text or "").strip()
    if not clean:
        return None, None, None

    # Match scientific notation or float with optional CI/range and optional footnote letter (e.g., '5 a', '0.008 b', '0.21 (0.18, 0.25)')
    m = re.match(
        r"^([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s*([a-zA-Z\*])?(?:\s*\(([^)]+)\))?$",
        clean
    )
    if m:
        try:
            return float(m.group(1)), m.group(2), m.group(3)
        except ValueError:
            return None, None, None

    # Also handle ranges like "56.9 - 70" or "0.18 - 0.25"
    m_range = re.match(r"^([+-]?\d+(?:\.\d+)?)\s*[\-\u2013\u2014]\s*([+-]?\d+(?:\.\d+)?)", clean)
    if m_range:
        try:
            return float(m_range.group(1)), None, clean
        except ValueError:
            return None, None, None

    return None, None, None

# ─────────────────────────────────────────────────────────────

import pandas as pd

# 1. Gate out non-input tables (Sensitivity Analysis, POD/HED, Exposure intakes)
EXCLUDE_TABLE_PATTERNS = re.compile(
    r"(sensitivity\s+coefficient|normalized\s+sensitivity|morris\s+screening|efast|"
    r"point\s+of\s+departure|pod\s*hed|exposure\s+estimate|daily\s+intake\s+estimate)",
    re.IGNORECASE
)

INCLUDE_PARAM_KEYWORDS = {
    "bw", "qcc", "qc", "tmc", "kt", "vmax", "km", "k12", "k21", "ka", "kabs",
    "kfeces", "vcc", "vfilc", "qfilc", "free", "fu", "bioav", "partition",
    "blood flow", "tissue volume", "organ volume", "clearance", "clint", "raf", "hct"
}

def is_valid_pbpk_input_table(caption: str, table_text: str) -> bool:
    """Filter out sensitivity analysis and exposure output tables before LLM extraction."""
    if EXCLUDE_TABLE_PATTERNS.search(caption):
        return False
    combined_lower = f"{caption} {table_text}".lower()
    matches = sum(1 for kw in INCLUDE_PARAM_KEYWORDS if kw in combined_lower)
    return matches >= 2


# 2. Stateful row preprocessor for Group Headers & Stacked Species (fixes Riluzole & Loccisano)
GROUP_HEADER_PATTERNS = re.compile(
    r"^(blood\s+flow|volume\s+of\s+organ|tissue\s+volume|tissue:plasma|tissue:blood|"
    r"partition\s+coefficient|elimination\s+constant|fractional\s+constant|"
    r"physiological\s+parameter|biochemical\s+parameter)",
    re.IGNORECASE
)

def preprocess_table_dataframe(df: pd.DataFrame, caption: str = "", footnotes: str = "") -> str:
    """
    1. Detects full-width group headers (where value columns are empty) and prepends
       the group name + unit to subsequent rows.
    2. Detects stacked species transitions (e.g., when 'Blood flow to organ' repeats
       mid-table in Riluzole Table I, switches context from Rat to Human).
    """
    processed_rows = []
    current_group = None
    current_species_hint = None
    blood_flow_section_count = 0

    for idx, row in df.iterrows():
        cells = [str(c).strip() if pd.notna(c) else "" for c in row.values]
        if not any(cells):
            continue

        first_cell = cells[0]
        other_cells = [c for c in cells[1:] if c not in ("", "None", "nan", "-")]

        # Detect stacked species transition when 'Blood flow to organ' repeats
        if "blood flow to organ" in first_cell.lower():
            blood_flow_section_count += 1
            if blood_flow_section_count == 1 and "rat" in caption.lower() and "human" in caption.lower():
                current_species_hint = "Rat"
            elif blood_flow_section_count >= 2 and current_species_hint == "Rat":
                current_species_hint = "Human"

        # Check if row is a spanning group header (first cell populated, value cells empty)
        if first_cell and len(other_cells) == 0 and GROUP_HEADER_PATTERNS.search(first_cell):
            current_group = first_cell
            continue  # Do NOT emit group header as a data row!

        # Prepend active group header (and inherited unit) to bare organ row labels
        if current_group and first_cell and not GROUP_HEADER_PATTERNS.search(first_cell):
            cells[0] = f"{current_group} - {first_cell}"

        if current_species_hint:
            cells[0] = f"[{current_species_hint}] {cells[0]}"

        processed_rows.append(cells)

    clean_df = pd.DataFrame(processed_rows, columns=df.columns)
    md_out = f"### Table Caption: {caption}\n\n"
    try:
        md_out += clean_df.to_markdown(index=False)
    except Exception:
        # Fallback if tabulate is not installed
        col_header = "| " + " | ".join(str(c) for c in clean_df.columns) + " |"
        sep_header = "|" + "|".join(["---"] * len(clean_df.columns)) + "|"
        row_lines = ["| " + " | ".join(str(v) for v in r) + " |" for r in clean_df.values]
        md_out += "\n".join([col_header, sep_header] + row_lines)
    if footnotes:
        md_out += f"\n\n### Table Footnotes (EXTRACT CONSTANTS FROM HERE):\n{footnotes}\n"
    return md_out


# 3. JATS XML Table & Footnote Extractor (preserves <sub>, <sup>, and <table-wrap-foot>)
def extract_tables_from_pmc_xml(xml_path: str) -> list[dict]:
    with open(xml_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "xml")

    extracted_tables = []
    for tw in soup.find_all("table-wrap"):
        label = tw.find("label").get_text(strip=True) if tw.find("label") else ""
        caption_el = tw.find("caption")
        caption = f"{label}: {caption_el.get_text(' ', strip=True)}" if caption_el else label

        # Preserve footnote markers inside cells with explicit brackets so '0.008b' is clear
        for xref in tw.find_all("xref", {"ref-type": "table-fn"}):
            xref.replace_with(f"[{xref.get_text(strip=True)}]")

        # Extract all footnotes from <table-wrap-foot>
        foot_el = tw.find("table-wrap-foot")
        footnotes = foot_el.get_text("\n", strip=True) if foot_el else ""

        table_el = tw.find("table")
        if not table_el:
            continue

        try:
            from io import StringIO
            dfs = pd.read_html(StringIO(str(table_el)))
            if not dfs:
                continue
            df = dfs[0]
        except Exception:
            continue

        if not is_valid_pbpk_input_table(caption, df.to_string()):
            continue

        markdown_str = preprocess_table_dataframe(df, caption=caption, footnotes=footnotes)
        extracted_tables.append({
            "source_location": label or "XML Table",
            "caption": caption,
            "markdown": markdown_str
        })
    return extracted_tables


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

        # Preserve footnote markers inside cells with explicit brackets so '0.008b' is clear
        for xref in table_wrap.find_all("xref", {"ref-type": "table-fn"}):
            xref.replace_with(f"[{xref.get_text(strip=True)}]")

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

        current_group = None
        current_species_hint = None
        blood_flow_section_count = 0

        for row in data_matrix:
            non_empty = [x for x in row if x.strip()]
            if not non_empty:
                continue

            first_cell = row[0].strip()
            other_cells = [c.strip() for c in row[1:] if c.strip() not in ("", "None", "nan", "-")]

            # Detect stacked species transition when 'Blood flow to organ' repeats
            if "blood flow to organ" in first_cell.lower():
                blood_flow_section_count += 1
                if blood_flow_section_count == 1 and "rat" in full_title.lower() and "human" in full_title.lower():
                    current_species_hint = "Rat"
                elif blood_flow_section_count >= 2 and current_species_hint == "Rat":
                    current_species_hint = "Human"

            # Check if row is a spanning group header (first cell populated, other value cells empty)
            if first_cell and len(other_cells) == 0 and GROUP_HEADER_PATTERNS.search(first_cell):
                current_group = first_cell
                md_lines.append(f"| **[Section: {first_cell}]** |" + "|".join([""] * (num_cols - 1)) + "|")
                continue

            if non_empty and all(x == non_empty[0] for x in non_empty) and len(non_empty) == num_cols:
                current_group = non_empty[0]
                md_lines.append(f"| **[Section: {non_empty[0]}]** |" + "|".join([""] * (num_cols - 1)) + "|")
                continue

            out_row = list(row)
            if current_group and first_cell and not GROUP_HEADER_PATTERNS.search(first_cell):
                out_row[0] = f"{current_group} - {first_cell}"
            if current_species_hint:
                out_row[0] = f"[{current_species_hint}] {out_row[0]}"

            md_lines.append("| " + " | ".join(out_row) + " |")

        # Extract all footnotes
        footnotes = []
        foot = table_wrap.find("table-wrap-foot")
        if foot:
            md_lines.append("")
            md_lines.append("### Table Footnotes (EXTRACT CONSTANTS FROM HERE):")
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
                        col_p = columns[c_idx].path if c_idx < len(columns) else []
                        num_val, qualifier, unc_txt = parse_cell_numeric(cell_txt, col_p)
                        cells.append(TableCell(
                            cell_id=cell_id,
                            row_id=row_id,
                            column_id=col_id,
                            text=cell_txt,
                            numeric_value=num_val,
                            qualifier=qualifier,
                            uncertainty_text=unc_txt
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

        # 1. Tables — filtered by is_valid_pbpk_input_table
        for idx, table_wrap in enumerate(self.soup.find_all("table-wrap")):
            t_title, content_str, table_evidence = self._parse_table_wrap(table_wrap, idx)
            is_valid = is_valid_pbpk_input_table(t_title, content_str)
            chunks.append({
                "role":           "table_xml",
                "content":        content_str,
                "title":          t_title,
                "kept":           is_valid,
                "skip_reason":    "" if is_valid else "Gated out (sensitivity or exposure/output table)",
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
