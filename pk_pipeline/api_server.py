import os
import glob
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Form, BackgroundTasks, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from pk_pipeline.verifier import Tier1Verifier
from pk_pipeline.tan_assessor import evaluate_tan_from_document, normalize_tan_assessment
from pk_pipeline.schemas import ResponseOption

logger = logging.getLogger("apex_ui_api")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="APEX v2 PBPK API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUT_DIR = Path("output")
TEST_DATA_DIR = Path("pk_pipeline/test_data")
PBPK_DATA_DIR = Path("pk_pipeline/pbpk_data")
TAN_DIR = Path("output/tan_markdown_assessment")

verifier = Tier1Verifier()

def find_pdf_for_doc(doc_name: str) -> Optional[Path]:
    """Find the source PDF matching doc_name across test_data and pbpk_data."""
    base = doc_name.replace(".json", "")
    candidates = [
        TEST_DATA_DIR / f"{base}.pdf",
        PBPK_DATA_DIR / f"{base}.pdf",
    ]
    # Check case-insensitive and partial prefix
    for c in candidates:
        if c.exists():
            return c
    
    # Search all PDFs
    for p in list(TEST_DATA_DIR.glob("*.pdf")) + list(PBPK_DATA_DIR.glob("*.pdf")):
        if base.lower() in p.stem.lower() or p.stem.lower() in base.lower():
            return p
    return None

def find_markdown_for_doc(doc_name: str) -> Optional[Path]:
    """Find converted markdown for a document."""
    base = doc_name.replace(".json", "")
    candidates = [
        TAN_DIR / f"{base}.md",
        TAN_DIR / f"{base.lower()}_converted.md",
        TAN_DIR / f"{base}_converted.md",
    ]
    for c in candidates:
        if c.exists():
            return c
    # Search partial
    for m in TAN_DIR.glob("*.md"):
        if base.lower() in m.stem.lower() or m.stem.lower() in base.lower():
            if not m.name.endswith("_report.md"):
                return m
    return None

def find_tan_for_doc(doc_name: str, doc_data: dict) -> Optional[dict]:
    """Find or extract Tan assessment."""
    if "tan_assessment" in doc_data and isinstance(doc_data["tan_assessment"], dict):
        return doc_data["tan_assessment"]
    
    base = doc_name.replace(".json", "")
    candidates = [
        TAN_DIR / f"{base}_tan_assessment.json",
        TAN_DIR / f"{base.lower()}_tan_assessment.json",
    ]
    for c in candidates:
        if c.exists():
            try:
                with open(c) as f:
                    return json.load(f)
            except Exception:
                pass
    
    for t in TAN_DIR.glob("*_tan_assessment.json"):
        if base.lower() in t.stem.lower() or t.stem.lower() in base.lower():
            try:
                with open(t) as f:
                    return json.load(f)
            except Exception:
                pass

    # Deterministic fallback evaluation from doc_data
    if doc_data.get("model_parameters") or doc_data.get("model_context"):
        try:
            tan_obj = evaluate_tan_from_document(doc_data)
            return tan_obj.model_dump()
        except Exception as e:
            logger.warning(f"Error evaluating Tan for {doc_name}: {e}")
    return None


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "2.0.0", "service": "APEX PBPK Extraction Engine"}


@app.get("/api/documents")
def list_documents():
    """List all extracted documents and available PDFs."""
    results = []
    
    # 1. Extracted JSON documents in output/
    for json_path in sorted(OUTPUT_DIR.glob("*.json")):
        if json_path.name.startswith("."):
            continue
        try:
            with open(json_path) as f:
                data = json.load(f)
            
            doc_id = json_path.name
            meta = data.get("page_metadata") or {}
            params = data.get("model_parameters") or []
            
            pdf_path = find_pdf_for_doc(doc_id)
            md_path = find_markdown_for_doc(doc_id)
            tan_data = find_tan_for_doc(doc_id, data)
            
            tan_score = None
            if tan_data:
                items = tan_data.get("items") or []
                yes_count = sum(1 for it in items if str(it.get("response")).lower() in ("yes", "responseoption.yes"))
                part_count = sum(1 for it in items if str(it.get("response")).lower() in ("partially", "responseoption.partially"))
                tan_score = {
                    "total": len(items),
                    "supported": yes_count + part_count,
                    "fit_for_purpose": tan_data.get("overall_fit_for_purpose", ""),
                }

            results.append({
                "id": doc_id,
                "title": meta.get("title") or json_path.stem,
                "authors": meta.get("authors") or [],
                "year": meta.get("year"),
                "journal": meta.get("journal"),
                "parameter_count": len(params),
                "has_pdf": pdf_path is not None,
                "has_markdown": md_path is not None,
                "has_tan": tan_data is not None,
                "tan_score": tan_score,
                "model_type": (data.get("model_classification") or {}).get("model_type", "PBPK"),
                "compounds": sorted(list({
                    str((p.get("context") or {}).get("compound"))
                    for p in params
                    if (p.get("context") or {}).get("compound")
                })),
                "species": sorted(list({
                    str((p.get("context") or {}).get("species"))
                    for p in params
                    if (p.get("context") or {}).get("species")
                })),
            })
        except Exception as e:
            logger.warning(f"Error reading {json_path}: {e}")

    return {"documents": results}


@app.get("/api/documents/{doc_id}")
def get_document(doc_id: str):
    """Retrieve complete extracted document JSON."""
    json_path = OUTPUT_DIR / doc_id
    if not json_path.exists():
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        with open(json_path) as f:
            data = json.load(f)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read document: {e}")


@app.get("/api/documents/{doc_id}/pdf")
def get_document_pdf(doc_id: str):
    """Serve PDF file for browser viewing / highlighting."""
    pdf_path = find_pdf_for_doc(doc_id)
    if not pdf_path or not pdf_path.exists():
        raise HTTPException(status_code=404, detail="Source PDF not found for this document")
    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=pdf_path.name,
        content_disposition_type="inline",
    )


@app.get("/api/documents/{doc_id}/pages/{page_num}")
def get_document_page_image(doc_id: str, page_num: int, dpi: int = 150):
    """Render a single PDF page into a high-resolution PNG image."""
    pdf_path = find_pdf_for_doc(doc_id)
    if not pdf_path or not pdf_path.exists():
        raise HTTPException(status_code=404, detail="Source PDF not found for this document")
    
    dpi = max(72, min(dpi, 300))
    try:
        import pymupdf
        doc = pymupdf.open(pdf_path)
        if page_num < 1 or page_num > len(doc):
            doc.close()
            raise HTTPException(status_code=404, detail=f"Page {page_num} out of bounds (1-{len(doc)})")
        
        page = doc[page_num - 1]
        pix = page.get_pixmap(dpi=dpi)
        img_bytes = pix.tobytes("png")
        doc.close()
        
        return Response(
            content=img_bytes,
            media_type="image/png",
            headers={"Cache-Control": "public, max-age=86400"}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to render page image: {e}")


@app.get("/api/documents/{doc_id}/pdf/info")
def get_document_pdf_info(doc_id: str):
    """Get page count and metadata for document PDF."""
    pdf_path = find_pdf_for_doc(doc_id)
    if not pdf_path or not pdf_path.exists():
        return {"available": False, "page_count": 0}
    try:
        import pymupdf
        doc = pymupdf.open(pdf_path)
        count = len(doc)
        doc.close()
        return {"available": True, "page_count": count, "filename": pdf_path.name}
    except Exception as e:
        return {"available": False, "page_count": 0, "error": str(e)}


@app.get("/api/documents/{doc_id}/markdown")
def get_document_markdown(doc_id: str):
    """Return converted markdown text."""
    md_path = find_markdown_for_doc(doc_id)
    if not md_path or not md_path.exists():
        return {"markdown": "", "available": False}
    try:
        with open(md_path, encoding="utf-8", errors="replace") as f:
            content = f.read()
        return {"markdown": content, "available": True, "filename": md_path.name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read markdown: {e}")


@app.get("/api/documents/{doc_id}/verification")
def get_document_verification(doc_id: str):
    """Run Tier 1 rule engine verifier on the document and return report."""
    json_path = OUTPUT_DIR / doc_id
    if not json_path.exists():
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        with open(json_path) as f:
            doc = json.load(f)
        report = verifier.verify(doc)
        
        # Serialize report cleanly
        flags = []
        for f in report.flags:
            flags.append({
                "param_index": f.param_index,
                "param_name": f.param_name,
                "severity": f.severity,
                "rule": f.rule,
                "message": f.message,
                "suggested_fix": f.suggested_fix,
            })
            
        return {
            "tier": report.tier,
            "elapsed_ms": report.elapsed_ms,
            "total_parameters": report.total_parameters,
            "parameters_with_flags": report.parameters_with_flags,
            "total_flags": report.total_flags,
            "error_count": report.error_count,
            "warning_count": report.warning_count,
            "clean": report.clean,
            "flags": flags,
            "summary": report.summary,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Verification failed: {e}")


@app.get("/api/documents/{doc_id}/tan")
def get_document_tan(doc_id: str):
    """Get the Tan 36-item PBPK reporting assessment."""
    json_path = OUTPUT_DIR / doc_id
    if not json_path.exists():
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        with open(json_path) as f:
            doc = json.load(f)
        tan = find_tan_for_doc(doc_id, doc)
        if not tan:
            tan_obj = evaluate_tan_from_document(doc)
            tan = tan_obj.model_dump()
        return tan
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get Tan assessment: {e}")


class ParameterUpdateRequest(BaseModel):
    value: Optional[float] = None
    value_text: Optional[str] = None
    unit: Optional[str] = None
    parameter_name: Optional[str] = None
    compound: Optional[str] = None
    species: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


@app.patch("/api/documents/{doc_id}/parameters/{param_id}")
def update_parameter(doc_id: str, param_id: str, req: ParameterUpdateRequest):
    """Update an extracted parameter in place (Human-in-the-loop review)."""
    json_path = OUTPUT_DIR / doc_id
    if not json_path.exists():
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        with open(json_path) as f:
            doc = json.load(f)
        
        params = doc.get("model_parameters") or []
        target = None
        for p in params:
            if p.get("parameter_id") == param_id:
                target = p
                break
        
        if not target:
            raise HTTPException(status_code=404, detail=f"Parameter {param_id} not found")
        
        qdata = target.setdefault("quantitative_data", {})
        ctx = target.setdefault("context", {})
        prov = target.setdefault("provenance", {})
        
        if req.value is not None:
            qdata["value"] = req.value
        if req.value_text is not None:
            qdata["value_text"] = req.value_text
        if req.unit is not None:
            qdata["unit_standardized"] = req.unit
            qdata["unit"] = req.unit
        if req.parameter_name is not None:
            target["parameter_name_standardized"] = req.parameter_name
        if req.compound is not None:
            ctx["compound"] = req.compound
        if req.species is not None:
            ctx["species"] = req.species
        if req.status is not None:
            prov["status"] = req.status
        if req.notes is not None:
            prov["curator_notes"] = req.notes
        
        prov["reviewed_by_human"] = True
        
        # Write back safely
        with open(json_path, "w") as f:
            json.dump(doc, f, indent=2)
            
        return {"status": "success", "updated_parameter": target}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Update failed: {e}")


@app.post("/api/upload")
async def upload_document(
    file: UploadFile = File(...),
    run_tan: bool = Form(True),
):
    """Upload a paper (PDF, JSON, or Markdown) and process it into the APEX PBPK workspace."""
    filename = file.filename or "uploaded_document"
    ext = Path(filename).suffix.lower()
    
    if ext not in (".pdf", ".json", ".md"):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{ext}'. Supported formats: .pdf, .json, .md"
        )
    
    stem = Path(filename).stem
    safe_stem = "".join(c if c.isalnum() or c in ("-", "_", " ") else "_" for c in stem).strip()
    if not safe_stem:
        safe_stem = "uploaded_paper"

    content = await file.read()
    
    PBPK_DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TAN_DIR.mkdir(parents=True, exist_ok=True)

    if ext == ".pdf":
        target_pdf = PBPK_DATA_DIR / f"{safe_stem}.pdf"
        target_pdf.write_bytes(content)
        
        # Read PDF metadata with pymupdf
        title = safe_stem
        authors = []
        page_count = 1
        year = None
        extracted_params = []
        table_evidence = []
        
        try:
            import pymupdf
            doc = pymupdf.open(stream=content, filetype="pdf")
            page_count = len(doc)
            meta = doc.metadata or {}
            if meta.get("title") and len(meta["title"].strip()) > 3:
                title = meta["title"].strip()
            if meta.get("author"):
                authors = [a.strip() for a in meta["author"].split(";") if a.strip()]
            if meta.get("creationDate") and len(meta["creationDate"]) >= 6:
                raw_d = meta["creationDate"].replace("D:", "")
                if raw_d[:4].isdigit():
                    year = int(raw_d[:4])
            
            # Extract basic tabular evidence from PDF
            for page_idx, page in enumerate(doc):
                try:
                    tabs = page.find_tables()
                    for t_idx, tab in enumerate(tabs.tables):
                        df_rows = tab.extract()
                        if df_rows and len(df_rows) > 1:
                            headers = [str(h or "").strip() for h in df_rows[0]]
                            table_name = f"Table (Page {page_idx + 1}, #{t_idx + 1})"
                            table_evidence.append({
                                "table_id": f"tab_p{page_idx + 1}_{t_idx + 1}",
                                "table_title": table_name,
                                "source_page": page_idx + 1,
                                "headers": headers,
                                "row_count": len(df_rows) - 1,
                            })
                            # Sample parameters from rows
                            for r_idx, row in enumerate(df_rows[1:15]):
                                row_str = [str(c or "").strip() for c in row]
                                if len(row_str) >= 2 and row_str[0]:
                                    param_name = row_str[0]
                                    val_str = row_str[1]
                                    val_num = None
                                    try:
                                        val_num = float(val_str.split()[0].replace(",", ""))
                                    except (ValueError, IndexError):
                                        pass
                                    
                                    if len(param_name) < 80:
                                        param_id = f"param_p{page_idx + 1}_r{r_idx + 1}_{t_idx + 1}"
                                        extracted_params.append({
                                            "parameter_id": param_id,
                                            "parameter_name_original": param_name,
                                            "parameter_name_standardized": param_name.lower().replace(" ", "_"),
                                            "quantitative_data": {
                                                "value": val_num,
                                                "value_text": val_str,
                                                "unit": row_str[2] if len(row_str) > 2 and len(row_str[2]) < 20 else "",
                                            },
                                            "context": {
                                                "compound": "Uploaded Compound",
                                                "species": "Human",
                                            },
                                            "provenance": {
                                                "source_page": page_idx + 1,
                                                "source_location": table_name,
                                                "source_quote": f"{param_name} = {val_str}",
                                            }
                                        })
                except Exception as te:
                    logger.debug(f"Table extract skip page {page_idx}: {te}")
            doc.close()
        except Exception as e:
            logger.warning(f"Could not read PDF metadata for {safe_stem}: {e}")
            
        # Convert to Markdown
        md_text = ""
        target_md = TAN_DIR / f"{safe_stem}_converted.md"
        try:
            from pk_pipeline.tan_assessor import convert_pdf_to_markdown
            md_text = convert_pdf_to_markdown(str(target_pdf), output_md_path=str(target_md))
        except Exception as e:
            logger.warning(f"pymupdf4llm conversion failed: {e}. Falling back to pymupdf text.")
            try:
                import pymupdf
                doc = pymupdf.open(str(target_pdf))
                blocks = []
                for idx, page in enumerate(doc):
                    t = page.get_text()
                    blocks.append(f"<!-- PAGE {idx + 1} -->\n### [Page {idx + 1}]\n{t}")
                md_text = "\n\n".join(blocks)
                target_md.write_text(md_text, encoding="utf-8")
                doc.close()
            except Exception as e2:
                logger.error(f"Fallback text extraction failed: {e2}")

        doc_json_path = OUTPUT_DIR / f"{safe_stem}.json"
        doc_data = {
            "page_metadata": {
                "title": title,
                "authors": authors,
                "year": year,
                "page_count": page_count,
                "filename": filename,
            },
            "model_classification": {
                "model_type": "PBPK",
                "species": ["Human"],
                "compounds": [],
            },
            "model_parameters": extracted_params,
            "table_evidence": table_evidence,
            "model_structure": {
                "compartments": ["Blood / Plasma", "Liver", "Kidney", "Gut / GI Tract", "Fat", "Muscle"],
                "connections": [
                    {"from": "Blood / Plasma", "to": "Liver", "type": "blood_flow"},
                    {"from": "Blood / Plasma", "to": "Kidney", "type": "blood_flow"},
                    {"from": "Gut / GI Tract", "to": "Liver", "type": "portal_vein"},
                ],
                "dosing_protocols": [],
            },
            "status": "ready",
        }

        if run_tan and md_text:
            try:
                from pk_pipeline.tan_assessor import assess_tan_from_markdown
                tan_res = await assess_tan_from_markdown(md_text, paper_title=safe_stem)
                tan_dict = tan_res.model_dump()
                tan_json_path = TAN_DIR / f"{safe_stem}_tan_assessment.json"
                with open(tan_json_path, "w", encoding="utf-8") as f:
                    json.dump(tan_dict, f, indent=2)
                doc_data["tan_assessment"] = tan_dict
            except Exception as e:
                logger.warning(f"Tan assessment failed: {e}. Falling back to evaluate_tan_from_document.")
                try:
                    tan_obj = evaluate_tan_from_document(doc_data)
                    doc_data["tan_assessment"] = tan_obj.model_dump()
                except Exception as e2:
                    logger.error(f"Fallback Tan assessment failed: {e2}")

        with open(doc_json_path, "w", encoding="utf-8") as f:
            json.dump(doc_data, f, indent=2)

        return {
            "status": "success",
            "doc_id": f"{safe_stem}.json",
            "title": title,
            "filename": filename,
            "pages": page_count,
            "parameter_count": len(extracted_params),
            "has_pdf": True,
            "has_markdown": bool(md_text),
            "message": f"Successfully uploaded and processed '{filename}'."
        }

    elif ext == ".json":
        try:
            parsed = json.loads(content.decode("utf-8"))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON file: {e}")
        
        target_json = OUTPUT_DIR / f"{safe_stem}.json"
        with open(target_json, "w", encoding="utf-8") as f:
            json.dump(parsed, f, indent=2)
            
        title = (parsed.get("page_metadata") or {}).get("title") or safe_stem
        params = parsed.get("model_parameters") or []
        
        return {
            "status": "success",
            "doc_id": f"{safe_stem}.json",
            "title": title,
            "filename": filename,
            "parameter_count": len(params),
            "message": f"Successfully imported '{filename}' with {len(params)} parameters."
        }

    elif ext == ".md":
        target_md = TAN_DIR / f"{safe_stem}.md"
        target_md.write_bytes(content)
        md_text = content.decode("utf-8", errors="replace")
        
        doc_json_path = OUTPUT_DIR / f"{safe_stem}.json"
        doc_data = {
            "page_metadata": {
                "title": safe_stem,
                "filename": filename,
            },
            "model_parameters": [],
            "status": "uploaded",
        }
        
        if run_tan:
            try:
                from pk_pipeline.tan_assessor import assess_tan_from_markdown
                tan_res = await assess_tan_from_markdown(md_text, paper_title=safe_stem)
                doc_data["tan_assessment"] = tan_res.model_dump()
            except Exception as e:
                logger.warning(f"Tan assessment failed on markdown: {e}")
                
        with open(doc_json_path, "w", encoding="utf-8") as f:
            json.dump(doc_data, f, indent=2)
            
        return {
            "status": "success",
            "doc_id": f"{safe_stem}.json",
            "title": safe_stem,
            "filename": filename,
            "message": f"Successfully uploaded Markdown file '{filename}'."
        }


# Serve compiled UI frontend if available
UI_DIST = Path("ui/dist")
if UI_DIST.exists():
    app.mount("/", StaticFiles(directory="ui/dist", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("pk_pipeline.api_server:app", host="0.0.0.0", port=8000, reload=True)

