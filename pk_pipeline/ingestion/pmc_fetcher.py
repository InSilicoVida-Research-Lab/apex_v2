"""
ingestion/pmc_fetcher.py — Multi-source paper resolver.

Resolution chain (in order):
  0. Auto-detect sibling local XML    → zero-network fast-path
  1. Explicit PMCID                   → NCBI PMC OA JATS XML
  2. DOI → NCBI PMC OA               → JATS XML fast-path
  3. DOI/Title → Europe PMC           → JATS XML fast-path  [NEW]
  4. DOI/Title → BioRxiv / medRxiv   → preprint PDF         [NEW]
  5. DOI → Unpaywall                  → free legal PDF
  6. DOI/Title → Semantic Scholar     → open-access PDF
  7. Caller falls back to local PDF OCR
"""

import os
import re
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

NCBI_ESEARCH    = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PMC_OA_FETCH    = "https://www.ncbi.nlm.nih.gov/pmc/oai/oai.cgi"
UNPAYWALL_API   = "https://api.unpaywall.org/v2/{doi}"
SS_SEARCH_API   = "https://api.semanticscholar.org/graph/v1/paper/search"
EUROPE_PMC_API  = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
EUROPE_PMC_XML  = "https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"
BIORXIV_API     = "https://api.biorxiv.org/details/{server}/{doi}/na/json"
CROSSREF_API    = "https://api.crossref.org/works/{doi}"
CACHE_DIR       = os.path.join(os.path.expanduser("~"), ".cache", "pk_pbpk_extractor")
UNPAYWALL_EMAIL = "pbpk-extractor@research.local"   # required by Unpaywall ToS


# ─────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────

def _normalize_doi(doi: str) -> str:
    return re.sub(r"^https?://doi\.org/", "", doi.strip())


def _esearch_pmc(params: dict) -> str | None:
    try:
        r = requests.get(NCBI_ESEARCH, params=params, timeout=15)
        r.raise_for_status()
        ids = r.json().get("esearchresult", {}).get("idlist", [])
        return f"PMC{ids[0]}" if ids else None
    except Exception as e:
        print(f"    [PMC] E-search error: {e}")
        return None


# ─────────────────────────────────────────────────────────────
# PDF scanning helpers — DOI extraction
# ─────────────────────────────────────────────────────────────

_DOI_PATTERN = r"\b(10\.\d{4,9}/[-._;()/:A-Z0-9]+)\b"


def _extract_doi_from_text(text: str) -> str | None:
    m = re.search(_DOI_PATTERN, text, re.IGNORECASE)
    if m:
        return m.group(1).rstrip(".")
    return None


def _crossref_doi_from_title(title: str) -> str | None:
    """Last-resort: ask CrossRef to resolve a DOI from a title string."""
    try:
        r = requests.get(
            "https://api.crossref.org/works",
            params={"query.title": title, "rows": 1, "select": "DOI,title"},
            timeout=12,
        )
        r.raise_for_status()
        items = r.json().get("message", {}).get("items", [])
        if not items:
            return None
        doi = items[0].get("DOI")
        if doi:
            print(f"  [CrossRef] Recovered DOI via title: {doi}")
            return doi
    except Exception as e:
        print(f"  [CrossRef] Title→DOI lookup failed: {e}")
    return None


def extract_doi_from_pdf(pdf_path: str) -> str | None:
    """Try fitz → pypdf → pdfminer byte scan, then CrossRef title recovery."""

    # 1. fitz (PyMuPDF)
    try:
        import fitz
        doc = fitz.open(pdf_path)
        text = "".join(page.get_text() for page in doc[:3])
        doi = _extract_doi_from_text(text)
        if doi:
            return doi
    except Exception:
        pass

    # 2. pypdf
    try:
        import pypdf
        with open(pdf_path, "rb") as f:
            reader = pypdf.PdfReader(f)
            text = "".join(
                reader.pages[i].extract_text() or ""
                for i in range(min(3, len(reader.pages)))
            )
        doi = _extract_doi_from_text(text)
        if doi:
            return doi
    except Exception:
        pass

    # 3. pdfminer.six (most robust text extraction)
    try:
        from pdfminer.high_level import extract_text as pdfminer_extract
        text = pdfminer_extract(pdf_path, maxpages=3)
        doi = _extract_doi_from_text(text)
        if doi:
            return doi
    except Exception:
        pass

    # 4. Raw byte scan (last resort for embedded DOIs in PDF metadata)
    try:
        with open(pdf_path, "rb") as f:
            raw = f.read(40000)
        text = raw.decode("utf-8", errors="ignore")
        doi = _extract_doi_from_text(text)
        if doi:
            return doi
    except Exception:
        pass

    return None


# ─────────────────────────────────────────────────────────────
# PDF scanning helpers — Title extraction
# ─────────────────────────────────────────────────────────────

def _crossref_title_from_doi(doi: str) -> str | None:
    """Given a clean DOI, ask CrossRef for the canonical title.
    
    Uses the 'polite pool' via mailto param for better rate limits.
    """
    doi = _normalize_doi(doi)
    try:
        # CrossRef /works/{doi} accepts slashes directly in the path
        r = requests.get(
            f"https://api.crossref.org/works/{doi}",
            params={"mailto": UNPAYWALL_EMAIL},
            timeout=12,
        )
        if r.status_code == 404:
            print(f"  [CrossRef] DOI {doi} not found.")
            return None
        r.raise_for_status()
        titles = r.json().get("message", {}).get("title", [])
        if titles:
            t = titles[0].strip()
            print(f"  [CrossRef] Canonical title for {doi}: {t[:80]}")
            return t
    except Exception as e:
        print(f"  [CrossRef] DOI→title lookup failed: {e}")
    return None


def extract_title_from_pdf(pdf_path: str, doi: str | None = None) -> str | None:
    """Try PDF metadata (pypdf → fitz), then CrossRef (if DOI known), then pdfminer heuristic."""

    # 1. pypdf metadata
    try:
        import pypdf
        with open(pdf_path, "rb") as f:
            reader = pypdf.PdfReader(f)
            meta = reader.metadata
            if meta and getattr(meta, "title", None):
                t = meta.title.strip()
                if len(t) > 10 and "untitled" not in t.lower():
                    return t
    except Exception:
        pass

    # 2. fitz metadata
    try:
        import fitz
        doc = fitz.open(pdf_path)
        meta = doc.metadata
        if meta and meta.get("title"):
            t = meta["title"].strip()
            if len(t) > 10 and "untitled" not in t.lower():
                return t
    except Exception:
        pass

    # 3. CrossRef via DOI — most reliable canonical title when DOI is known
    if doi:
        t = _crossref_title_from_doi(doi)
        if t:
            return t

    # 4. pdfminer first-page heuristic — last resort
    #    Skip lines that look like author lists (many commas + digits = affiliations)
    try:
        from pdfminer.high_level import extract_text as pdfminer_extract
        text = pdfminer_extract(pdf_path, maxpages=1) or ""
        lines = [l.strip() for l in text.splitlines() if len(l.strip()) > 20]
        for line in lines[:8]:
            # Heuristic: author lines have many digits (affiliations) or >3 commas
            digit_ratio = sum(c.isdigit() for c in line) / max(len(line), 1)
            if digit_ratio > 0.05 or line.count(",") > 3:
                continue
            if 15 < len(line) < 300:
                print(f"  [pdfminer] Heuristic title: {line[:80]}")
                return line
    except Exception:
        pass

    return None


# ─────────────────────────────────────────────────────────────
# Source 0 — Local sibling XML auto-detect
# ─────────────────────────────────────────────────────────────

def try_local_xml(pdf_path: str) -> str | None:
    """Look for a JATS XML file sitting next to the PDF (same stem, .xml extension).

    For example: 'Loccisano 2013.pdf' → 'Loccisano 2013.xml'
    Also checks an xml_output/ subfolder in the same directory.
    """
    stem, _ = os.path.splitext(pdf_path)
    candidates = [
        stem + ".xml",
        os.path.join(os.path.dirname(pdf_path), "xml_output", os.path.basename(stem) + ".xml"),
    ]

    for candidate in candidates:
        if os.path.exists(candidate):
            # Minimal JATS sanity check
            try:
                with open(candidate, "r", encoding="utf-8", errors="ignore") as f:
                    head = f.read(2000)
                if "<article" in head or "<pmc-articleset" in head:
                    print(f"  [Local XML] Found sibling XML: {candidate}")
                    return candidate
            except Exception:
                pass

    return None


# ─────────────────────────────────────────────────────────────
# Source 1 — NCBI PMC Open Access
# ─────────────────────────────────────────────────────────────

def doi_to_pmcid(doi: str) -> str | None:
    doi = _normalize_doi(doi)
    print(f"  [PMC] Searching by DOI: {doi}")
    pmcid = _esearch_pmc({"db": "pmc", "term": f"{doi}[DOI]", "retmode": "json", "retmax": 1})
    print(f"  [PMC] DOI → {pmcid or 'not found'}")
    return pmcid


def title_to_pmcid(title: str) -> str | None:
    clean = re.sub(r"[^a-zA-Z0-9 ]", " ", title)
    print(f"  [PMC] Searching by Title: \"{title[:60]}...\"")
    pmcid = _esearch_pmc({"db": "pmc", "term": f"{clean}[Title]", "retmode": "json", "retmax": 1})
    print(f"  [PMC] Title → {pmcid or 'not found'}")
    return pmcid


def fetch_pmc_xml(pmcid: str) -> str | None:
    out_dir = os.path.join(CACHE_DIR, "xml")
    os.makedirs(out_dir, exist_ok=True)
    xml_path = os.path.join(out_dir, f"{pmcid}.xml")

    if os.path.exists(xml_path):
        print(f"  [PMC] Cached XML: {xml_path}")
        return xml_path

    print(f"  [PMC] Downloading XML for {pmcid}...")
    params = {
        "verb": "GetRecord",
        "identifier": f"oai:pubmedcentral.nih.gov:{pmcid.replace('PMC', '')}",
        "metadataPrefix": "pmc",
    }
    try:
        r = requests.get(PMC_OA_FETCH, params=params, timeout=30)
        r.raise_for_status()
        if "<error" in r.text and ("idDoesNotExist" in r.text or "noRecordsMatch" in r.text):
            print(f"  [PMC] {pmcid} not in OA subset.")
            return None
        if len(r.text) < 500:
            print(f"  [PMC] Response too short.")
            return None
        with open(xml_path, "w", encoding="utf-8") as f:
            f.write(r.text)
        print(f"  [PMC] XML saved: {xml_path}")
        time.sleep(0.35)
        return xml_path
    except Exception as e:
        print(f"  [PMC] Download failed: {e}")
        return None


def try_pmc(doi: str = None, title: str = None) -> str | None:
    """Returns path to downloaded NCBI PMC XML, or None."""
    if not doi and not title:
        return None

    found_pmcid = None

    # Strictly prioritize DOI if available
    if doi:
        found_pmcid = doi_to_pmcid(doi)
    elif title and len(title) > 10 and any(c.isalpha() for c in title):
        found_pmcid = title_to_pmcid(title)

    if found_pmcid:
        return fetch_pmc_xml(found_pmcid)
    return None


# ─────────────────────────────────────────────────────────────
# Source 3 — Europe PMC (NEW)
# ─────────────────────────────────────────────────────────────

def try_europe_pmc(doi: str = None, title: str = None) -> str | None:
    """Search Europe PMC and download JATS full-text XML.

    Europe PMC covers European-funded research often absent from NCBI OA.
    Returns path to downloaded XML, or None.
    """
    print(f"\n  [Europe PMC] Searching...")
    query = None
    if doi:
        query = f"DOI:{_normalize_doi(doi)}"
    elif title:
        query = f"TITLE:\"{title}\""
    else:
        return None

    try:
        r = requests.get(
            EUROPE_PMC_API,
            params={
                "query": query,
                "resultType": "core",
                "format": "json",
                "pageSize": 1,
            },
            timeout=15,
        )
        r.raise_for_status()
        results = r.json().get("resultList", {}).get("result", [])
        if not results:
            print(f"  [Europe PMC] No results.")
            return None

        hit = results[0]
        pmcid = hit.get("pmcid")
        has_full_text = hit.get("hasTextMinedTerms") == "Y" or hit.get("inEPMC") == "Y"

        if not pmcid:
            print(f"  [Europe PMC] Result has no PMCID — cannot fetch XML.")
            return None

        print(f"  [Europe PMC] Found: {pmcid} | full text: {has_full_text}")

        # Download full-text XML
        out_dir = os.path.join(CACHE_DIR, "xml")
        os.makedirs(out_dir, exist_ok=True)
        xml_path = os.path.join(out_dir, f"{pmcid}_europepmc.xml")

        if os.path.exists(xml_path):
            print(f"  [Europe PMC] Cached XML: {xml_path}")
            return xml_path

        xml_url = EUROPE_PMC_XML.format(pmcid=pmcid)
        xml_r = requests.get(xml_url, timeout=30)
        if xml_r.status_code == 404:
            print(f"  [Europe PMC] Full-text XML not available for {pmcid}.")
            return None
        xml_r.raise_for_status()

        content = xml_r.text
        if len(content) < 500 or "<article" not in content:
            print(f"  [Europe PMC] Response does not look like JATS XML.")
            return None

        with open(xml_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  [Europe PMC] XML saved: {xml_path}")
        time.sleep(0.35)
        return xml_path

    except Exception as e:
        print(f"  [Europe PMC] Error: {e}")
        return None


# ─────────────────────────────────────────────────────────────
# Source 4 — BioRxiv / medRxiv (NEW)
# ─────────────────────────────────────────────────────────────

def try_biorxiv(doi: str = None, title: str = None) -> str | None:
    """Try to download the PDF from bioRxiv or medRxiv.

    Uses the bioRxiv content API. Falls back to medRxiv if not found on bioRxiv.
    Returns path to downloaded PDF, or None.
    """
    if not doi:
        print(f"\n  [BioRxiv] Skipped — no DOI available.")
        return None

    doi_clean = _normalize_doi(doi)
    print(f"\n  [BioRxiv/medRxiv] Searching for DOI: {doi_clean}")

    for server in ("biorxiv", "medrxiv"):
        try:
            url = BIORXIV_API.format(server=server, doi=doi_clean)
            r = requests.get(url, timeout=15)
            r.raise_for_status()
            data = r.json()
            collection = data.get("collection", [])
            if not collection:
                print(f"  [{server}] Not found.")
                continue

            # Take the most recent version
            latest = collection[-1]
            doi_str = latest.get("doi", doi_clean)
            version = latest.get("version", "1")
            print(f"  [{server}] Found: version {version}, DOI: {doi_str}")

            # Build PDF URL
            pdf_url = f"https://www.{server}.org/content/{doi_str}v{version}.full.pdf"
            file_stem = doi_clean.replace("/", "_")
            pdf_path = _download_pdf(pdf_url, file_stem, source=server)
            if pdf_path:
                return pdf_path

        except Exception as e:
            print(f"  [{server}] Error: {e}")

    return None


# ─────────────────────────────────────────────────────────────
# Source 5 — Unpaywall (free legal PDF by DOI)
# ─────────────────────────────────────────────────────────────

def try_unpaywall(doi: str) -> str | None:
    """Returns path to downloaded PDF, or None."""
    if not doi:
        return None

    doi = _normalize_doi(doi)
    print(f"\n  [Unpaywall] Looking up DOI: {doi}")

    try:
        url = UNPAYWALL_API.format(doi=doi)
        r = requests.get(url, params={"email": UNPAYWALL_EMAIL}, timeout=15)
        if r.status_code == 404:
            print(f"  [Unpaywall] DOI not found in Unpaywall.")
            return None
        r.raise_for_status()
        data = r.json()

        oa_loc = data.get("best_oa_location")
        if not oa_loc:
            print(f"  [Unpaywall] No open-access version found.")
            return None

        pdf_url = oa_loc.get("url_for_pdf") or oa_loc.get("url")
        host    = oa_loc.get("host_type", "unknown")
        version = oa_loc.get("version", "unknown")
        print(f"  [Unpaywall] Found OA version — host: {host}, version: {version}")
        print(f"  [Unpaywall] PDF URL: {pdf_url}")

        if not pdf_url:
            print(f"  [Unpaywall] No direct PDF URL available.")
            return None

        return _download_pdf(pdf_url, doi.replace("/", "_"), source="unpaywall")

    except Exception as e:
        print(f"  [Unpaywall] Error: {e}")
        return None


# ─────────────────────────────────────────────────────────────
# Source 6 — Semantic Scholar (open-access PDF by title/DOI)
# ─────────────────────────────────────────────────────────────

def try_semantic_scholar(doi: str = None, title: str = None) -> str | None:
    """Returns path to downloaded PDF, or None."""
    print(f"\n  [Semantic Scholar] Searching...")

    try:
        if doi:
            doi = _normalize_doi(doi)
            url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}"
            r = requests.get(url, params={"fields": "title,openAccessPdf,externalIds"}, timeout=15)
        elif title:
            r = requests.get(SS_SEARCH_API, params={
                "query": title,
                "fields": "title,openAccessPdf,externalIds",
                "limit": 1
            }, timeout=15)
            data = r.json()
            papers = data.get("data", [])
            if not papers:
                print(f"  [Semantic Scholar] No results for title search.")
                return None
            r = type("R", (), {"json": lambda self: papers[0], "raise_for_status": lambda self: None})()
        else:
            return None

        r.raise_for_status() if hasattr(r, "status_code") else None
        paper = r.json()

        oa_pdf = paper.get("openAccessPdf")
        if not oa_pdf or not oa_pdf.get("url"):
            print(f"  [Semantic Scholar] No open-access PDF available.")
            return None

        pdf_url = oa_pdf["url"]
        paper_id = doi.replace("/", "_") if doi else re.sub(r"[^a-zA-Z0-9]", "_", (title or "paper"))[:40]
        print(f"  [Semantic Scholar] Found PDF: {pdf_url}")
        return _download_pdf(pdf_url, paper_id, source="semanticscholar")

    except Exception as e:
        print(f"  [Semantic Scholar] Error: {e}")
        return None


# ─────────────────────────────────────────────────────────────
# PDF downloader helper
# ─────────────────────────────────────────────────────────────

def _download_pdf(url: str, file_stem: str, source: str = "web") -> str | None:
    out_dir = os.path.join(CACHE_DIR, "pdfs")
    os.makedirs(out_dir, exist_ok=True)
    pdf_path = os.path.join(out_dir, f"{file_stem}_{source}.pdf")

    if os.path.exists(pdf_path):
        print(f"  Cached PDF: {pdf_path}")
        return pdf_path

    if source == "pmc_supp" or "pmc.ncbi" in url:
        try:
            from playwright.sync_api import sync_playwright
            print(f"  [PMC] Downloading via playwright to bypass PoW: {url}")
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")
                page = context.new_page()
                try:
                    with page.expect_download(timeout=30000) as download_info:
                        page.goto(url)
                    download = download_info.value
                    download.save_as(pdf_path)
                    size_kb = os.path.getsize(pdf_path) / 1024
                    print(f"  Downloaded PDF ({size_kb:.1f} KB): {pdf_path}")
                    return pdf_path
                except Exception as e:
                    print(f"  Playwright download failed: {e}")
                    return None
                finally:
                    browser.close()
        except Exception as e:
            print(f"  Failed to use playwright: {e}")
            return None

    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; PBPK-Extractor/1.0; research use)"}
        r = requests.get(url, headers=headers, timeout=60, stream=True)
        r.raise_for_status()
        content_type = r.headers.get("content-type", "")
        if "pdf" not in content_type and "octet-stream" not in content_type:
            print(f"  Warning: unexpected content-type '{content_type}'. Saving anyway.")
        with open(pdf_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        size_kb = os.path.getsize(pdf_path) / 1024
        print(f"  Downloaded PDF ({size_kb:.1f} KB): {pdf_path}")
        return pdf_path
    except Exception as e:
        print(f"  PDF download failed: {e}")
        return None


# ─────────────────────────────────────────────────────────────
# PMC figure image downloader
# ─────────────────────────────────────────────────────────────

def fetch_figure_image(pmcid: str, image_href: str) -> str | None:
    """Download a single figure image from PMC and return its local path.

    PMC serves article assets at:
      https://www.ncbi.nlm.nih.gov/pmc/articles/{PMCID}/bin/{filename}

    Args:
        pmcid:      e.g. 'PMC3502013'
        image_href: filename from the XML <graphic xlink:href="...">
                    e.g. 'nihms-403084-f0001.jpg'

    Returns:
        Local path to the cached image, or None on failure.
    """
    if not pmcid or not image_href:
        return None

    if not pmcid.startswith("PMC"):
        pmcid = f"PMC{pmcid}"

    # Strip any path prefix in the href (some XMLs embed a relative path)
    filename = os.path.basename(image_href)
    if not any(filename.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".gif", ".tif", ".tiff"]):
        filename = filename + ".jpg"   # fallback

    out_dir = os.path.join(CACHE_DIR, "figures", pmcid)
    os.makedirs(out_dir, exist_ok=True)
    local_path = os.path.join(out_dir, filename)

    if os.path.exists(local_path):
        return local_path

    url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/bin/{filename}"
    print(f"  [PMC Figures] Downloading: {url}")
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; PBPK-Extractor/1.0; research use)"}
        r = requests.get(url, headers=headers, timeout=30, stream=True)
        if r.status_code == 404:
            print(f"  [PMC Figures] Not found: {filename}")
            return None
        r.raise_for_status()
        with open(local_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        size_kb = os.path.getsize(local_path) / 1024
        print(f"  [PMC Figures] Saved ({size_kb:.1f} KB): {local_path}")
        return local_path
    except Exception as e:
        print(f"  [PMC Figures] Download failed: {e}")
        return None


def fetch_all_figures(pmcid: str, figure_chunks: list) -> list:
    """Download all figure images referenced in figure_chunks and attach local paths.

    Returns the same list with 'image_path' field populated where successful.
    """
    updated = []
    for chunk in figure_chunks:
        href = chunk.get("image_href", "")
        if href:
            local = fetch_figure_image(pmcid, href)
            chunk = dict(chunk)   # don't mutate original
            chunk["image_path"] = local
        else:
            chunk = dict(chunk)
            chunk["image_path"] = None
        updated.append(chunk)
    return updated


# ─────────────────────────────────────────────────────────────
# Supplementary PDF scraper
# ─────────────────────────────────────────────────────────────

def fetch_supplementary_pdfs(pmcid: str) -> list[str]:
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin
    print(f"\n  [PMC Scraper] Searching for supplementary files for {pmcid}...")

    if not pmcid.startswith("PMC"):
        pmcid = f"PMC{pmcid}"

    url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
    except Exception as e:
        print(f"  [PMC Scraper] Failed to fetch PMC page: {e}")
        return []

    soup = BeautifulSoup(r.text, 'html.parser')
    downloaded_pdfs = []

    for a in soup.find_all('a', href=True):
        href = a.get('href', '')
        if '/bin/' in href or 'supp' in href.lower() or href.lower().endswith('.pdf'):
            if not (href.lower().endswith('.pdf') or '/bin/' in href):
                continue
            full_url = urljoin(r.url, href)
            file_name = href.split('/')[-1]
            if not file_name.endswith('.pdf'):
                file_name += '.pdf'
            if 'supp' not in href.lower() and 'bin' not in href:
                continue
            print(f"  [PMC Scraper] Found supplementary file: {full_url}")
            out_path = _download_pdf(full_url, f"{pmcid}_{file_name.replace('.pdf', '')}", source="pmc_supp")
            if out_path and out_path not in downloaded_pdfs:
                downloaded_pdfs.append(out_path)

    return downloaded_pdfs


# ─────────────────────────────────────────────────────────────
# Main public resolver
# ─────────────────────────────────────────────────────────────

def resolve_paper(doi: str = None, title: str = None, pmcid: str = None, pdf_path: str = None) -> dict:
    """
    Tries all available free sources in order.

    Returns a dict:
      {
        "xml_path":     str | None,   # path to JATS XML (fast-path)
        "pdf_path":     str | None,   # path to downloaded free PDF (OCR path)
        "source":       str | None,   # see SOURCE_* constants below
        "source_type":  str           # "published" | "preprint"
      }

    Sources:
      local_xml        — sibling .xml file detected next to the PDF
      pmc_xml          — NCBI PMC Open Access JATS XML
      europe_pmc       — Europe PMC JATS XML
      biorxiv          — bioRxiv preprint PDF
      medrxiv          — medRxiv preprint PDF
      unpaywall        — Unpaywall free legal PDF
      semantic_scholar — Semantic Scholar open-access PDF
    """
    result = {
        "xml_path":    None,
        "pdf_path":    None,
        "source":      None,
        "source_type": "published",
    }

    # ── 0. Local sibling XML ─────────────────────────────
    if pdf_path:
        print("\n  ── Source 0: Local sibling XML ────────────────")
        xml = try_local_xml(pdf_path)
        if xml:
            result.update({"xml_path": xml, "source": "local_xml"})
            return result
        print("  [Local XML] No sibling XML found.")

    # ── 1. Explicit PMCID ────────────────────────────────
    if pmcid:
        if not pmcid.startswith("PMC"):
            pmcid = f"PMC{pmcid}"
        xml = fetch_pmc_xml(pmcid)
        if xml:
            result.update({"xml_path": xml, "source": "pmc_xml"})
            return result

    # ── 2. NCBI PMC via DOI/Title ────────────────────────
    print("\n  ── Source 1: NCBI PMC Open Access ─────────────")
    xml = try_pmc(doi=doi, title=title)
    if xml:
        result.update({"xml_path": xml, "source": "pmc_xml"})
        return result
    print("  [PMC] Not available in OA subset.")

    # ── 3. Europe PMC ─────────────────────────────────────
    print("\n  ── Source 2: Europe PMC ───────────────────────")
    xml = try_europe_pmc(doi=doi, title=title)
    if xml:
        result.update({"xml_path": xml, "source": "europe_pmc"})
        return result
    print("  [Europe PMC] Not available.")

    # ── 4. BioRxiv / medRxiv ─────────────────────────────
    print("\n  ── Source 3: BioRxiv / medRxiv ────────────────")
    pdf = try_biorxiv(doi=doi, title=title)
    if pdf:
        source = "medrxiv" if "medrxiv" in pdf else "biorxiv"
        result.update({"pdf_path": pdf, "source": source, "source_type": "preprint"})
        return result
    print("  [BioRxiv/medRxiv] Not found.")

    # ── 5. Unpaywall ─────────────────────────────────────
    print("\n  ── Source 4: Unpaywall ─────────────────────────")
    if doi:
        pdf = try_unpaywall(doi)
        if pdf:
            result.update({"pdf_path": pdf, "source": "unpaywall"})
            return result
    else:
        print("  [Unpaywall] Skipped — no DOI available.")

    # ── 6. Semantic Scholar ───────────────────────────────
    print("\n  ── Source 5: Semantic Scholar ──────────────────")
    pdf = try_semantic_scholar(doi=doi, title=title)
    if pdf:
        result.update({"pdf_path": pdf, "source": "semantic_scholar"})
        return result

    print("\n  [Resolver] No free source found — will use local PDF.")
    return result
