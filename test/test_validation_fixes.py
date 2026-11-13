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


def test_bug14_find_matched_cell_empty_cell_not_matched():
    from pk_pipeline.verifier import find_matched_cell

    te = {
        "table_id": "Table 1",
        "cells": [
            {"cell_id": "c1", "text": "", "numeric_value": None, "row_path": ["Row 1"], "column_path": ["Col 1"]},
            {"cell_id": "c2", "text": "   ", "numeric_value": None, "row_path": ["Row 1"], "column_path": ["Col 2"]},
            {"cell_id": "c3", "text": "100", "numeric_value": 100.0, "row_path": ["Row 1"], "column_path": ["Col 3"]},
        ]
    }

    param = {
        "parameter_name_original": "Test Param",
        "quantitative_data": {"value": 0.0, "value_text": "0"},
        "provenance": {"source_table": "Table 1"},
    }
    match = find_matched_cell(param, te)
    assert match is None

    param_valid = {
        "parameter_name_original": "Test Param",
        "quantitative_data": {"value": 100.0, "value_text": "100"},
        "provenance": {"source_table": "Table 1"},
    }
    match_valid = find_matched_cell(param_valid, te)
    assert match_valid is not None
    assert match_valid["cell_id"] == "c3"


def test_bug15_rule10_column_context_and_cross_table():
    from pk_pipeline.verifier import Tier1Verifier

    verifier = Tier1Verifier()

    params_diff_cols = [
        {
            "parameter_name_original": "Liver weight",
            "parameter_class": "physiological",
            "parameter_subclass": "tissue_weight",
            "context": {"species": "Human", "compound": "PFOA"},
            "quantitative_data": {"value": 1500.0, "unit": "g"},
            "provenance": {
                "source_table": "Table 1",
                "column_path": ["Maternal", "Mean"],
                "column_id": "col_1",
                "source_quote": "1500",
                "confidence": "high",
            },
        },
        {
            "parameter_name_original": "Liver weight",
            "parameter_class": "physiological",
            "parameter_subclass": "tissue_weight",
            "context": {"species": "Human", "compound": "PFOA"},
            "quantitative_data": {"value": 50.0, "unit": "g"},
            "provenance": {
                "source_table": "Table 1",
                "column_path": ["Fetal", "Mean"],
                "column_id": "col_2",
                "source_quote": "50",
                "confidence": "high",
            },
        },
    ]

    report = verifier.verify({"model_parameters": params_diff_cols, "table_evidence": []})
    conflict_flags = [f for f in report.flags if f.rule == "CONFLICTING_ENTRY"]
    assert len(conflict_flags) == 0, f"False conflict detected: {conflict_flags}"

    params_cross_table = [
        {
            "parameter_name_original": "CL",
            "parameter_class": "compound_specific",
            "parameter_subclass": "clearance",
            "context": {"species": "Human", "compound": "PFOA"},
            "quantitative_data": {"value": 0.05, "unit": "L/h"},
            "provenance": {
                "source_table": "Table 1",
                "column_path": ["Clearance"],
                "source_quote": "0.05",
                "confidence": "high",
            },
        },
        {
            "parameter_name_original": "CL",
            "parameter_class": "compound_specific",
            "parameter_subclass": "clearance",
            "context": {"species": "Human", "compound": "PFOA"},
            "quantitative_data": {"value": 0.05, "unit": "L/h"},
            "provenance": {
                "source_table": "Table 2",
                "column_path": ["Clearance"],
                "source_quote": "0.05",
                "confidence": "high",
            },
        },
    ]
    report2 = verifier.verify({"model_parameters": params_cross_table, "table_evidence": []})
    dup_flags = [f for f in report2.flags if f.rule == "DUPLICATE_ENTRY"]
    assert len(dup_flags) == 1, f"Cross-table duplicate was not caught: {report2.flags}"


def test_bug17_range_cells_set_start_and_end_value():
    from pk_pipeline.main import normalize_parameter_units_and_ranges

    param = {
        "parameter_name_original": "Body weight (kg)",
        "parameter_subclass": "body_weight",
        "quantitative_data": {
            "value": 56.9,
            "value_text": "56.9 - 70 (gestation)",
            "unit_original": "kg",
        },
        "provenance": {"source_table": "Table 1", "reference": "Loccisano et al."},
    }

    normalized = normalize_parameter_units_and_ranges(param)
    q = normalized["quantitative_data"]
    assert q["value"] is None
    assert q["start_value"] == 56.9
    assert q["end_value"] == 70.0
    assert q["uncertainty"]["type"] == "time_varying_range"
    assert q["uncertainty"]["lower"] == 56.9
    assert q["uncertainty"]["upper"] == 70.0


def test_force_backend_local_does_not_leak_to_cloud():
    from pk_pipeline.config import Config
    from pk_pipeline.ml_services import SGLangExtractor

    orig_key = Config.OPENAI_API_KEY
    orig_base = Config.OPENAI_BASE_URL
    orig_force = getattr(Config, "FORCE_BACKEND", "auto")
    try:
        Config.OPENAI_API_KEY = "sk-fake-secret-key-12345"
        Config.OPENAI_BASE_URL = "http://fake-cloud-endpoint:1234/v1"
        Config.FORCE_BACKEND = "local"

        extractor = SGLangExtractor(use_4bit=False)
        assert extractor.backend_mode != "openai_api"
    finally:
        Config.OPENAI_API_KEY = orig_key
        Config.OPENAI_BASE_URL = orig_base
        Config.FORCE_BACKEND = orig_force
