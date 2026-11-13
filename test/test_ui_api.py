import pytest
from fastapi.testclient import TestClient
from pk_pipeline.api_server import app

client = TestClient(app)

def test_health_endpoint():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["version"] == "2.0.0"

def test_list_documents_endpoint():
    res = client.get("/api/documents")
    assert res.status_code == 200
    data = res.json()
    assert "documents" in data
    assert len(data["documents"]) > 0
    # Check that Loccisano 2013 is in the list
    doc_ids = [d["id"] for d in data["documents"]]
    assert any("Loccisano" in did for did in doc_ids)

def test_get_document_loccisano():
    res = client.get("/api/documents/Loccisano%202013.json")
    assert res.status_code == 200
    doc = res.json()
    assert "model_parameters" in doc
    assert len(doc["model_parameters"]) > 0
    assert doc["page_metadata"]["title"] is not None

def test_verification_endpoint():
    res = client.get("/api/documents/Loccisano%202013.json/verification")
    assert res.status_code == 200
    report = res.json()
    assert "total_parameters" in report
    assert report["total_parameters"] == 128
    assert "flags" in report
    assert "error_count" in report

def test_tan_assessment_endpoint():
    res = client.get("/api/documents/Loccisano%202013.json/tan")
    assert res.status_code == 200
    tan = res.json()
    assert "items" in tan
    assert len(tan["items"]) == 36
    assert tan["items"][0]["item_id"] == "TAN_1.1"

def test_ui_static_index_serving():
    res = client.get("/")
    assert res.status_code == 200
    assert '<div id="root"' in res.text

def test_upload_json_endpoint(tmp_path):
    sample_json = {
        "page_metadata": {"title": "Test Paper Upload"},
        "model_parameters": [
            {
                "parameter_id": "test_p1",
                "parameter_name_original": "Body Weight",
                "quantitative_data": {"value": 70.0, "unit": "kg"},
            }
        ]
    }
    import json
    content = json.dumps(sample_json).encode("utf-8")
    files = {"file": ("test_paper.json", content, "application/json")}
    res = client.post("/api/upload", files=files, data={"run_tan": "false"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["doc_id"] == "test_paper.json"
    assert data["parameter_count"] == 1

def test_upload_unsupported_file_fails():
    files = {"file": ("test.exe", b"binary", "application/octet-stream")}
    res = client.post("/api/upload", files=files)
    assert res.status_code == 400
    assert "Unsupported file format" in res.json()["detail"]

def test_render_pdf_page_endpoint():
    res = client.get("/api/documents/Loccisano%202013.json/pages/1?dpi=72")
    assert res.status_code == 200
    assert res.headers["content-type"] == "image/png"
    assert len(res.content) > 1000

def test_pdf_info_endpoint():
    res = client.get("/api/documents/Loccisano%202013.json/pdf/info")
    assert res.status_code == 200
    data = res.json()
    assert data["available"] is True
    assert data["page_count"] == 40



