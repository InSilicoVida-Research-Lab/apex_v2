import copy

import pytest

from pk_pipeline.corpus import evaluate_documents, load_reference, validate_corpus
from pk_pipeline.schemas import ExtractedDocument, Provenance, ProvenanceStatus


def test_reference_corpus_is_complete_and_valid():
    report = validate_corpus()

    assert report["valid"] is True
    assert report["paper_count"] == 5
    assert report["total_parameters"] == 341


def test_reference_evaluates_perfectly_against_itself():
    document = load_reference("dean_2025_pfas")

    report = evaluate_documents(
        document,
        document,
        paper_id="dean_2025_pfas",
        corpus_version="test",
    )

    assert report["parameter_metrics"]["precision"] == 1.0
    assert report["parameter_metrics"]["recall"] == 1.0
    assert report["parameter_metrics"]["f1"] == 1.0
    assert not report["ambiguous_matches"]


def test_empty_prediction_is_reported_as_missing_not_clean():
    reference = load_reference("dean_2025_pfas")
    prediction_data = reference.model_dump(mode="json")
    prediction_data["model_parameters"] = []
    prediction_data["system_specific_parameters"] = []
    prediction_data["compound_specific_parameters"] = []
    prediction = ExtractedDocument.model_validate(prediction_data, context={"allow_empty_parameters": True})

    report = evaluate_documents(
        reference,
        prediction,
        paper_id="dean_2025_pfas",
        corpus_version="test",
    )

    assert report["parameter_metrics"]["matched_count"] == 0
    assert report["parameter_metrics"]["recall"] == 0.0
    assert len(report["unmatched_reference_parameter_ids"]) == 56


def test_value_and_unit_mismatches_are_reported():
    reference = load_reference("dean_2025_pfas")
    prediction_data = copy.deepcopy(reference.model_dump(mode="json"))
    parameter = prediction_data["model_parameters"][0]
    parameter["quantitative_data"]["value"] *= 2
    parameter["quantitative_data"]["unit_standardized"] = "mg"
    prediction_data["system_specific_parameters"][0] = copy.deepcopy(parameter)
    prediction = ExtractedDocument.model_validate(prediction_data)

    report = evaluate_documents(
        reference,
        prediction,
        paper_id="dean_2025_pfas",
        corpus_version="test",
    )

    assert report["field_agreement"]["value"]["mismatched"] == 1
    assert report["field_agreement"]["unit"]["mismatched"] == 1


def test_provenance_legacy_values_normalize_and_keep_raw_label():
    provenance = Provenance(status="optimized")

    assert provenance.status == ProvenanceStatus.FITTED
    assert provenance.status_raw == "optimized"


def test_document_rejects_stale_derived_parameter_views():
    document_data = load_reference("dean_2025_pfas").model_dump(mode="json")
    document_data["system_specific_parameters"] = []

    with pytest.raises(ValueError, match="system_specific_parameters"):
        ExtractedDocument.model_validate(document_data)
