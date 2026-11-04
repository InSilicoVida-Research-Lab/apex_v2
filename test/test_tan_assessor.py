from pk_pipeline.tan_assessor import (
    TAN_QUESTIONNAIRE_ITEMS,
    build_tan_assessment_prompt,
    evaluate_tan_from_document,
    normalize_biological_basis,
    normalize_tan_assessment,
    verify_parameters_deterministically,
)
from pk_pipeline.schemas import ResponseOption


def test_tan_questionnaire_is_complete_and_excludes_generic_background():
    assessment = evaluate_tan_from_document({})

    assert len(assessment.items) == len(TAN_QUESTIONNAIRE_ITEMS)
    assert all(
        item.response == ResponseOption.I_CANNOT_ANSWER
        for item in assessment.items
        if item.item_id != "TAN_1.3"
    )
    assert next(item for item in assessment.items if item.item_id == "TAN_1.3").response == ResponseOption.YES
    assert "Introduction" in assessment.assessment_scope

    prompt = build_tan_assessment_prompt("{}")
    assert "generic Introduction/Background" in prompt
    assert "Do not use outside knowledge" in prompt


def test_tan_normalization_rejects_unsupported_llm_rating_and_recomputes_confidence():
    raw = {
        "items": [
            {
                "item_id": "TAN_2.1.1",
                "section": "wrong section supplied by model",
                "question": "wrong question supplied by model",
                "response": "yes",
                "details": "The model said yes.",
                "evidence": [],
                "confidence": "high",
                "confidence_basis": "model self-score",
            }
        ]
    }

    assessment = normalize_tan_assessment(raw, {})
    item = next(item for item in assessment.items if item.item_id == "TAN_2.1.1")

    assert item.response == ResponseOption.I_CANNOT_ANSWER
    assert item.confidence == "low"
    assert item.section == "2.1 Executive summary"
    assert "auditable" in item.details


def test_biological_basis_confidence_is_derived_from_quote_and_location():
    document = {
        "biological_basis": {
            "adme_determinants": ["renal reabsorption"],
            "adme_determinant_evidence": [
                {
                    "description": "Renal reabsorption controls long retention.",
                    "evidence_quote": "The model includes renal reabsorption.",
                    "source_location": "Methods, model structure",
                    "evidence_directness": "explicit",
                    "evidence_confidence": "low",
                }
            ],
            "stated_assumptions": [
                {
                    "description": "Renal reabsorption is represented explicitly.",
                    "evidence_quote": "Renal reabsorption was modeled.",
                    "source_location": "Methods",
                    "evidence_directness": "explicit",
                    "evidence_confidence": "low",
                }
            ],
            "specialized_mechanisms": ["renal reabsorption"],
        }
    }

    normalize_biological_basis(document)
    basis = document["biological_basis"]

    assert basis["evidence_confidence"] == "high"
    assert basis["adme_determinant_evidence"][0]["evidence_confidence"] == "high"
    assert basis["stated_assumptions"][0]["evidence_confidence"] == "high"
    assert "deterministically" not in basis["confidence_basis"].lower()


def test_refined_parameter_verification_uses_four_checks():
    parameter = {
        "symbol_original": "ka",
        "parameter_subclass": "absorption_rate_constant",
        "quantitative_data": {
            "value_text": "0.5",
            "value": 0.5,
            "unit_original": "1/h",
            "unit_standardized": "h^-1",
        },
        "provenance": {
            "source_table": "Table 1",
            "source_quote": "ka 0.5",
            "reference": "Smith et al. (2020)",
            "parameter_status": "Literature",
        },
    }
    document = {
        "model_parameters": [parameter],
        "table_evidence": [{"table_id": "Table 1", "cells": []}],
    }

    summary = verify_parameters_deterministically(document)

    assert parameter["verification_score"] == 1.0
    assert all(parameter["verification_checks"].values())
    assert parameter["needs_review"] is False
    assert summary["mean_verification_score"] == 1.0
