"""Test OECD GD 331 assessment schema and evaluator on extracted PBPK models.
"""

import json
import os
import sys

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pk_pipeline.schemas import (
    ExtractedDocument,
    ModelContext,
    SoftwareMetadata,
    ReproducibilityMetadata,
    ModeOfAction,
    ExtendedSensitivityUncertainty,
    ValidationResult,
    DatasetRole,
    DatasetType,
    IndependenceStatus,
    OECDAssessment,
    OECDChecklistItem,
    ResponseOption,
)
from pk_pipeline.oecd_assessor import evaluate_oecd_from_document, CANONICAL_CHECKLIST_ITEMS


def test_oecd_schema_validation():
    print("--- 1. Testing Schema Construction & Validation ---")
    doc_path = "benchmarking/outputs/dean_2025_pfas/apex_v2.json"
    with open(doc_path, "r") as f:
        doc_data = json.load(f)

    # Inject new factual metadata fields
    doc_data["software"] = {
        "name": "MCSim / R",
        "version": "6.1.0",
        "platform_type": "open_source",
        "solver": "lsoda",
        "optimization_method": "MCMC",
        "source_quote": "Simulations were performed using GNU MCSim version 6.1.0.",
    }
    doc_data["reproducibility"] = {
        "equations_available": True,
        "equations_location": "supplementary_info",
        "code_available": True,
        "code_location": "https://github.com/example/dean2025-pfas-pbpk",
        "public_repository": "https://github.com/example/dean2025-pfas-pbpk",
    }
    doc_data["mode_of_action"] = {
        "available": True,
        "description": "PPAR-alpha receptor activation and downstream transcriptional alteration in hepatocytes.",
        "toxic_moiety": "parent_chemical",
        "target_tissue": "liver",
        "graphical_representation_present": False,
    }
    doc_data["extended_sensitivity"] = {
        "analysis_type": "local",
        "method": "one-at-a-time",
        "criterion": "|NSC| > 0.1",
        "key_sensitive_parameters": ["Vmax_baso", "Km_baso", "Free"],
        "overall_impact_on_dose_metric": "Renal reabsorption transporters have highest sensitivity on plasma AUC.",
    }

    # Run deterministic OECD assessment
    print("--- 2. Running OECD GD 331 Assessment Engine ---")
    assessment = evaluate_oecd_from_document(doc_data)
    doc_data["oecd_assessment"] = assessment.model_dump()

    print(f"Total checklist items evaluated: {len(assessment.items)}")
    print(f"Checklist version: {assessment.checklist_version}")
    print(f"Fit for purpose summary: {assessment.overall_fit_for_purpose}")
    print(f"Key gaps identified: {len(assessment.key_gaps)}")
    for gap in assessment.key_gaps:
        print(f"  * {gap}")

    # Validate against ExtractedDocument Pydantic model
    print("--- 3. Validating ExtractedDocument Pydantic Strict Model ---")
    validated = ExtractedDocument.model_validate(doc_data)
    assert validated.software is not None
    assert validated.software.name == "MCSim / R"
    assert validated.reproducibility.code_available is True
    assert validated.mode_of_action.target_tissue == "liver"
    assert validated.extended_sensitivity.criterion == "|NSC| > 0.1"
    assert validated.oecd_assessment is not None
    assert len(validated.oecd_assessment.items) == 22

    # Save demo assessment report
    out_report = "benchmarking/outputs/dean_2025_pfas/oecd_assessment_report.md"
    with open(out_report, "w") as f:
        f.write("# OECD GD 331 / Tan et al. PBPK Model Evaluation Report\n\n")
        f.write(f"**Checklist Version**: {assessment.checklist_version}\n\n")
        f.write(f"**Overall Fit-for-Purpose**: {assessment.overall_fit_for_purpose}\n\n")
        f.write("## Checklist Items Summary\n\n")
        f.write("| Item ID | Category | Question | Rating | Confidence | Rationale |\n")
        f.write("|---|---|---|---|---|---|\n")
        for item in assessment.items:
            f.write(f"| {item.item_id} | {item.category} | {item.question} | `{item.response.value}` | {item.confidence} | {item.rationale} |\n")
        f.write("\n## Key Gaps Identified\n\n")
        for gap in assessment.key_gaps:
            f.write(f"- {gap}\n")

    print(f"Generated OECD assessment report at: {out_report}")
    print("All tests passed successfully!")


if __name__ == "__main__":
    test_oecd_schema_validation()
