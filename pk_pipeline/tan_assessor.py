"""Tan et al. PBPK reporting-template questionnaire.

Tan's template is used here as a model-reporting questionnaire covering purpose,
strategy, data, structure, equations, parameters, simulations, software,
evaluation, and sensitivity/uncertainty.

The questionnaire does not treat generic Introduction/Background prose as
evidence about the PBPK model.  It also does not trust an LLM-supplied
confidence score: confidence is recalculated from the evidence references in
Python after the response is parsed.
"""

from __future__ import annotations

import json
import math
import re
from typing import Any, Dict, List, Optional, Union

from pk_pipeline.schemas import (
    EvidenceReference,
    ExtractedDocument,
    ResponseOption,
    TanPBPKAssessment,
    TanQuestionnaireItem,
)


_PURPOSE_SECTIONS = ["Title", "Abstract", "Introduction: final paragraph", "Discussion", "Conclusion"]
_METHOD_SECTIONS = ["Materials", "Methods", "Results", "Tables", "Figures", "Supplementary Information", "Supplementary Code"]
_STRUCTURE_SECTIONS = ["Materials", "Methods: model structure/physiology/parameters", "Model schematic figures", "Discussion: limitations/assumptions", "Supplementary Code"]
_EVAL_SECTIONS = ["Materials and Methods: evaluation/sensitivity", "Results", "Discussion", "Evaluation figures/tables", "Sensitivity figures/tables"]


def _question(
    item_id: str,
    section: str,
    question: str,
    allowed: List[str],
    routing: str,
    structured_fields: Optional[List[str]] = None,
) -> dict[str, Any]:
    return {
        "item_id": item_id,
        "section": section,
        "question": question,
        "allowed_source_sections": allowed,
        "routing_rule": routing,
        "structured_fields": structured_fields or [],
    }


TAN_QUESTIONNAIRE_ITEMS: List[dict[str, Any]] = [
    _question("TAN_1.1", "1. Model identification", "Name the PBPK model and target compound(s), including parent, active metabolites, and CAS/identifiers when stated.", ["Title", "Abstract", "Methods"], "Do not infer identifiers or compounds from general Introduction background.", ["model_name", "target_compounds", "parent_or_metabolites", "identifiers"]),
    _question("TAN_1.2", "1. Model identification", "Extract authors, publication year, journal, and DOI/PMID.", ["Title page", "Header", "Bibliographic metadata"], "Use bibliographic metadata only.", ["authors", "publication_year", "journal", "doi_pmid"]),
    _question("TAN_1.3", "1. Reviewer context", "Record assessment date, reviewer, and pipeline version.", ["Reviewer metadata"], "This is pipeline metadata, not paper evidence.", ["assessment_date", "reviewer", "pipeline_version"]),

    _question("TAN_2.1.1", "2.1 Executive summary", "What is the specific scientific or regulatory rationale for conducting this PBPK analysis?", _PURPOSE_SECTIONS, "Use Abstract, the final Introduction objective paragraph, and Discussion/Conclusion summary only; block general Introduction background.", ["rationale", "purpose"]),
    _question("TAN_2.1.2", "2.1 Executive summary", "Provide a high-level overview of modeled chemicals, species, life stages/populations, exposure routes, and primary applications.", _PURPOSE_SECTIONS, "Use only purpose-summary sections; do not reconstruct scope from generic background.", ["model_overview", "chemicals", "species", "life_stages", "routes", "applications"]),
    _question("TAN_2.1.3", "2.1 Executive summary", "What primary quantitative and scientific conclusions are supported by the PBPK simulations?", _PURPOSE_SECTIONS, "Use only Abstract and Discussion/Conclusion model results; do not infer conclusions from model inputs.", ["key_conclusions", "quantitative_results"]),
    _question("TAN_2.3.1", "2.3 Model purpose", "What exact scientific, dosimetry, or regulatory questions does the model address, and what internal dose metrics are predicted?", _PURPOSE_SECTIONS + ["Methods: model purpose"], "Prefer explicit problem formulation/purpose statements; exclude generic exposure/toxicity history.", ["problem_formulation", "fit_for_purpose", "dose_metrics"]),

    _question("TAN_2.2.1", "2.2 & 2.4.2 Chemical properties and active moiety", "Which physicochemical and PK/TK properties are explicitly used in Methods to build or parameterize the model? Identify the modeled moiety and exposure routes.", _METHOD_SECTIONS, "Strictly exclude general toxicity/epidemiology background not used to parameterize, calibrate, or evaluate the model.", ["properties", "active_moiety", "exposure_routes", "parameter_use"]),
    _question("TAN_2.4.1", "2.4.1 Modeling strategy", "What is the end-to-end workflow from data preparation to model development, calibration/fitting, verification/evaluation, and application, and how does it support the purpose?", _METHOD_SECTIONS, "Use Materials/Methods/Tables/Figures; exclude generic Introduction.", ["workflow", "data_preparation", "development", "calibration", "evaluation", "application"]),
    _question("TAN_2.4.2A", "2.4.2 Data summary: parameterization studies", "Summarize specific in vitro, in silico, mass-balance, tissue-distribution, metabolism, transporter, and protein-binding studies used to inform structure or derive parameters.", _METHOD_SECTIONS, "Require study conditions and citations when reported; do not treat background citations as model data.", ["studies", "conditions", "species", "cell_fraction", "substrate", "software", "parameters_derived"]),
    _question("TAN_2.4.2B", "2.4.2 Calibration datasets", "List all datasets used to calibrate, optimize, or fit unknown parameters, including citation, species/population, matrix, sample size, dosing/exposure, and time points.", _METHOD_SECTIONS, "Only label a dataset calibration when the paper explicitly assigns that role.", ["datasets", "role", "citation", "species_population", "matrix", "sample_size", "dose", "time_points"]),
    _question("TAN_2.4.2C", "2.4.2 Evaluation datasets", "List independent datasets held out from calibration and used to evaluate predictive capability.", _METHOD_SECTIONS + ["Results"], "Only label a dataset independent when the paper explicitly distinguishes it from calibration.", ["datasets", "role", "citation", "species_population", "matrix", "sample_size", "time_points"]),

    _question("TAN_2.4.3.1", "2.4.3A Structure and lineage", "Does the model replicate, refine/modify a published model, or introduce a new structure? Describe and justify customized modifications and predecessor citations.", _STRUCTURE_SECTIONS, "Exclude Introduction; use Methods, schematic, Discussion limitations, and supplementary code.", ["lineage", "predecessor_citations", "modifications", "justification"]),
    _question("TAN_2.4.3.2", "2.4.3A Structure and platform", "For each species/life-stage submodel, list anatomical compartments, total count, platform, and inter-organ/inter-life-stage connectivity.", _STRUCTURE_SECTIONS, "Use diagrams and model-structure Methods; do not infer disconnected links.", ["platform", "submodels", "compartments", "count", "connections", "flows"]),
    _question("TAN_2.4.3.3", "2.4.3B ADME: absorption", "How does the model represent uptake across oral/GI, drinking water, breast milk, inhalation, dermal, IV, and presystemic routes?", _STRUCTURE_SECTIONS, "Extract mechanism, mathematical implementation, governing parameters/compartments, and exact source location.", ["biological_mechanism", "mathematical_implementation", "governing_parameters", "compartments", "source_location"]),
    _question("TAN_2.4.3.4", "2.4.3B ADME: binding and blood partitioning", "How are protein binding, free fraction, hematocrit, and blood-to-plasma partitioning represented?", _STRUCTURE_SECTIONS, "Extract mechanism, implementation, parameters/compartments, and exact source location.", ["biological_mechanism", "mathematical_implementation", "governing_parameters", "compartments", "source_location"]),
    _question("TAN_2.4.3.5", "2.4.3B ADME: tissue partitioning", "Which tissues are perfusion- versus diffusion-limited, how are partition coefficients determined, and how are dynamic physiological changes represented?", _STRUCTURE_SECTIONS, "Extract mechanism, implementation, parameters/compartments, and exact source location.", ["biological_mechanism", "mathematical_implementation", "governing_parameters", "compartments", "source_location"]),
    _question("TAN_2.4.3.6", "2.4.3B ADME: metabolism", "Is the compound metabolized or inert? If metabolized, identify organs, enzymes, rate laws, parent transformation, and metabolite formation.", _STRUCTURE_SECTIONS, "Extract mechanism, implementation, parameters/compartments, and exact source location.", ["biological_mechanism", "mathematical_implementation", "governing_parameters", "compartments", "source_location"]),
    _question("TAN_2.4.3.7", "2.4.3B ADME: excretion and recirculation", "How are urinary, biliary/fecal, exhaled, long-half-life, renal-reabsorption, and enterohepatic mechanisms represented, including life-stage differences?", _STRUCTURE_SECTIONS, "Extract mechanism, implementation, parameters/compartments, and exact source location.", ["biological_mechanism", "mathematical_implementation", "governing_parameters", "compartments", "source_location"]),
    _question("TAN_2.4.3.8", "2.4.3B ADME: barrier and life-stage transfer", "For gestational/lactational/barrier models, extract placental, amniotic, milk, and suckling-transfer mechanisms and equations.", _STRUCTURE_SECTIONS, "Use model structure, schematic, and Methods only; mark not_applicable only when explicitly established.", ["biological_mechanism", "mathematical_implementation", "governing_parameters", "compartments", "source_location"]),
    _question("TAN_2.4.3.9", "2.4.3C Assumptions: perfusion/diffusion/lumping", "What assumptions concern well-stirred behavior, organ lumping, or omitted compartments, and what are the justification and structural/equation impacts?", _STRUCTURE_SECTIONS, "Extract explicit assumptions only; do not supply textbook assumptions.", ["stated_assumption", "authors_justification", "structural_impact", "source_location"]),
    _question("TAN_2.4.3.10", "2.4.3C Assumptions: binding/free fraction", "What assumptions concern protein/RBC binding and constancy of fu/Free across concentration, species, or life stage?", _STRUCTURE_SECTIONS, "Extract explicit assumptions only with justification and model impact.", ["stated_assumption", "authors_justification", "structural_impact", "source_location"]),
    _question("TAN_2.4.3.11", "2.4.3C Assumptions: borrowing", "Which parameters are borrowed across surrogate species or analogue chemicals, and why?", _STRUCTURE_SECTIONS, "Do not infer borrowing from similar values; require explicit evidence.", ["stated_assumption", "authors_justification", "structural_impact", "source_location"]),
    _question("TAN_2.4.3.12", "2.4.3C Assumptions: clearance/resorption/ontogeny", "What assumptions concern zero metabolism, active renal reabsorption, or immature/omitted transporter activity in fetuses/infants?", _STRUCTURE_SECTIONS, "Extract explicit assumptions only with justification and model impact.", ["stated_assumption", "authors_justification", "structural_impact", "source_location"]),
    _question("TAN_2.4.3.13", "2.4.3C Assumptions: dosing/steady state", "What assumptions concern pre-pregnancy run-in, route surrogates, intake adjustments, or milk production/suckling initialization?", _STRUCTURE_SECTIONS, "Extract explicit assumptions only with justification and model impact.", ["stated_assumption", "authors_justification", "structural_impact", "source_location"]),

    _question("TAN_2.4.4", "2.4.4 Model equations", "Provide all extracted differential mass-balance, saturable transport/metabolism, dynamic growth, and allometric scaling equations.", ["Materials", "Methods", "Input parameter tables", "Table footnotes", "Supporting Information"], "Exclude sensitivity-output and reverse-dosimetry result tables from input equation extraction; never generate missing equations.", ["mass_balance_equations", "rate_equations", "growth_equations", "scaling_equations", "source_location"]),
    _question("TAN_2.4.5A", "2.4.5A Parameter tabulation and scaling", "Extract all physiological and chemical-specific input parameters from tables, footnotes, and Methods, including dynamic ranges, units, scaling, compound, species, and life stage.", ["Materials", "Methods", "Input parameter tables", "Table footnotes", "Supporting Information"], "Exclude sensitivity-output and reverse-dosimetry result tables from input parameters.", ["parameters", "dynamic_start_value", "dynamic_end_value", "units", "scaling", "context"]),
    _question("TAN_2.4.5B", "2.4.5B Parameter sources and competing values", "For each parameter, identify source category, original primary citation/location, competing values, chosen value, and rationale.", ["Materials", "Methods", "Input parameter tables", "Table footnotes", "Supporting Information"], "Prefer original primary citations over secondary citations; do not invent citations.", ["source_category", "original_citation", "competing_values", "chosen_value", "rationale"]),
    _question("TAN_2.4.5C", "2.4.5C Parameter distributions and uncertainty", "Extract probability distributions and bounds, or explain deterministic time-varying range/alternative-bound parameterization.", ["Materials", "Methods", "Input parameter tables", "Table footnotes", "Supporting Information"], "Do not confuse confidence intervals with dynamic physiological ranges.", ["distribution_type", "distribution_parameters", "bounds", "range_parameterization"]),
    _question("TAN_2.4.6A", "2.4.6A Exposure and dosing", "Extract all simulated exposure/dosing scenarios, routes, timing, duration, formulation, feeding/fasting, doses/concentrations, and intake rates.", ["Materials", "Methods", "Input parameter tables", "Supporting Information"], "Use model simulation conditions only; do not infer doses from general exposure history.", ["scenarios", "routes", "timing", "duration", "formulation", "dose", "intake_rates"]),
    _question("TAN_2.4.6B", "2.4.6B Samples, subjects, trials, and probabilistic setup", "Extract sample matrices/times, subject and virtual-population characteristics, number of trials/subjects, and Monte Carlo/MCMC iterations.", ["Materials", "Methods", "Results", "Supporting Information"], "Use explicit simulation/evaluation conditions only.", ["matrices", "collection_times", "subjects", "virtual_population", "trials", "iterations"]),
    _question("TAN_2.4.7", "2.4.7 Software and numerical solvers", "Extract software/version/product reference, ODE solver, interpolation, optimization/statistical algorithms, and code availability.", ["Materials", "Methods", "Supporting Information"], "Do not infer solver or code availability from software name alone.", ["software", "version", "website_manual", "solver", "interpolation", "optimization", "statistics", "code_available"]),

    _question("TAN_2.5.1A", "2.5.1A Evaluation: training versus validation", "Compare predictions with observed time-concentration data and distinguish calibration fit from independent predictive performance.", _EVAL_SECTIONS, "Use evaluation Methods, Results, Discussion, and evaluation figures/tables; preserve training/validation roles exactly.", ["training_comparison", "validation_comparison", "observations", "predictions", "limitations"]),
    _question("TAN_2.5.1B", "2.5.1B Goodness-of-fit and applicability", "Extract statistical tests, fold-error criteria, visual criteria, interpretation, applicability, and limitations.", _EVAL_SECTIONS, "Do not infer GOF from a graph unless the paper states the criterion.", ["metrics", "criteria", "visual_assessment", "applicability", "limitations"]),
    _question("TAN_2.5.2A", "2.5.2A Sensitivity protocol", "Extract local/global type, sampling approach, perturbation/time points/dose levels, mathematical method, and threshold criterion.", _EVAL_SECTIONS, "Use sensitivity Methods/Results and sensitivity figures/tables only.", ["analysis_type", "sampling", "perturbation", "time_points", "method", "criterion"]),
    _question("TAN_2.5.2B", "2.5.2B Sensitive parameters and uncertainty impact", "Summarize influential parameters and the overall impact of sensitivity, variability, and uncertainty on outputs and reliability.", _EVAL_SECTIONS, "Use explicit reported results; do not infer reliability from parameter magnitude.", ["key_parameters", "output_matrices", "overall_impact", "reliability"]),
]


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, ExtractedDocument):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return value
    return {}


def _nonempty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict, tuple, set)):
        return bool(value)
    return True


def _evidence(
    *,
    location: Optional[str] = None,
    quote: Optional[str] = None,
    page: Optional[int] = None,
    section: Optional[str] = None,
) -> EvidenceReference:
    return EvidenceReference(
        source_page=page,
        source_section=section,
        source_location=location,
        source_quote=quote,
    )


def _dedupe_evidence(items: List[EvidenceReference]) -> List[EvidenceReference]:
    result: List[EvidenceReference] = []
    seen: set[tuple[Any, ...]] = set()
    for item in items:
        key = (
            item.source_page,
            item.source_section,
            item.source_location,
            item.source_quote,
        )
        if key == (None, None, None, None) or key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _deterministic_confidence(
    response: ResponseOption,
    evidence: List[EvidenceReference],
) -> tuple[str, str]:
    """Derive confidence from evidence completeness, never from LLM opinion."""
    if response == ResponseOption.I_CANNOT_ANSWER:
        return "low", "The required model-specific evidence was not available."

    direct = [
        item
        for item in evidence
        if item.source_quote and (item.source_location or item.source_page is not None)
    ]
    quoted = [item for item in evidence if item.source_quote]
    located = [
        item
        for item in evidence
        if item.source_location or item.source_page is not None
    ]
    if direct:
        return "high", "At least one verbatim model-specific quote has a source location."
    if quoted or located:
        return "medium", "Structured or quoted evidence exists, but a fully located verbatim source quote is incomplete."
    return "low", "The response has no auditable model-specific evidence reference."


def _has_auditable_evidence(evidence: List[EvidenceReference]) -> bool:
    """Require a quote, concrete source location, or page—not a semantic tag."""
    return any(
        item.source_quote
        or item.source_location
        or item.source_page is not None
        for item in evidence
    )


def _context_evidence(document: dict[str, Any]) -> List[EvidenceReference]:
    context = document.get("model_context") or {}
    evidence: List[EvidenceReference] = []
    if context.get("source_quote") or context.get("source_location") or context.get("source_page") is not None:
        evidence.append(
            _evidence(
                location=context.get("source_location"),
                quote=context.get("source_quote"),
                page=context.get("source_page"),
            )
        )
    if context.get("stated_purpose") not in (None, "", "not_reported"):
        evidence.append(
            _evidence(
                quote=context.get("source_quote"),
                section="model context / purpose",
            )
        )
    return _dedupe_evidence(evidence)


def _biological_evidence(document: dict[str, Any]) -> List[EvidenceReference]:
    basis = document.get("biological_basis") or {}
    evidence: List[EvidenceReference] = []
    for determinant in basis.get("adme_determinant_evidence") or []:
        evidence.append(
            _evidence(
                location=determinant.get("source_location"),
                quote=determinant.get("evidence_quote"),
                page=determinant.get("source_page"),
                section="ADME determinant",
            )
        )
    for assumption in basis.get("stated_assumptions") or []:
        evidence.append(
            _evidence(
                location=assumption.get("source_location"),
                quote=assumption.get("evidence_quote"),
                page=assumption.get("source_page"),
                section="model assumption",
            )
        )
    return _dedupe_evidence(evidence)


def _parameter_evidence(document: dict[str, Any], limit: int = 6) -> List[EvidenceReference]:
    evidence: List[EvidenceReference] = []
    for parameter in (document.get("model_parameters") or [])[:limit]:
        provenance = parameter.get("provenance") or {}
        evidence.append(
            _evidence(
                page=provenance.get("source_page"),
                location=provenance.get("source_location") or provenance.get("source_table"),
                quote=provenance.get("source_quote"),
                section=provenance.get("source_section"),
            )
        )
    for table in (document.get("table_evidence") or [])[:limit]:
        evidence.append(
            _evidence(
                page=table.get("source_page"),
                location=table.get("table_id") or table.get("title"),
                section="parameter table",
            )
        )
    return _dedupe_evidence(evidence)


def _data_evidence(document: dict[str, Any], limit: int = 6) -> List[EvidenceReference]:
    evidence: List[EvidenceReference] = []
    for collection_name in ("observed_data", "simulated_data"):
        for record in (document.get(collection_name) or [])[:limit]:
            provenance = record.get("provenance") or {}
            evidence.append(
                _evidence(
                    page=provenance.get("source_page"),
                    location=provenance.get("source_location") or provenance.get("source_table"),
                    quote=provenance.get("source_quote"),
                    section=collection_name,
                )
            )
    return _dedupe_evidence(evidence)


def _sensitivity_evidence(document: dict[str, Any]) -> List[EvidenceReference]:
    evidence: List[EvidenceReference] = []
    for record in (document.get("sensitivity_analysis") or [])[:6]:
        provenance = record.get("provenance") or {}
        evidence.append(
            _evidence(
                page=provenance.get("source_page"),
                location=provenance.get("source_location") or provenance.get("source_table"),
                quote=provenance.get("source_quote"),
                section="sensitivity analysis",
            )
        )
    if document.get("extended_sensitivity"):
        evidence.append(_evidence(section="extended sensitivity metadata"))
    return _dedupe_evidence(evidence)


def _dosing_evidence(document: dict[str, Any]) -> List[EvidenceReference]:
    evidence: List[EvidenceReference] = []
    for event in (document.get("dosing") or [])[:6]:
        evidence.append(
            _evidence(
                quote=event.get("source_quote"),
                section="dosing event",
            )
        )
    return _dedupe_evidence(evidence)


def _evidence_summary(evidence: List[EvidenceReference]) -> str:
    if not evidence:
        return "No model-specific evidence was captured for this Tan item."
    locations = [item.source_location or item.source_section for item in evidence]
    locations = [str(item) for item in locations if item]
    return f"Evidence is available from: {', '.join(locations[:4])}."


def _make_item(
    definition: dict[str, Any],
    response: ResponseOption,
    details: str,
    evidence: Optional[List[EvidenceReference]] = None,
    structured_details: Optional[Dict[str, Any]] = None,
    require_evidence: bool = True,
) -> TanQuestionnaireItem:
    evidence = _dedupe_evidence(evidence or [])
    if require_evidence and response != ResponseOption.I_CANNOT_ANSWER and not _has_auditable_evidence(evidence):
        response = ResponseOption.I_CANNOT_ANSWER
        details = (
            "The extracted fact did not include a quote, page, or concrete source location; "
            "the item remains i_cannot_answer."
        )
    confidence, basis = _deterministic_confidence(response, evidence)
    return TanQuestionnaireItem(
        item_id=definition["item_id"],
        section=definition["section"],
        question=definition["question"],
        allowed_source_sections=definition.get("allowed_source_sections", []),
        routing_rule=definition.get("routing_rule"),
        response=response,
        details=details,
        structured_details=structured_details or {},
        evidence=evidence,
        confidence=confidence,
        confidence_basis=basis,
    )


def _has_parameters(document: dict[str, Any]) -> bool:
    return bool(document.get("model_parameters") or document.get("table_evidence"))


def _legacy_evaluate_tan_from_document(doc: Union[dict[str, Any], ExtractedDocument]) -> TanPBPKAssessment:
    """Legacy evaluator retained for compatibility; refined evaluator follows below."""
    document = _as_dict(doc)
    context = document.get("model_context") or {}
    basis = document.get("biological_basis") or {}
    structure = document.get("model_structure") or {}
    software = document.get("software") or {}
    reproducibility = document.get("reproducibility") or {}
    extended = document.get("extended_sensitivity") or {}
    parameters = document.get("model_parameters") or []
    observed = document.get("observed_data") or []
    simulated = document.get("simulated_data") or []
    dosing = document.get("dosing") or []
    sensitivity = document.get("sensitivity_analysis") or []
    data_evidence = _data_evidence(document)
    parameter_evidence = _parameter_evidence(document)
    biological_evidence = _biological_evidence(document)
    sensitivity_evidence = _sensitivity_evidence(document)
    dosing_evidence = _dosing_evidence(document)
    context_evidence = _context_evidence(document)

    by_id = {item["item_id"]: item for item in TAN_QUESTIONNAIRE_ITEMS}
    items: List[TanQuestionnaireItem] = []

    purpose_present = _nonempty(context.get("stated_purpose")) and context.get("stated_purpose") != "not_reported"
    items.append(_make_item(
        by_id["TAN_2.1_PURPOSE"],
        ResponseOption.YES if purpose_present else ResponseOption.I_CANNOT_ANSWER,
        "The extracted model context contains a stated purpose." if purpose_present else "A model-specific purpose was not captured.",
        context_evidence,
    ))

    items.append(_make_item(
        by_id["TAN_2.3_PURPOSE"],
        ResponseOption.YES if purpose_present and _nonempty(context.get("dose_metric")) else (ResponseOption.PARTIALLY if purpose_present else ResponseOption.I_CANNOT_ANSWER),
        "Model purpose and dose metric are both structured." if purpose_present and _nonempty(context.get("dose_metric")) else "Purpose evidence is incomplete or the chosen dose metric was not captured.",
        context_evidence,
    ))

    overview_present = bool(document.get("model_classification") and (_nonempty(structure) or parameters))
    items.append(_make_item(
        by_id["TAN_2.1_OVERVIEW"],
        ResponseOption.PARTIALLY if overview_present else ResponseOption.I_CANNOT_ANSWER,
        "Model classification and structural/parameter evidence provide a partial overview; a complete executive summary is not a factual extraction field." if overview_present else "No model-specific overview evidence was captured.",
        _dedupe_evidence(context_evidence + parameter_evidence),
    ))

    items.append(_make_item(
        by_id["TAN_2.1_CONCLUSIONS"],
        ResponseOption.I_CANNOT_ANSWER,
        "Research-paper conclusions are not inferred from generic Introduction/Background text and were not captured as a model-specific conclusion field.",
        [],
    ))

    strategy_present = bool(context.get("model_origin") or structure or basis.get("stated_assumptions"))
    items.append(_make_item(
        by_id["TAN_2.4.1_STRATEGY"],
        ResponseOption.PARTIALLY if strategy_present else ResponseOption.I_CANNOT_ANSWER,
        "Some model-development evidence is present, but a complete workflow from preparation through application is not represented." if strategy_present else "No model-development workflow was captured.",
        _dedupe_evidence(context_evidence + biological_evidence),
    ))

    items.append(_make_item(
        by_id["TAN_2.4.1_RELEVANCE"],
        ResponseOption.PARTIALLY if strategy_present and purpose_present else ResponseOption.I_CANNOT_ANSWER,
        "Purpose and some development evidence are present, but the strategy-to-purpose justification is not separately structured." if strategy_present and purpose_present else "No evidence links the modeling strategy to the stated purpose.",
        _dedupe_evidence(context_evidence + biological_evidence),
    ))

    role_values = [
        record.get("dataset_role")
        for record in observed + simulated
        if record.get("dataset_role")
    ]
    data_present = bool(role_values or observed or simulated or parameters)
    data_response = ResponseOption.YES if role_values else (ResponseOption.PARTIALLY if data_present else ResponseOption.I_CANNOT_ANSWER)
    items.append(_make_item(
        by_id["TAN_2.4.2_DATA"],
        data_response,
        "Dataset records and/or model parameters are present, with explicit calibration/evaluation roles only where extracted." if data_present else "No calibration or evaluation dataset evidence was captured.",
        _dedupe_evidence(data_evidence + parameter_evidence),
    ))

    chemical_exposure_present = bool(
        context.get("compound")
        or context.get("dose_metric")
        or context.get("target_populations")
        or dosing
        or parameters
        or document.get("mode_of_action")
    )
    items.append(_make_item(
        by_id["TAN_2.4.2_CHEMICAL_EXPOSURE"],
        ResponseOption.PARTIALLY if chemical_exposure_present else ResponseOption.I_CANNOT_ANSWER,
        "Some chemical, dose, population, or application fields are present; generic Introduction/Background statements were not used." if chemical_exposure_present else "No model-specific chemical or exposure context was captured.",
        _dedupe_evidence(context_evidence + parameter_evidence + dosing_evidence),
    ))

    calibration_records = [
        record for record in observed + simulated
        if str(record.get("dataset_role", "")).lower() == "calibration"
    ]
    evaluation_records = [
        record for record in observed + simulated
        if str(record.get("dataset_role", "")).lower() in {"independent_evaluation", "external_validation"}
    ]
    items.append(_make_item(
        by_id["TAN_2.4.2_CALIBRATION"],
        ResponseOption.YES if calibration_records else ResponseOption.I_CANNOT_ANSWER,
        "Calibration dataset role is explicitly present in extracted records." if calibration_records else "No explicitly labeled calibration dataset was captured.",
        data_evidence if calibration_records else [],
    ))
    items.append(_make_item(
        by_id["TAN_2.4.2_EVALUATION"],
        ResponseOption.YES if evaluation_records else ResponseOption.I_CANNOT_ANSWER,
        "Independent evaluation or external validation dataset role is explicitly present." if evaluation_records else "No explicitly labeled independent evaluation dataset was captured.",
        data_evidence if evaluation_records else [],
    ))

    adme_present = bool(
        basis.get("adme_determinants")
        or basis.get("adme_determinant_evidence")
        or document.get("metabolic_pathways")
        or document.get("mode_of_action")
    )
    items.append(_make_item(
        by_id["TAN_2.4.2_ADME"],
        ResponseOption.YES if basis.get("adme_determinant_evidence") else (ResponseOption.PARTIALLY if adme_present else ResponseOption.I_CANNOT_ANSWER),
        "ADME evidence is reported only when tied to extracted model-specific determinants or pathways; generic paper background is excluded." if adme_present else "No model-specific ADME evidence was captured.",
        biological_evidence,
    ))

    structure_present = bool(structure.get("compartments") or structure.get("connections") or context.get("model_origin"))
    structure_evidence = list(context_evidence)
    if structure:
        structure_evidence.append(
            _evidence(location=structure.get("source_location"), section="model structure")
        )
    items.append(_make_item(
        by_id["TAN_2.4.3_STRUCTURE"],
        ResponseOption.YES if structure.get("compartments") or structure.get("connections") else (ResponseOption.PARTIALLY if structure_present else ResponseOption.I_CANNOT_ANSWER),
        "The extracted document contains model structure evidence." if structure_present else "Model structure and its relationship to prior models were not captured.",
        _dedupe_evidence(structure_evidence),
    ))

    assumption_count = len(basis.get("stated_assumptions") or [])
    items.append(_make_item(
        by_id["TAN_2.4.3_ASSUMPTIONS"],
        ResponseOption.YES if assumption_count and biological_evidence else ResponseOption.I_CANNOT_ANSWER,
        f"{assumption_count} explicit assumption record(s) were extracted with evidence fields." if assumption_count else "No explicit, quote-backed model assumptions were captured; standard PBPK assumptions are not filled in by inference.",
        biological_evidence,
    ))

    prior_model_present = bool(
        context.get("model_origin")
        or context.get("original_application")
        or context.get("current_application")
        or context.get("repurposed") is not None
    )
    items.append(_make_item(
        by_id["TAN_2.4.3_PRIOR_MODEL"],
        ResponseOption.PARTIALLY if prior_model_present else ResponseOption.I_CANNOT_ANSWER,
        "Model origin/application metadata is present, but customized changes are not separately structured." if prior_model_present else "Model origin and customized changes were not captured.",
        context_evidence,
    ))

    equations_present = reproducibility.get("equations_available") is True or structure.get("equations_provided") in {"text", "supplementary_info", "code_repo"} or bool(structure.get("scaling_equations"))
    items.append(_make_item(
        by_id["TAN_2.4.4_EQUATIONS"],
        ResponseOption.YES if reproducibility.get("equations_available") is True else (ResponseOption.PARTIALLY if equations_present else ResponseOption.I_CANNOT_ANSWER),
        "Equation availability or symbolic scaling information is present; APEX does not generate equations that were not extracted." if equations_present else "Equation evidence was not captured.",
        [_evidence(location=structure.get("source_location"), section="model equations")] if equations_present else [],
    ))

    parameter_detail_count = sum(
        1
        for parameter in parameters
        if (parameter.get("parameter_name_original") or parameter.get("symbol_original"))
        and (parameter.get("quantitative_data") or {}).get("unit_original")
        and (parameter.get("provenance") or {}).get("source_table")
    )
    items.append(_make_item(
        by_id["TAN_2.4.5_PARAMETERS"],
        ResponseOption.YES if parameter_detail_count and parameter_detail_count == len(parameters) else (ResponseOption.PARTIALLY if parameters else ResponseOption.I_CANNOT_ANSWER),
        f"{parameter_detail_count} of {len(parameters)} extracted parameters contain name, unit, and table provenance." if parameters else "No model parameter records were captured.",
        parameter_evidence,
    ))

    distribution_present = bool(
        extended.get("uncertainty_distributions")
        or any((parameter.get("quantitative_data") or {}).get("uncertainty") for parameter in parameters)
        or (structure.get("allometric_scaling_rules") or structure.get("scaling_equations"))
    )
    items.append(_make_item(
        by_id["TAN_2.4.5_DISTRIBUTIONS"],
        ResponseOption.PARTIALLY if distribution_present else ResponseOption.I_CANNOT_ANSWER,
        "Uncertainty/distribution or scaling information is present, but full distribution parameters are not assumed unless extracted." if distribution_present else "No parameter distribution, uncertainty-distribution, or scaling evidence was captured.",
        _dedupe_evidence(parameter_evidence + ([_evidence(location="model structure", section="allometric scaling")] if structure.get("allometric_scaling_rules") or structure.get("scaling_equations") else [])),
    ))

    simulation_present = bool(dosing or observed or simulated)
    simulation_detail = bool(dosing and (observed or simulated))
    items.append(_make_item(
        by_id["TAN_2.4.6_SIMULATIONS"],
        ResponseOption.YES if simulation_detail else (ResponseOption.PARTIALLY if simulation_present else ResponseOption.I_CANNOT_ANSWER),
        "Dosing and/or observed/simulated data are available, but completeness of all Tan simulation conditions is assessed only from extracted fields." if simulation_present else "No dosing or simulation-condition evidence was captured.",
        _dedupe_evidence(data_evidence + dosing_evidence),
    ))

    items.append(_make_item(
        by_id["TAN_2.4.6_EXPOSURE"],
        ResponseOption.YES if dosing else ResponseOption.I_CANNOT_ANSWER,
        "Dosing records contain extracted administration conditions." if dosing else "No dosing/exposure-condition record was captured.",
        dosing_evidence,
    ))

    population_present = bool(
        context.get("target_populations")
        or context.get("age_groups")
        or context.get("life_stages")
        or context.get("sex_or_gender")
        or context.get("health_status")
        or any((parameter.get("context") or {}).get("species") for parameter in parameters)
    )
    items.append(_make_item(
        by_id["TAN_2.4.6_POPULATION"],
        ResponseOption.PARTIALLY if population_present else ResponseOption.I_CANNOT_ANSWER,
        "Some subject or population characteristics are structured." if population_present else "Subject and virtual-population characteristics were not captured.",
        _dedupe_evidence(context_evidence + parameter_evidence),
    ))

    probabilistic_present = bool(
        extended.get("sampling_approach")
        or extended.get("iterations")
        or extended.get("analysis_type") in {"global", "both"}
    )
    items.append(_make_item(
        by_id["TAN_2.4.6_PROBABILISTIC"],
        ResponseOption.YES if extended.get("sampling_approach") and extended.get("iterations") else (ResponseOption.PARTIALLY if probabilistic_present else ResponseOption.I_CANNOT_ANSWER),
        "Probabilistic simulation metadata is present." if probabilistic_present else "No probabilistic simulation method or iteration count was captured.",
        sensitivity_evidence if probabilistic_present else [],
    ))

    software_fields = [software.get("name"), software.get("version"), software.get("solver"), software.get("optimization_method"), software.get("statistical_methods")]
    software_count = sum(_nonempty(value) for value in software_fields)
    software_provenance = software.get("provenance") or {}
    items.append(_make_item(
        by_id["TAN_2.4.7_SOFTWARE"],
        ResponseOption.YES if software_count >= 4 else (ResponseOption.PARTIALLY if software_count else ResponseOption.I_CANNOT_ANSWER),
        f"{software_count} software/solver fields are populated." if software_count else "Software and numerical algorithm evidence was not captured.",
        [_evidence(
            location=software_provenance.get("source_location") or software_provenance.get("source_table"),
            quote=software.get("source_quote") or software_provenance.get("source_quote"),
            section="software",
        )] if software_count else [],
    ))

    evaluation_present = bool(observed and simulated)
    items.append(_make_item(
        by_id["TAN_2.5.1_EVALUATION"],
        ResponseOption.YES if evaluation_present else (ResponseOption.PARTIALLY if observed or simulated else ResponseOption.I_CANNOT_ANSWER),
        "Observed and simulated records are both present for comparison." if evaluation_present else "Only partial or no observed-versus-simulated evidence was captured.",
        data_evidence,
    ))

    independence_values = [
        str(record.get("independence_status", "")).lower()
        for record in observed + simulated
        if record.get("independence_status")
    ]
    independence_present = bool(independence_values)
    independence_yes = any(value == "independent" for value in independence_values)
    items.append(_make_item(
        by_id["TAN_2.5.1_INDEPENDENCE"],
        ResponseOption.YES if independence_yes else (ResponseOption.PARTIALLY if independence_present else ResponseOption.I_CANNOT_ANSWER),
        "Dataset independence metadata is explicitly present." if independence_present else "Calibration/evaluation independence was not explicitly captured.",
        data_evidence if independence_present else [],
    ))

    gof_terms = {"aafe", "rmse", "r2", "r^2", "r_squared", "mfe", "visual predictive check", "goodness-of-fit"}
    gof_present = any(any(term in str(record.get("metric", "")).lower() for term in gof_terms) for record in observed + simulated)
    items.append(_make_item(
        by_id["TAN_2.5.1_GOODNESS_OF_FIT"],
        ResponseOption.YES if gof_present else ResponseOption.I_CANNOT_ANSWER,
        "Goodness-of-fit terminology is present in extracted evaluation records." if gof_present else "No explicit goodness-of-fit metric or criterion was captured.",
        data_evidence if gof_present else [],
    ))

    sensitivity_present = bool(sensitivity or extended)
    items.append(_make_item(
        by_id["TAN_2.5.2_SENSITIVITY"],
        ResponseOption.YES if sensitivity and (extended.get("criterion") or any(record.get("criterion") for record in sensitivity)) else (ResponseOption.PARTIALLY if sensitivity_present else ResponseOption.I_CANNOT_ANSWER),
        "Sensitivity records or extended sensitivity metadata are present; criteria are rated only when explicitly extracted." if sensitivity_present else "No sensitivity-analysis evidence was captured.",
        sensitivity_evidence,
    ))

    uncertainty_present = bool(
        extended.get("uncertainty_distributions")
        or extended.get("individual_variability_modeled") is not None
        or extended.get("experimental_reproducibility")
        or any((record.get("quantitative_data") or {}).get("uncertainty") for record in parameters)
    )
    items.append(_make_item(
        by_id["TAN_2.5.2_UNCERTAINTY"],
        ResponseOption.YES if extended.get("uncertainty_distributions") or extended.get("individual_variability_modeled") is True else (ResponseOption.PARTIALLY if uncertainty_present else ResponseOption.I_CANNOT_ANSWER),
        "Parameter uncertainty or variability metadata is present." if uncertainty_present else "No explicit uncertainty, reproducibility, or biological-variability analysis was captured.",
        _dedupe_evidence(parameter_evidence + sensitivity_evidence),
    ))

    impact_present = bool(
        extended.get("key_sensitive_parameters")
        or extended.get("overall_impact_on_dose_metric")
        or extended.get("experimental_reproducibility")
    )
    items.append(_make_item(
        by_id["TAN_2.5.2_IMPACT"],
        ResponseOption.YES if extended.get("key_sensitive_parameters") and extended.get("overall_impact_on_dose_metric") else (ResponseOption.PARTIALLY if impact_present else ResponseOption.I_CANNOT_ANSWER),
        "Key sensitive parameters or overall impact metadata is present." if impact_present else "No explicit overall impact or key-parameter summary was captured.",
        sensitivity_evidence if impact_present else [],
    ))

    applicability_present = bool(
        context.get("model_origin")
        or context.get("stated_purpose")
        or context.get("dose_metric")
        or document.get("table_evidence")
    )
    items.append(_make_item(
        by_id["TAN_2.5.2_APPLICABILITY"],
        ResponseOption.PARTIALLY if applicability_present else ResponseOption.I_CANNOT_ANSWER,
        "Some applicability context is structured, but a complete fit-for-purpose and analogue justification is not assumed from generic background text." if applicability_present else "Applicability evidence was not captured.",
        _dedupe_evidence(context_evidence + parameter_evidence),
    ))

    cannot_count = sum(item.response == ResponseOption.I_CANNOT_ANSWER for item in items)
    key_gaps = [
        f"{item.item_id}: model-specific evidence not captured"
        for item in items
        if item.response == ResponseOption.I_CANNOT_ANSWER
    ]
    fit = (
        f"Tan questionnaire: {len(items) - cannot_count}/{len(items)} items have at least some structured evidence; "
        f"{cannot_count}/{len(items)} require source review."
    )
    return TanPBPKAssessment(
        items=items,
        overall_fit_for_purpose=fit,
        key_gaps=key_gaps,
        reviewer_notes=[
            "Generic Introduction/Background prose was excluded from model evidence.",
            "Confidence levels were calculated from evidence references by deterministic APEX rules.",
        ],
    )


def _definition_evidence(document: dict[str, Any], item_id: str) -> List[EvidenceReference]:
    """Collect auditable evidence relevant to a refined Tan item."""
    context = document.get("model_context") or {}
    basis = document.get("biological_basis") or {}
    structure = document.get("model_structure") or {}
    evidence: List[EvidenceReference] = []

    if item_id in {"TAN_1.1", "TAN_1.2"}:
        metadata = document.get("page_metadata") or {}
        quote = metadata.get("title") or metadata.get("journal")
        if quote:
            evidence.append(_evidence(quote=str(quote), section="bibliographic metadata"))
        evidence.extend(_parameter_evidence(document, limit=2))
    elif item_id in {"TAN_1.3"}:
        return []
    elif item_id in {"TAN_2.1.1", "TAN_2.1.2", "TAN_2.1.3", "TAN_2.3.1"}:
        evidence.extend(_context_evidence(document))
        evidence.extend(_data_evidence(document, limit=2))
    elif item_id == "TAN_2.2.1":
        evidence.extend(_parameter_evidence(document))
        evidence.extend(_context_evidence(document))
    elif item_id in {"TAN_2.4.1", "TAN_2.4.3.1", "TAN_2.4.3.2"}:
        evidence.extend(_context_evidence(document))
        if structure:
            evidence.append(_evidence(location=structure.get("source_location"), section="model structure"))
        evidence.extend(_biological_evidence(document))
    elif item_id in {"TAN_2.4.2A", "TAN_2.4.5A", "TAN_2.4.5B", "TAN_2.4.5C"}:
        evidence.extend(_parameter_evidence(document, limit=8))
    elif item_id in {"TAN_2.4.2B", "TAN_2.4.2C", "TAN_2.5.1A", "TAN_2.5.1B"}:
        evidence.extend(_data_evidence(document, limit=8))
    elif item_id.startswith("TAN_2.4.3."):
        suffix = item_id.rsplit(".", 1)[-1]
        if suffix in {"3", "4", "5", "6", "7", "8"}:
            phase_map = {
                "3": "absorption",
                "4": "distribution_binding",
                "5": "distribution_tissue",
                "6": "metabolism",
                "7": "excretion_recirculation",
                "8": "barrier_life_stage_transfer",
            }
            for phase in basis.get("adme_phase_evidence") or []:
                if phase.get("phase") == phase_map[suffix]:
                    evidence.append(_evidence(
                        page=phase.get("source_page"),
                        location=phase.get("source_location"),
                        quote=phase.get("evidence_quote"),
                        section=f"ADME {phase_map[suffix]}",
                    ))
        else:
            for assumption in basis.get("assumption_evidence") or []:
                evidence.append(_evidence(
                    page=assumption.get("source_page"),
                    location=assumption.get("source_location"),
                    quote=assumption.get("evidence_quote"),
                    section="model assumption",
                ))
            evidence.extend(_biological_evidence(document))
    elif item_id == "TAN_2.4.4":
        if structure:
            evidence.append(_evidence(location=structure.get("source_location"), section="model equations"))
    elif item_id in {"TAN_2.4.6A", "TAN_2.4.6B"}:
        evidence.extend(_dosing_evidence(document))
        evidence.extend(_data_evidence(document, limit=5))
        evidence.extend(_context_evidence(document))
    elif item_id == "TAN_2.4.7":
        software = document.get("software") or {}
        provenance = software.get("provenance") or {}
        evidence.append(_evidence(
            location=provenance.get("source_location") or provenance.get("source_table"),
            quote=software.get("source_quote") or provenance.get("source_quote"),
            section="software",
        ))
    elif item_id in {"TAN_2.5.2A", "TAN_2.5.2B"}:
        evidence.extend(_sensitivity_evidence(document))
    return _dedupe_evidence(evidence)


def _structured_details_for_item(document: dict[str, Any], item_id: str) -> Dict[str, Any]:
    basis = document.get("biological_basis") or {}
    context = document.get("model_context") or {}
    structure = document.get("model_structure") or {}
    if item_id.startswith("TAN_2.4.3."):
        suffix = item_id.rsplit(".", 1)[-1]
        if suffix in {"3", "4", "5", "6", "7", "8"}:
            phase_map = {"3": "absorption", "4": "distribution_binding", "5": "distribution_tissue", "6": "metabolism", "7": "excretion_recirculation", "8": "barrier_life_stage_transfer"}
            return {"phase": next((p for p in basis.get("adme_phase_evidence", []) if p.get("phase") == phase_map[suffix]), {})}
        categories = {"9": "tissue_perfusion_diffusion_lumping", "10": "protein_binding_free_fraction", "11": "cross_species_cross_chemical_borrowing", "12": "clearance_resorption_ontogeny", "13": "dosing_exposure_steady_state"}
        return {"assumptions": [a for a in basis.get("assumption_evidence", []) if a.get("category") == categories.get(suffix)]}
    if item_id in {"TAN_2.1.1", "TAN_2.1.2", "TAN_2.1.3", "TAN_2.3.1"}:
        return {"model_context": context}
    if item_id == "TAN_2.4.3.2":
        return {"model_structure": structure}
    if item_id == "TAN_2.4.4":
        return {"equations": structure.get("scaling_equations", []), "scaling_rules": structure.get("allometric_scaling_rules", [])}
    if item_id in {"TAN_2.5.2A", "TAN_2.5.2B"}:
        return {"extended_sensitivity": document.get("extended_sensitivity") or {}, "coefficients": document.get("sensitivity_analysis") or []}
    return {}


def evaluate_tan_from_document(
    doc: Union[dict[str, Any], ExtractedDocument],
    *,
    verification_summary: Optional[Dict[str, Any]] = None,
) -> TanPBPKAssessment:
    """Create the refined 36-item Tan questionnaire deterministically."""
    document = _as_dict(doc)
    parameters = document.get("model_parameters") or []
    context = document.get("model_context") or {}
    basis = document.get("biological_basis") or {}
    structure = document.get("model_structure") or {}
    observed = document.get("observed_data") or []
    simulated = document.get("simulated_data") or []
    dosing = document.get("dosing") or []
    software = document.get("software") or {}
    extended = document.get("extended_sensitivity") or {}
    sensitivity = document.get("sensitivity_analysis") or []
    items: List[TanQuestionnaireItem] = []

    for definition in TAN_QUESTIONNAIRE_ITEMS:
        item_id = definition["item_id"]
        evidence = _definition_evidence(document, item_id)
        details = "No model-specific evidence was captured for this refined Tan item."
        response = ResponseOption.I_CANNOT_ANSWER
        structured = _structured_details_for_item(document, item_id)
        require_evidence = item_id != "TAN_1.3"

        if item_id == "TAN_1.3":
            response = ResponseOption.YES
            details = "Assessment metadata is assigned by the pipeline."
        elif item_id in {"TAN_1.1", "TAN_1.2"}:
            response = ResponseOption.PARTIALLY if evidence else ResponseOption.I_CANNOT_ANSWER
            details = "Bibliographic/model identification evidence is available." if evidence else details
        elif item_id in {"TAN_2.1.1", "TAN_2.1.2", "TAN_2.3.1"}:
            present = bool(context.get("stated_purpose") and context.get("source_quote"))
            response = ResponseOption.YES if present else (ResponseOption.PARTIALLY if evidence else ResponseOption.I_CANNOT_ANSWER)
            details = "Purpose evidence is linked to a model-specific context quote." if present else "Purpose evidence is incomplete or not explicitly routed to an allowed section."
        elif item_id == "TAN_2.1.3":
            response = ResponseOption.I_CANNOT_ANSWER
            details = "Key conclusions require an Abstract/Discussion/Conclusion extraction; they are not inferred from parameters."
        elif item_id == "TAN_2.2.1":
            response = ResponseOption.PARTIALLY if parameters else ResponseOption.I_CANNOT_ANSWER
            details = "Model parameter records provide partial model-relevant property evidence." if parameters else details
        elif item_id in {"TAN_2.4.1", "TAN_2.4.3.1"}:
            present = bool(context.get("model_origin") or structure or basis.get("stated_assumptions"))
            response = ResponseOption.PARTIALLY if present else ResponseOption.I_CANNOT_ANSWER
            details = "Model-development evidence is present, but completeness depends on routed Methods/Discussion evidence." if present else details
        elif item_id == "TAN_2.4.2A":
            present = bool(parameters or document.get("metabolic_pathways"))
            response = ResponseOption.PARTIALLY if present else ResponseOption.I_CANNOT_ANSWER
            details = "Parameter/pathway records are present; experimental conditions are only reported when extracted." if present else details
        elif item_id in {"TAN_2.4.2B", "TAN_2.4.2C"}:
            roles = [str(r.get("dataset_role", "")).lower() for r in observed + simulated]
            role = "calibration" if item_id.endswith("B") else "independent_evaluation"
            present = role in roles or (role == "independent_evaluation" and "external_validation" in roles)
            response = ResponseOption.YES if present else ResponseOption.I_CANNOT_ANSWER
            details = "Dataset role is explicitly labeled in the extracted records." if present else "The requested dataset role was not explicitly captured."
        elif item_id == "TAN_2.4.3.2":
            present = bool(structure.get("compartments") or structure.get("connections"))
            response = ResponseOption.YES if present else ResponseOption.I_CANNOT_ANSWER
            details = "Compartment/connectivity evidence is structured." if present else details
        elif item_id.startswith("TAN_2.4.3."):
            response = ResponseOption.YES if structured.get("phase") or structured.get("assumptions") else ResponseOption.I_CANNOT_ANSWER
            details = "Mechanistic/assumption evidence is structured by phase/category." if response == ResponseOption.YES else "No explicit phase-specific mechanism or categorized assumption was captured."
        elif item_id == "TAN_2.4.4":
            present = bool(structure.get("scaling_equations") or structure.get("allometric_scaling_rules") or structure.get("equations_provided") not in (None, "none"))
            response = ResponseOption.PARTIALLY if present else ResponseOption.I_CANNOT_ANSWER
            details = "Extracted equations/scaling evidence is present; missing equations are not generated." if present else details
        elif item_id == "TAN_2.4.5A":
            response = ResponseOption.YES if parameters else ResponseOption.I_CANNOT_ANSWER
            details = f"{len(parameters)} canonical parameter records are available." if parameters else details
        elif item_id == "TAN_2.4.5B":
            sourced = sum(bool((p.get("provenance") or {}).get("reference")) for p in parameters)
            response = ResponseOption.YES if parameters and sourced == len(parameters) else (ResponseOption.PARTIALLY if sourced else ResponseOption.I_CANNOT_ANSWER)
            details = f"{sourced}/{len(parameters)} parameters contain an original reference field." if parameters else details
        elif item_id == "TAN_2.4.5C":
            present = bool(extended.get("uncertainty_distributions") or any((p.get("quantitative_data") or {}).get("uncertainty") for p in parameters))
            response = ResponseOption.PARTIALLY if present else ResponseOption.I_CANNOT_ANSWER
            details = "Uncertainty/range evidence is present; distribution details are not inferred." if present else details
        elif item_id == "TAN_2.4.6A":
            response = ResponseOption.YES if dosing else ResponseOption.I_CANNOT_ANSWER
            details = "Dosing events are extracted from model methods." if dosing else details
        elif item_id == "TAN_2.4.6B":
            present = bool(observed or simulated or context.get("target_populations") or context.get("life_stages"))
            response = ResponseOption.PARTIALLY if present else ResponseOption.I_CANNOT_ANSWER
            details = "Sample/population/simulation records are partially available." if present else details
        elif item_id == "TAN_2.4.7":
            fields = [software.get(k) for k in ("name", "version", "solver", "optimization_method", "statistical_methods")]
            response = ResponseOption.YES if sum(_nonempty(v) for v in fields) >= 4 else (ResponseOption.PARTIALLY if any(_nonempty(v) for v in fields) else ResponseOption.I_CANNOT_ANSWER)
            details = "Software metadata is partially or fully populated." if response != ResponseOption.I_CANNOT_ANSWER else details
        elif item_id == "TAN_2.5.1A":
            present = bool(observed and simulated)
            response = ResponseOption.YES if present else (ResponseOption.PARTIALLY if observed or simulated else ResponseOption.I_CANNOT_ANSWER)
            details = "Observed and simulated records are available for comparison." if present else "Observed/simulated comparison is incomplete."
        elif item_id == "TAN_2.5.1B":
            gof = any(any(term in str(r.get("metric", "")).lower() for term in ("aafe", "rmse", "r2", "r^2", "mfe", "goodness")) for r in observed + simulated)
            response = ResponseOption.YES if gof else ResponseOption.I_CANNOT_ANSWER
            details = "An explicit GOF metric/criterion was captured." if gof else "No explicit GOF metric or criterion was captured."
        elif item_id == "TAN_2.5.2A":
            present = bool(sensitivity or extended)
            response = ResponseOption.PARTIALLY if present else ResponseOption.I_CANNOT_ANSWER
            details = "Sensitivity metadata is present; protocol fields are rated only when explicitly extracted." if present else details
        elif item_id == "TAN_2.5.2B":
            present = bool(extended.get("key_sensitive_parameters") or extended.get("overall_impact_on_dose_metric") or sensitivity)
            response = ResponseOption.PARTIALLY if present else ResponseOption.I_CANNOT_ANSWER
            details = "Sensitive parameters or impact metadata is present." if present else details

        items.append(_make_item(definition, response, details, evidence, structured, require_evidence=require_evidence))

    model_metadata = {
        "model_name": (document.get("page_metadata") or {}).get("title"),
        "target_compounds": sorted({str(c) for t in document.get("table_evidence", []) for c in t.get("subject_compounds", [])}),
        "authors": (document.get("page_metadata") or {}).get("authors"),
        "publication_year": (document.get("page_metadata") or {}).get("year"),
        "journal": (document.get("page_metadata") or {}).get("journal"),
    }
    cannot_count = sum(item.response == ResponseOption.I_CANNOT_ANSWER for item in items)
    return TanPBPKAssessment(
        template_name="Refined TAN et al. PBPK Model Evaluation & Extraction Questionnaire",
        template_version="Refined-Tan-PBPK-Research-v1",
        assessment_scope="Strict section routing: Introduction background is excluded; only the final objective paragraph may support purpose items.",
        assessment_date=None,
        model_identification=model_metadata,
        items=items,
        verification_summary=verification_summary or document.get("parameter_verification_summary") or {},
        overall_fit_for_purpose=f"{len(items) - cannot_count}/{len(items)} refined Tan items have at least some supported evidence; {cannot_count}/{len(items)} remain i_cannot_answer.",
        key_gaps=[f"{item.item_id}: model-specific evidence not captured or incomplete" for item in items if item.response == ResponseOption.I_CANNOT_ANSWER],
        reviewer_notes=["Generic Introduction/background prose was excluded except for a final study-objective paragraph.", "Confidence is deterministic and parameter verification uses four post-extraction checks."],
    )


def normalize_tan_assessment(
    raw: Union[dict[str, Any], TanPBPKAssessment],
    document: Optional[Union[dict[str, Any], ExtractedDocument]] = None,
) -> TanPBPKAssessment:
    """Validate an LLM response and enforce complete, evidence-grounded items."""
    if isinstance(raw, TanPBPKAssessment):
        assessment = raw
    else:
        assessment = TanPBPKAssessment.model_validate(raw)

    raw_by_id = {item.item_id: item for item in assessment.items}
    normalized: List[TanQuestionnaireItem] = []
    for definition in TAN_QUESTIONNAIRE_ITEMS:
        source = raw_by_id.get(definition["item_id"])
        if source is None:
            source = TanQuestionnaireItem(
                item_id=definition["item_id"],
                section=definition["section"],
                question=definition["question"],
                allowed_source_sections=definition.get("allowed_source_sections", []),
                routing_rule=definition.get("routing_rule"),
                response=ResponseOption.I_CANNOT_ANSWER,
                details="The LLM did not return this Tan questionnaire item.",
                evidence=[],
            )
        evidence = _dedupe_evidence(source.evidence)
        response = source.response
        details = source.details
        requires_evidence = definition["item_id"] != "TAN_1.3"
        if requires_evidence and response != ResponseOption.I_CANNOT_ANSWER and not _has_auditable_evidence(evidence):
            response = ResponseOption.I_CANNOT_ANSWER
            details = (
                "The returned rating had no auditable model-specific evidence; "
                "APEX changed it to i_cannot_answer."
            )
        confidence, basis = _deterministic_confidence(response, evidence)
        normalized.append(
            TanQuestionnaireItem(
                item_id=definition["item_id"],
                section=definition["section"],
                question=definition["question"],
                allowed_source_sections=definition.get("allowed_source_sections", []),
                routing_rule=definition.get("routing_rule"),
                response=response,
                details=details,
                structured_details=source.structured_details,
                evidence=evidence,
                confidence=confidence,
                confidence_basis=basis,
            )
        )

    cannot_count = sum(item.response == ResponseOption.I_CANNOT_ANSWER for item in normalized)
    gaps = list(dict.fromkeys(list(assessment.key_gaps) + [
        f"{item.item_id}: model-specific evidence not sufficient for a supported rating"
        for item in normalized
        if item.response == ResponseOption.I_CANNOT_ANSWER
    ]))
    return TanPBPKAssessment(
        template_name=assessment.template_name,
        template_version=assessment.template_version,
        assessment_date=assessment.assessment_date,
        reviewer=assessment.reviewer,
        pipeline_version=assessment.pipeline_version,
        model_identification=assessment.model_identification,
        assessment_scope=(
            "Model-specific evidence only; generic Introduction/Background statements are excluded unless explicitly tied to the model."
        ),
        items=normalized,
        verification_summary=assessment.verification_summary,
        overall_fit_for_purpose=(
            f"{len(normalized) - cannot_count}/{len(normalized)} Tan items have an evidence-backed rating; "
            f"{cannot_count}/{len(normalized)} remain i_cannot_answer."
        ),
        key_gaps=gaps,
        reviewer_notes=list(dict.fromkeys(assessment.reviewer_notes + [
            "Confidence was recalculated by APEX from evidence completeness; the LLM confidence value was not trusted.",
        ])),
    )


def normalize_biological_basis(document: dict[str, Any]) -> None:
    """Assign evidence quality to ADME determinants and assumptions in place.

    This is deliberately separate from the LLM extraction step.  The model may
    propose a statement, but only the presence of a quote and source location
    controls the final evidence confidence.
    """
    basis = document.get("biological_basis")
    if not isinstance(basis, dict):
        return

    evidence_scores: List[int] = []

    determinants = basis.get("adme_determinant_evidence") or []
    for determinant in determinants:
        if not isinstance(determinant, dict):
            continue
        quote = str(determinant.get("evidence_quote") or "").strip()
        location = str(determinant.get("source_location") or "").strip()
        directness = determinant.get("evidence_directness") or "explicit"
        if directness != "explicit":
            confidence = "low"
            score = 0
        elif quote and location:
            confidence = "high"
            score = 2
        elif quote or location:
            confidence = "medium"
            score = 1
        else:
            confidence = "low"
            score = 0
        determinant["evidence_confidence"] = confidence
        evidence_scores.append(score)

    assumptions = basis.get("stated_assumptions") or []
    for assumption in assumptions:
        if not isinstance(assumption, dict):
            continue
        quote = str(assumption.get("evidence_quote") or "").strip()
        location = str(assumption.get("source_location") or "").strip()
        directness = assumption.get("evidence_directness") or "explicit"
        if directness != "explicit":
            confidence = "low"
            score = 0
        elif quote and location:
            confidence = "high"
            score = 2
        elif quote or location:
            confidence = "medium"
            score = 1
        else:
            confidence = "low"
            score = 0
        assumption["evidence_confidence"] = confidence
        evidence_scores.append(score)

    for record in (basis.get("adme_phase_evidence") or []) + (basis.get("assumption_evidence") or []):
        if not isinstance(record, dict):
            continue
        quote = str(record.get("evidence_quote") or "").strip()
        location = str(record.get("source_location") or "").strip()
        directness = record.get("evidence_directness") or "explicit"
        if directness != "explicit":
            confidence = "low"
            score = 0
        elif quote and location:
            confidence = "high"
            score = 2
        elif quote or location:
            confidence = "medium"
            score = 1
        else:
            confidence = "low"
            score = 0
        record["evidence_confidence"] = confidence
        evidence_scores.append(score)

    if evidence_scores and min(evidence_scores) == 2:
        basis["evidence_confidence"] = "high"
        basis["confidence_basis"] = "All extracted ADME/assumption records have explicit quotes and source locations."
    elif any(score > 0 for score in evidence_scores):
        basis["evidence_confidence"] = "medium"
        basis["confidence_basis"] = "Some extracted ADME/assumption records have quote or location evidence, but coverage is incomplete."
    else:
        basis["evidence_confidence"] = "low"
        basis["confidence_basis"] = "No complete quote-and-location evidence was available for the extracted ADME/assumption records."


def _verification_text(value: Any) -> str:
    text = str(value or "")
    text = text.replace("−", "-").replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", "", text).casefold()


def _parameter_source_text(parameter: dict[str, Any], document: dict[str, Any]) -> str:
    provenance = parameter.get("provenance") or {}
    parts = [
        provenance.get("source_quote"),
        provenance.get("source_table"),
        " ".join(provenance.get("row_path") or []),
        " ".join(provenance.get("column_path") or []),
    ]
    table_id = provenance.get("source_table")
    cell_id = provenance.get("cell_id")
    for table in document.get("table_evidence") or []:
        if table_id and table.get("table_id") != table_id:
            continue
        for cell in table.get("cells") or []:
            if cell_id and cell.get("cell_id") != cell_id:
                continue
            if provenance.get("row_id") and cell.get("row_id") != provenance.get("row_id"):
                continue
            if provenance.get("column_id") and cell.get("column_id") != provenance.get("column_id"):
                continue
            parts.extend([cell.get("text"), cell.get("unit"), cell.get("uncertainty_text")])
    return " ".join(str(part) for part in parts if part)


def _numeric(value: Any) -> bool:
    try:
        return value is not None and math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _unit_dimension_ok(parameter: dict[str, Any]) -> bool:
    q = parameter.get("quantitative_data") or {}
    unit = str(q.get("unit_standardized") or q.get("unit_original") or "").lower().replace(" ", "")
    subclass = str(parameter.get("parameter_subclass") or "").lower()
    if not unit:
        return False
    if any(term in subclass for term in ("partition", "fraction_unbound", "bioavailability", "hematocrit", "blood_flow_fraction", "organ_volume_fraction")):
        return any(term in unit for term in ("dimensionless", "fraction", "ratio", "%", "none", "unitless"))
    if any(term in subclass for term in ("rate", "absorption", "distribution_rate", "elimination")):
        return any(term in unit for term in ("/h", "h^-1", "1/h", "/min", "min^-1"))
    if any(term in subclass for term in ("clearance", "cardiac_output", "blood_flow")):
        return any(term in unit for term in ("l/h", "ml/min", "l/min", "/day"))
    if any(term in subclass for term in ("volume", "body_weight", "organ_volume")):
        return any(term in unit for term in ("l", "ml", "kg"))
    return True


def verify_parameters_deterministically(
    document: dict[str, Any],
    pdf_path: Optional[str] = None,
) -> dict[str, Any]:
    """Apply the refined Tan four-check verification score to every parameter.

    Checks: verbatim symbol/value source match, numeric parse completeness, unit
    dimensional consistency, and provenance/original-citation completeness.
    Any failed check sets ``needs_review=True``.
    """
    parameters = document.get("model_parameters") or []
    page_text: Dict[int, str] = {}
    if pdf_path:
        try:
            import pymupdf
            with pymupdf.open(pdf_path) as pdf:
                page_text = {
                    index + 1: page.get_text("text")
                    for index, page in enumerate(pdf)
                }
        except Exception:
            page_text = {}
    counts = {"verbatim_source_match": 0, "numeric_parse_complete": 0, "unit_dimension_consistent": 0, "provenance_complete": 0}
    score_total = 0.0
    for parameter in parameters:
        q = parameter.get("quantitative_data") or {}
        provenance = parameter.get("provenance") or {}
        source_value = _parameter_source_text(parameter, document)
        source_page = (parameter.get("provenance") or {}).get("source_page")
        if source_page in page_text:
            source_value = f"{source_value} {page_text[source_page]}"
        source = _verification_text(source_value)
        symbol = _verification_text(parameter.get("symbol_original") or parameter.get("symbol"))
        value_text = _verification_text(q.get("value_text"))
        source_match = bool(symbol and value_text and symbol in source and value_text in source)

        raw_text = str(q.get("value_text") or "")
        range_match = re.match(r"^\s*[-+]?\d*\.?\d+\s*[-–—]\s*[-+]?\d*\.?\d+", raw_text)
        if range_match:
            numeric_complete = _numeric(q.get("start_value")) and _numeric(q.get("end_value"))
        else:
            numeric_complete = _numeric(q.get("value")) or (_numeric(q.get("start_value")) and _numeric(q.get("end_value")))

        unit_ok = _unit_dimension_ok(parameter)
        location_ok = bool(provenance.get("source_table") or provenance.get("source_location") or provenance.get("source_page") is not None)
        citation_ok = bool(provenance.get("reference"))
        status_ok = bool(provenance.get("parameter_status") or provenance.get("status"))
        provenance_ok = location_ok and citation_ok and status_ok

        checks = {
            "verbatim_source_match": source_match,
            "numeric_parse_complete": numeric_complete,
            "unit_dimension_consistent": unit_ok,
            "provenance_complete": provenance_ok,
        }
        failures = [name for name, passed in checks.items() if not passed]
        score = sum(checks.values()) / 4.0
        parameter["verification_score"] = round(score, 4)
        parameter["verification_checks"] = checks
        parameter["verification_failures"] = failures
        parameter["needs_review"] = bool(failures) or bool(parameter.get("needs_review"))
        # LLM confidence is not used as a quality score.
        parameter["confidence"] = None
        score_total += score
        for name, passed in checks.items():
            if passed:
                counts[name] += 1

    total = len(parameters)
    summary = {
        "checks": counts,
        "parameter_count": total,
        "parameters_needing_review": sum(bool(p.get("verification_failures")) for p in parameters),
        "mean_verification_score": round(score_total / total, 4) if total else None,
        "weights": {"verbatim_source_match": 0.25, "numeric_parse_complete": 0.25, "unit_dimension_consistent": 0.25, "provenance_complete": 0.25},
    }
    document["parameter_verification_summary"] = summary
    return summary


def build_tan_assessment_prompt(
    extracted_doc_json: str,
    context_text: Optional[str] = None,
) -> str:
    """Build the Tan questionnaire prompt for the live assessment pass."""
    schema_json = json.dumps(TanPBPKAssessment.model_json_schema(), indent=2)
    questions = "\n".join(
        f"- [{item['item_id']}] ({item['section']}) {item['question']}\n"
        f"  Allowed evidence: {', '.join(item['allowed_source_sections'])}\n"
        f"  Routing: {item['routing_rule']}\n"
        f"  Structured fields: {', '.join(item.get('structured_fields', []))}"
        for item in TAN_QUESTIONNAIRE_ITEMS
    )
    system_prompt = f"""You are an evidence-grounded PBPK model reporting reviewer using the Tan et al. PBPK reporting template.

SCOPE RULES:
1. Evaluate the PBPK model and its reporting, not the quality of the research paper's generic Introduction or Background.
2. Apply each item's allowed-source routing exactly. The Introduction is blocked except for its final study-objective paragraph for purpose items. Do not use generic disease, toxicity, epidemiology, manufacturing, or chemical-history prose.
3. Use only the supplied extracted document. Do not use outside knowledge and do not infer that a standard PBPK practice was performed.
4. For every rating, cite the supplied model-specific evidence with a verbatim quote and source location when available.
5. If evidence is missing or ambiguous, use `i_cannot_answer`. Use `not_applicable` only when the supplied evidence explicitly establishes that the item does not apply.
6. Do not generate model code or equations. Report whether they are available and quote only equations actually present in the supplied evidence.
7. For ADME phase items, provide all four requested fields: biological mechanism, mathematical implementation, governing parameters/compartments, and exact source location.
8. For assumption items, provide stated assumption, author biological/data-gap justification, mathematical/structural impact, and exact source location.
9. Do not populate or self-score confidence. APEX will calculate deterministic parameter scores and evidence confidence after extraction.

Return every questionnaire item exactly once and output only valid JSON matching this schema:
{schema_json}
"""
    user_prompt = (
        f"TAN PBPK REPORTING QUESTIONNAIRE ITEMS:\n{questions}\n\n"
        f"EXTRACTED MODEL-SPECIFIC EVIDENCE:\n{extracted_doc_json}\n"
    )
    if context_text:
        user_prompt += (
            "\nADDITIONAL TEXT IS PROVIDED ONLY IF IT IS A MODEL-SPECIFIC METHODS/RESULTS/"
            "EQUATIONS/SOFTWARE/SENSITIVITY PASSAGE. Ignore Introduction/Background prose.\n"
            f"{context_text[:12000]}\n"
        )
    return f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\n{user_prompt}<|im_end|>\n<|im_start|>assistant\n"


def build_tan_pbpk_assessment_prompt(
    extracted_doc_json: str,
    context_text: Optional[str] = None,
) -> str:
    """Backward-friendly descriptive alias for prompt callers."""
    return build_tan_assessment_prompt(extracted_doc_json, context_text=context_text)
