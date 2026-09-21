"""
ingestion/pmc_fetcher.py — Multi-source paper resolver.

Resolution chain (in order):
  1. Explicit local XML  → passed directly by caller
  2. PMC OA (DOI + Title in parallel) → JATS XML fast-path
  3. Unpaywall (DOI) → free legal PDF download → OCR path
  4. Semantic Scholar (Title) → open-access PDF download → OCR path
  5. Caller falls back to local PDF OCR
"""

import os
import re
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

NCBI_ESEARCH  = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PMC_OA_FETCH  = "https://www.ncbi.nlm.nih.gov/pmc/oai/oai.cgi"
UNPAYWALL_API = "https://api.unpaywall.org/v2/{doi}"
SS_SEARCH_API = "https://api.semanticscholar.org/graph/v1/paper/search"
CACHE_DIR     = os.path.join(os.path.expanduser("~"), ".cache", "pk_pbpk_extractor")
UNPAYWALL_EMAIL = "pbpk-extractor@research.local"   # required by Unpaywall ToS


# ─────────────────────────────────────────────────────────────
# PDF scanning helpers
# ─────────────────────────────────────────────────────────────

def extract_doi_from_pdf(pdf_path: str) -> str | None:
    doi_pattern = r"\b(10\.\d{4,9}/[-._;()/:A-Z0-9]+)\b"

    try:
        import fitz
        doc = fitz.open(pdf_path)
        text = "".join(page.get_text() for page in doc[:3])
        m = re.search(doi_pattern, text, re.IGNORECASE)
        if m:
            return m.group(1).rstrip(".")
    except Exception:
        pass

    try:
        import pypdf
        with open(pdf_path, "rb") as f:
            reader = pypdf.PdfReader(f)
            text = "".join(reader.pages[i].extract_text() or "" for i in range(min(3, len(reader.pages))))
        m = re.search(doi_pattern, text, re.IGNORECASE)
        if m:
            return m.group(1).rstrip(".")
    except Exception:
        pass

    try:
        with open(pdf_path, "rb") as f:
            raw = f.read(40000)
        text = raw.decode("utf-8", errors="ignore")
        m = re.search(doi_pattern, text, re.IGNORECASE)
        if m:
            return m.group(1).rstrip(".")
    except Exception:
        pass

    return None


def extract_title_from_pdf(pdf_path: str) -> str | None:
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

    return None


# ─────────────────────────────────────────────────────────────
# Source 1 — PMC Open Access
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
    """Returns path to downloaded XML, or None."""
    if not doi and not title:
        return None
    
    found_pmcid = None
    
    # Strictly prioritize DOI if available.
    if doi:
        found_pmcid = doi_to_pmcid(doi)
    elif title and len(title) > 10 and any(c.isalpha() for c in title):
        # ONLY search by title if no DOI was extracted from the PDF at all.
        found_pmcid = title_to_pmcid(title)

    if found_pmcid:
        return fetch_pmc_xml(found_pmcid)
    return None


# ─────────────────────────────────────────────────────────────
# Source 2 — Unpaywall (free legal PDF by DOI)
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

        # Prefer the best OA location (sorted by Unpaywall)
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
# Source 3 — Semantic Scholar (open-access PDF by title/DOI)
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
# Main public resolver
# ─────────────────────────────────────────────────────────────


def fetch_supplementary_pdfs(pmcid: str) -> list[str]:
    import requests
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin
    import os
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
                
            if 'pdf' in file_name.lower() and pmcid.lower() not in file_name.lower() and 'supp' in file_name.lower():
                pass
            elif 'supp' not in href.lower() and 'bin' not in href:
                continue
                
            print(f"  [PMC Scraper] Found supplementary file: {full_url}")
            out_path = _download_pdf(full_url, f"{pmcid}_{file_name.replace('.pdf', '')}", source="pmc_supp")
            if out_path and out_path not in downloaded_pdfs:
                downloaded_pdfs.append(out_path)
                
    return downloaded_pdfs

def resolve_paper(doi: str = None, title: str = None, pmcid: str = None) -> dict:
    """
    Tries all available free sources in order.
    
    Returns a dict:
      {
        "xml_path":  str | None,   # path to PMC JATS XML (fast-path)
        "pdf_path":  str | None,   # path to downloaded free PDF (OCR path)
        "source":    str           # "pmc_xml" | "unpaywall" | "semantic_scholar" | None
      }
    """
    result = {"xml_path": None, "pdf_path": None, "source": None}

    # ── 1. Explicit PMCID ────────────────────────────────
    if pmcid:
        if not pmcid.startswith("PMC"):
            pmcid = f"PMC{pmcid}"
        xml = fetch_pmc_xml(pmcid)
        if xml:
            result.update({"xml_path": xml, "source": "pmc_xml"})
            return result

    # ── 2. PMC via DOI + Title (parallel) ────────────────
    print("\n  ── Source 1: PMC Open Access ──────────────────")
    xml = try_pmc(doi=doi, title=title)
    if xml:
        result.update({"xml_path": xml, "source": "pmc_xml"})
        return result
    print("  [PMC] Not available in OA subset.")

    # ── 3. Unpaywall (DOI required) ───────────────────────
    print("\n  ── Source 2: Unpaywall ────────────────────────")
    if doi:
        pdf = try_unpaywall(doi)
        if pdf:
            result.update({"pdf_path": pdf, "source": "unpaywall"})
            return result
    else:
        print("  [Unpaywall] Skipped — no DOI available.")

    # ── 4. Semantic Scholar ───────────────────────────────
    print("\n  ── Source 3: Semantic Scholar ─────────────────")
    pdf = try_semantic_scholar(doi=doi, title=title)
    if pdf:
        result.update({"pdf_path": pdf, "source": "semantic_scholar"})
        return result

    print("\n  [Resolver] No free source found — will use local PDF.")
    return result
