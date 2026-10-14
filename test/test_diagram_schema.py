import json
import pytest
from pk_pipeline.schemas import DiagramExtractionPage, ExtractedPage, ModelClassification, ModelStructure


def test_diagram_schema_generation():
    schema = DiagramExtractionPage.model_json_schema()
    assert "properties" in schema
    assert "model_classification" in schema["properties"]
    assert "model_structure" in schema["properties"]
    # Verify that heavy tabular parameter definitions are excluded
    assert "TableEvidence" not in schema.get("$defs", {})
    assert "TableCell" not in schema.get("$defs", {})
    assert "DoseEvent" not in schema.get("$defs", {})


def test_diagram_payload_hydration():
    sample_llm_json = {
        "model_classification": {
            "model_type": "simple_empirical_compartmental",
            "evidence_quote": "three-compartment model (Vc, Vt, Vfil)"
        },
        "model_structure": {
            "compartments": [
                {"id": "c1", "label_raw": "Central (Vc)"},
                {"id": "c2", "label_raw": "Tissue (Vt)"},
                {"id": "c3", "label_raw": "Filtrate (Vfil)"}
            ],
            "connections": [
                {"source": "c1", "target": "c2", "direction": "bidirectional", "label_raw": "k12, k21"},
                {"source": "c1", "target": "c3", "direction": "forward", "label_raw": "Qfil"}
            ]
        }
    }

    # Validate against DiagramExtractionPage
    diag_page = DiagramExtractionPage(**sample_llm_json)
    assert diag_page.model_classification.model_type == "simple_empirical_compartmental"
    assert len(diag_page.model_structure.compartments) == 3
    assert len(diag_page.model_structure.connections) == 2

    # Validate that ExtractedPage natively accepts DiagramExtractionPage output
    extracted_page = ExtractedPage(**sample_llm_json)
    assert extracted_page.model_classification.model_type == "simple_empirical_compartmental"
    assert len(extracted_page.model_structure.compartments) == 3
    assert len(extracted_page.parameter_blocks) == 0
