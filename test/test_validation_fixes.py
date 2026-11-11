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


def test_duplicate_parameter_id_disambiguation_in_finalize():
    from pk_pipeline.main import finalize_extracted_document, refresh_parameter_views

    doc_dict = {
        "page_metadata": {"title": "Test Title"},
        "model_classification": {"model_type": "pbpk", "confidence": 0.9, "evidence_quote": "test"},
        "model_parameters": [
            {
                "parameter_id": "param_duplicate_id",
                "parameter_name": "Serum half-life (geom mean)",
                "parameter_name_original": "half-life",
                "parameter_class": "compound_specific",
                "context": {"species": "Human", "compound": "PFOA"},
                "quantitative_data": {"value": 3.5, "unit_original": "years"},
                "provenance": {"source_location": "text", "source_section": "methods"},
            },
            {
                "parameter_id": "param_duplicate_id",
                "parameter_name": "Serum half-life (arith mean)",
                "parameter_name_original": "half-life",
                "parameter_class": "compound_specific",
                "context": {"species": "Human", "compound": "PFOA"},
                "quantitative_data": {"value": 3.8, "unit_original": "years"},
                "provenance": {"source_location": "text", "source_section": "methods"},
            },
        ],
    }

    refresh_parameter_views(doc_dict)
    # finalize_extracted_document must disambiguate and validate without raising duplicate parameter_id error
    final = finalize_extracted_document(doc_dict)
    pids = [p["parameter_id"] for p in final["model_parameters"]]
    assert len(pids) == 2
    assert len(set(pids)) == 2
    assert "param_duplicate_id" in pids
    assert "param_duplicate_id_2" in pids


def test_flatten_parameter_blocks_unique_hash_for_narrative_parameters():
    from pk_pipeline.schemas import ParameterBlock, ExtractedParameter, BiologicalContext, QuantitativeData, Provenance
    from pk_pipeline.main import flatten_parameter_blocks

    block = ParameterBlock(
        block_id="narrative_block",
        block_name="narrative_block",
        parameters=[
            ExtractedParameter(
                parameter_name="Serum half-life (geom mean)",
                parameter_name_original="serum half-life",
                context=BiologicalContext(species="Human", compound="PFOS"),
                quantitative_data=QuantitativeData(value=4.8, unit_original="years"),
                provenance=Provenance(source_location="text", source_section="methods"),
            ),
            ExtractedParameter(
                parameter_name="Serum half-life (arith mean)",
                parameter_name_original="serum half-life",
                context=BiologicalContext(species="Human", compound="PFOS"),
                quantitative_data=QuantitativeData(value=5.4, unit_original="years"),
                provenance=Provenance(source_location="text", source_section="methods"),
            ),
        ]
    )

    flat = flatten_parameter_blocks([block])
    assert len(flat) == 2
    assert flat[0]["parameter_id"] != flat[1]["parameter_id"]
    assert flat[0]["parameter_id"].startswith("param_")
    assert flat[1]["parameter_id"].startswith("param_")
