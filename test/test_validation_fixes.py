import pytest
from pk_pipeline.schemas import (
    ModelStructure,
    Derivation,
    Provenance,
    ExtractedParameter,
    ExtractedDocument,
)
from pk_pipeline.main import refresh_parameter_views


def test_equations_provided_diagram():
    ms = ModelStructure(equations_provided="diagram")
    assert ms.equations_provided == "diagram"

    ms_loose = ModelStructure(equations_provided="Figure 1 Diagram")
    assert ms_loose.equations_provided == "diagram"


def test_derivation_from_string():
    d = Derivation.model_validate("Held constant from Nonhuman Primate model")
    assert d.method == "Held constant from Nonhuman Primate model"

    p = Provenance.model_validate({
        "source_location": "Table 1",
        "derivation": "Held constant from Nonhuman Primate model"
    })
    assert p.derivation is not None
    assert p.derivation.method == "Held constant from Nonhuman Primate model"


def test_extracted_document_validation_with_diagram_and_derivation():
    doc_dict = {
        "model_structure": {
            "equations_provided": "diagram",
            "compartments": ["Central", "Tissue"],
            "connections": [{"source": "Central", "target": "Tissue", "direction": "bidirectional"}]
        },
        "model_parameters": [
            {
                "parameter_id": "test_param_1",
                "parameter_name": "Clearance",
                "parameter_name_original": "CL",
                "context": {"species": "human", "compound": "PFOA"},
                "quantitative_data": {"value": 0.05, "unit": "L/h"},
                "provenance": {
                    "source_table": "Table 1",
                    "derivation": "Held constant from Nonhuman Primate model"
                }
            }
        ]
    }

    refresh_parameter_views(doc_dict)
    doc = ExtractedDocument.model_validate(doc_dict)
    assert doc.model_structure.equations_provided == "diagram"
    assert doc.model_parameters[0].provenance.derivation.method == "Held constant from Nonhuman Primate model"
    assert doc.compound_specific_parameters[0].provenance.derivation.method == "Held constant from Nonhuman Primate model"
