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

TAN_SECTIONS: Dict[str, List[str]] = {
    "identification_and_purpose": [
        "TAN_1.1", "TAN_1.2", "TAN_1.3",
        "TAN_2.1.1", "TAN_2.1.2", "TAN_2.1.3", "TAN_2.3.1",
    ],
    "chemical_strategy_data": [
        "TAN_2.2.1", "TAN_2.4.1", "TAN_2.4.2A", "TAN_2.4.2B", "TAN_2.4.2C",
    ],
    "structure_adme_assumptions": [
        "TAN_2.4.3.1", "TAN_2.4.3.2", "TAN_2.4.3.3", "TAN_2.4.3.4", "TAN_2.4.3.5",
        "TAN_2.4.3.6", "TAN_2.4.3.7", "TAN_2.4.3.8", "TAN_2.4.3.9", "TAN_2.4.3.10",
        "TAN_2.4.3.11", "TAN_2.4.3.12", "TAN_2.4.3.13",
    ],
    "equations_parameters_software": [
        "TAN_2.4.4", "TAN_2.4.5A", "TAN_2.4.5B", "TAN_2.4.5C",
        "TAN_2.4.6A", "TAN_2.4.6B", "TAN_2.4.7",
    ],
    "evaluation_and_sensitivity": [
        "TAN_2.5.1A", "TAN_2.5.1B", "TAN_2.5.2A", "TAN_2.5.2B",
    ],
}


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


def _definition_evidence(document: dict[str, Any], item_id: str) -> List[EvidenceReference]:
    """Collect auditable evidence relevant to a refined Tan item."""
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
        # Gracefully repair LLM field aliases before Pydantic validation
        if isinstance(raw, dict) and isinstance(raw.get("items"), list):
            for item_dict in raw["items"]:
                if isinstance(item_dict, dict):
                    if not item_dict.get("details") and item_dict.get("rationale"):
                        item_dict["details"] = str(item_dict.pop("rationale"))
                    elif not item_dict.get("details"):
                        item_dict["details"] = "Evaluated from paper Markdown."
                    # Ensure required fields exist using TAN_QUESTIONNAIRE_ITEMS lookup
                    iid = item_dict.get("item_id")
                    if iid:
                        defn = next((d for d in TAN_QUESTIONNAIRE_ITEMS if d["item_id"] == iid), None)
                        if defn:
                            item_dict.setdefault("section", defn["section"])
                            item_dict.setdefault("question", defn["question"])
        assessment = TanPBPKAssessment.model_validate(raw)

    raw_by_id = {item.item_id: item for item in assessment.items}
    normalized: List[TanQuestionnaireItem] = []
    for definition in TAN_QUESTIONNAIRE_ITEMS:
        source = raw_by_id.get(definition["item_id"])
        if source is None:
            if definition["item_id"] == "TAN_1.3":
                source = TanQuestionnaireItem(
                    item_id="TAN_1.3",
                    section=definition["section"],
                    question=definition["question"],
                    allowed_source_sections=definition.get("allowed_source_sections", []),
                    routing_rule=definition.get("routing_rule"),
                    response=ResponseOption.YES,
                    details="Assessment metadata is assigned deterministically by APEX.",
                    structured_details={"reviewer": "APEX-LLM", "pipeline_version": "Refined-Tan-PBPK-v1"},
                    evidence=[],
                )
            else:
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
    """Assign evidence quality to ADME determinants and assumptions in place."""
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
    """Apply the refined Tan four-check verification score to every parameter."""
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


def convert_pdf_to_markdown(
    pdf_path: str,
    output_md_path: Optional[str] = None,
    write_images: bool = False,
    image_path: Optional[str] = None,
) -> str:
    """Convert a PDF document into structured Markdown text with explicit page markers using pymupdf4llm."""
    import os

    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    try:
        import pymupdf4llm
    except ImportError:
        raise ImportError(
            "pymupdf4llm is required to convert PDF to Markdown. "
            "Please install it with: pip install pymupdf4llm"
        )

    kwargs: Dict[str, Any] = {"page_chunks": True}
    if write_images and image_path:
        os.makedirs(image_path, exist_ok=True)
        kwargs["write_images"] = True
        kwargs["image_path"] = image_path

    raw_result = pymupdf4llm.to_markdown(pdf_path, **kwargs)
    if isinstance(raw_result, list):
        page_blocks: List[str] = []
        for idx, page_dict in enumerate(raw_result):
            page_num = (page_dict.get("metadata") or {}).get("page", idx + 1)
            text = (page_dict.get("text") or "").strip()
            if text:
                page_blocks.append(f"<!-- PAGE {page_num} -->\n### [Page {page_num}]\n{text}")
        md_text = "\n\n".join(page_blocks)
    else:
        md_text = str(raw_result)

    if output_md_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_md_path)), exist_ok=True)
        with open(output_md_path, "w", encoding="utf-8") as f:
            f.write(md_text)

    return md_text


def extract_relevant_markdown_for_items(
    markdown_text: str,
    items: Optional[List[dict[str, Any]]] = None,
    max_chars: int = 28000,
) -> str:
    """Route and filter Markdown sections specifically for the requested Tan questionnaire items.

    Prevents the second half of scientific papers (Results, Evaluation, Sensitivity,
    Discussion, Tables) from being cut off by naive prefix truncation, while strictly
    blocking generic Introduction background prose and References.
    """
    # 1. Strip References / Bibliography section from the tail to save tokens
    cleaned_md = re.sub(
        r"\n(?:#+\s*|\*\*\s*)(?:references|bibliography|literature cited|acknowledg(?:e)?ments)\b.*",
        "",
        markdown_text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    # 2. Split Markdown into logical blocks by Markdown headings (## / ###) or Page markers
    blocks = re.split(r"(?=\n(?:#{1,4}\s+|<!-- PAGE \d+ -->))", "\n" + cleaned_md)
    blocks = [b.strip() for b in blocks if b.strip()]

    if not items:
        return cleaned_md[:max_chars]

    item_ids = {it["item_id"] for it in items}

    # Determine which semantic categories of sections are needed for this batch
    needs_header_abstract = bool(item_ids & {"TAN_1.1", "TAN_1.2", "TAN_1.3", "TAN_2.1.1", "TAN_2.1.2", "TAN_2.1.3", "TAN_2.3.1"})
    needs_methods_structure = any(
        iid.startswith(("TAN_2.2", "TAN_2.4.1", "TAN_2.4.2", "TAN_2.4.3", "TAN_2.4.4", "TAN_2.4.5", "TAN_2.4.6", "TAN_2.4.7"))
        for iid in item_ids
    )
    needs_eval_sensitivity = any(
        iid.startswith(("TAN_2.5", "TAN_2.1.3", "TAN_2.4.2B", "TAN_2.4.2C"))
        for iid in item_ids
    )

    prioritized_blocks: List[str] = []
    secondary_blocks: List[str] = []

    for idx, block in enumerate(blocks):
        first_line = block.splitlines()[0].lower() if block.splitlines() else ""
        block_lower = block.lower()

        # Rule A: Filter generic Introduction background prose — retain ONLY the final objective paragraph
        if re.search(r"^#+\s*(?:1\.?\s*)?introduction\b", first_line):
            paragraphs = [p.strip() for p in re.split(r"\n\s*\n", block) if p.strip()]
            if len(paragraphs) > 1:
                first_p = paragraphs[0] if len(paragraphs[0]) <= 2000 else paragraphs[0][:2000] + "..."
                last_p = paragraphs[-1] if len(paragraphs[-1]) <= 2000 else paragraphs[-1][:2000]
                block = f"{first_p}\n\n[...General Introduction background excluded per Tan routing rule...]\n\n{last_p}"
            if needs_header_abstract:
                prioritized_blocks.append(block)
            else:
                secondary_blocks.append(block)
            continue

        # Rule B: Title / Header / Abstract / Conclusion / Discussion
        if idx <= 1 or any(k in first_line for k in ("abstract", "summary", "conclusion", "objective", "purpose")):
            if needs_header_abstract:
                prioritized_blocks.append(block)
            else:
                secondary_blocks.append(block)
            continue

        # Rule C: Evaluation, Validation, Goodness-of-Fit, Sensitivity, Uncertainty, Results, Discussion
        if any(k in first_line or k in block_lower[:400] for k in (
            "sensitivity", "evaluation", "validation", "goodness", "aafe", "rmse", "fold error",
            "fold-error", "uncertainty", "variability", "monte carlo", "mcmc", "results", "discussion", "comparison"
        )):
            if needs_eval_sensitivity:
                prioritized_blocks.append(block)
            else:
                secondary_blocks.append(block)
            continue

        # Rule D: Methods, Model Structure, ADME, Equations, Parameters, Tables, Software, Dosing
        if any(k in first_line or k in block_lower[:400] for k in (
            "method", "material", "model", "structure", "compartment", "equation", "parameter",
            "table", "software", "solver", "mrgsolve", "mcsim", "simcyp", "gastroplus", "pk-sim",
            "berkeley madonna", "matlab", "python", "scipy", "desolve", "dosing", "exposure", "calibration"
        )) or "|" in block:
            if needs_methods_structure:
                prioritized_blocks.append(block)
            else:
                secondary_blocks.append(block)
            continue

        secondary_blocks.append(block)

    # Assemble within max_chars budget, preserving document order among selected blocks
    selected_set = set()
    current_chars = 0

    for b in prioritized_blocks:
        if current_chars + len(b) + 2 <= max_chars:
            selected_set.add(b)
            current_chars += len(b) + 2
        elif current_chars < max_chars // 2:
            # Partial clip of a very large block
            selected_set.add(b[: max_chars - current_chars])
            current_chars = max_chars
            break

    for b in secondary_blocks:
        if b not in selected_set and current_chars + len(b) + 2 <= max_chars:
            selected_set.add(b)
            current_chars += len(b) + 2

    ordered_output = [b for b in (prioritized_blocks + secondary_blocks) if b in selected_set]
    # Deduplicate while preserving order
    seen_blocks: set[str] = set()
    deduped_output: List[str] = []
    for b in ordered_output:
        if b not in seen_blocks:
            seen_blocks.add(b)
            deduped_output.append(b)

    result_md = "\n\n".join(deduped_output)
    return result_md[:max_chars] if result_md else cleaned_md[:max_chars]


def build_tan_markdown_assessment_prompt(
    markdown_text: str,
    paper_title: Optional[str] = None,
    max_markdown_chars: int = 28000,
    items: Optional[List[dict[str, Any]]] = None,
    include_no_think: bool = False,
) -> str:
    """Build a high-precision, schema-aligned Tan questionnaire prompt for a paper in Markdown format."""
    selected_items = items or TAN_QUESTIONNAIRE_ITEMS
    routed_md = extract_relevant_markdown_for_items(
        markdown_text,
        items=selected_items,
        max_chars=max_markdown_chars,
    )

    questions_block = "\n".join(
        f"- [{item['item_id']}] (Section: \"{item['section']}\")\n"
        f"  Question: \"{item['question']}\"\n"
        f"  Allowed Sections: {', '.join(item['allowed_source_sections'])}\n"
        f"  Routing Rule: {item['routing_rule']}\n"
        f"  Required `structured_details` keys: {json.dumps(item.get('structured_fields', []))}"
        for item in selected_items
    )

    no_think_directive = "/no_think\n" if include_no_think else ""

    system_prompt = f"""{no_think_directive}You are an expert regulatory PBPK/TK model evaluator (US EPA / FDA / OECD GD 331 standard) executing the Tan et al. PBPK Model Reporting Questionnaire on a scientific paper converted to Markdown.

==================================================
1. STRICT OUTPUT & TOKEN BUDGET RULES
==================================================
- Output ONLY a single valid JSON object. Do NOT emit `<think>` blocks, markdown code fences, or conversational preamble.
- Return all {len(selected_items)} requested items inside the `"items"` array in the exact order listed.
- Use the EXACT field names defined below (`item_id`, `section`, `question`, `response`, `details`, `structured_details`, `evidence`). NEVER use `"rationale"` in place of `"details"`.
- Keep `"details"` concise and information-dense (1–2 sentences, <= 35 words) summarizing the exact factual answer.
- Populate `"structured_details"` as a JSON dictionary mapping each item's `Required structured_details keys` to the concrete values extracted from the paper (use `null` or `[]` if not reported).

==================================================
2. RESPONSE DECISION RUBRIC (`response` enum)
==================================================
Choose `"response"` strictly from `["yes", "partially", "no", "not_applicable", "i_cannot_answer"]`:
- `"yes"`: All core aspects of the question are explicitly reported in the allowed sections of the paper, backed by a verbatim quote.
- `"partially"`: Some aspects are explicitly reported (e.g., software name is stated, but ODE solver algorithm or version is omitted; or model compartments are listed, but mathematical equations are only partially shown), backed by a verbatim quote.
- `"no"`: The paper explicitly states that an expected step/analysis was NOT performed (e.g., "no sensitivity analysis was conducted").
- `"not_applicable"`: The paper explicitly establishes that the mechanism does not apply (e.g., gestational/lactational barrier transfer `TAN_2.4.3.8` in an adult-only non-pregnant model, or metabolism `TAN_2.4.3.6` when the compound is explicitly stated to be metabolically inert/unmetabolized).
- `"i_cannot_answer"`: The required information is absent from the allowed sections or cannot be verified with a concrete quote/location.
- SPECIAL RULE FOR `TAN_1.3`: Always set `"response": "yes"`, `"details": "Assessment metadata recorded by APEX pipeline."`, and `"structured_details": {{"assessment_date": "2026-11-09", "reviewer": "APEX Automated Tan Assessor", "pipeline_version": "Refined-Tan-PBPK-v1"}}`.

==================================================
3. SECTION ROUTING & ANTI-HALLUCINATION RULES
==================================================
- BLOCK INTRODUCTION BACKGROUND: Never use generic Introduction/Background literature (toxicity history, epidemiology, manufacturing) as evidence. Only the final study-objective paragraph of the Introduction may be used for Purpose items (`TAN_2.1.1`, `TAN_2.1.2`, `TAN_2.3.1`).
- VERBATIM EVIDENCE MANDATE: Every item rated `"yes"`, `"partially"`, `"no"`, or `"not_applicable"` (except `TAN_1.3`) MUST include at least 1 entry in `"evidence"` with:
  * `"source_page"`: Integer page number from the `<!-- PAGE X -->` or `### [Page X]` marker (or `null` if unknown).
  * `"source_section"`: Section heading name (e.g., `"Abstract"`, `"Materials and Methods"`, `"Table 1"`, `"Results"`).
  * `"source_location"`: Specific location (e.g., `"Page 3, Model Structure"`, `"Page 5, Table 1"`, `"Page 8, Sensitivity Analysis"`).
  * `"source_quote"`: Exact verbatim substring copied from the Markdown text (<= 30 words). Never paraphrase inside `source_quote`.
- Do NOT invent equations, parameter values, solver names, or goodness-of-fit criteria from general PBPK knowledge.

==================================================
4. REQUIRED JSON STRUCTURE EXAMPLE
==================================================
{{
  "model_identification": {{
    "model_name": "3-compartment TK model for PFOA, PFOS, and PFHxS",
    "target_compounds": ["PFOA", "PFOS", "PFHxS"],
    "authors": ["Author A", "Author B"],
    "publication_year": 2025,
    "journal": "Toxicological Sciences",
    "doi_pmid": "10.1093/toxsci/kfaf087"
  }},
  "items": [
    {{
      "item_id": "TAN_1.1",
      "section": "1. Model identification",
      "question": "Name the PBPK model and target compound(s), including parent, active metabolites, and CAS/identifiers when stated.",
      "response": "yes",
      "details": "The study adapts a 3-compartment toxicokinetic model for PFOA, PFOS, and PFHxS in nonhuman primates and humans; no active metabolites are modeled.",
      "structured_details": {{
        "model_name": "3-compartment TK model",
        "target_compounds": ["PFOA", "PFOS", "PFHxS"],
        "parent_or_metabolites": "Parent compounds only",
        "identifiers": null
      }},
      "evidence": [
        {{
          "source_page": 1,
          "source_section": "Abstract",
          "source_location": "Page 1, Abstract",
          "source_quote": "Here, we evaluate the use of a 3-compartment TK model for PFOA, PFOS, and PFHxS..."
        }}
      ]
    }}
  ],
  "overall_fit_for_purpose": "Brief 1-sentence summary of reporting completeness.",
  "key_gaps": [],
  "reviewer_notes": []
}}"""

    header = f"PAPER TITLE: {paper_title}\n\n" if paper_title else ""
    user_prompt = (
        f"{header}EVALUATE THE FOLLOWING {len(selected_items)} TAN PBPK QUESTIONNAIRE ITEMS:\n"
        f"{questions_block}\n\n"
        f"==================================================\n"
        f"SCIENTIFIC PAPER TEXT (MARKDOWN WITH PAGE MARKERS):\n"
        f"==================================================\n"
        f"{routed_md}\n"
    )
    return f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\n{user_prompt}<|im_end|>\n<|im_start|>assistant\n"


def strip_tan_bibliography(markdown_text: str) -> str:
    """Remove References / Bibliography section while keeping all prior paper content
    and any subsequent Tables, Figures, or Appendices intact.
    """
    ref_pattern = r"\n(?:#+\s*)?(?:\*\*\s*)?(?:references|literature cited|bibliography)(?:\s*\*\*)?\s*\n"
    m_ref = re.search(ref_pattern, markdown_text, flags=re.IGNORECASE)
    if not m_ref:
        return markdown_text.strip()

    pre_ref = markdown_text[:m_ref.start()].rstrip()
    after_ref_text = markdown_text[m_ref.end():]

    # Look for subsequent content that is NOT part of the bibliography
    # (e.g. Tables, Figures, Appendices, Supporting Info often placed at the end of author manuscripts)
    post_pattern = r"\n(?:#+\s*)?(?:\*\*\s*)?(?:table\s+\d+|tables?\b|appendix|supplementary|supporting information|figures?\s+and\s+tables?)\b"
    m_post = re.search(post_pattern, after_ref_text, flags=re.IGNORECASE)

    if m_post:
        post_content = after_ref_text[m_post.start():].strip()
        return f"{pre_ref}\n\n[... References Section Omitted For Length ...]\n\n{post_content}"
    else:
        return pre_ref


def build_tan_kv_cache_prompt(
    clean_paper_md: str,
    items: Optional[List[dict[str, Any]]] = None,
    paper_title: Optional[str] = None,
    include_no_think: bool = False,
    pre_close_think: bool = True,
) -> str:
    """Build an immutable-prefix, KV-cache-optimized prompt for the Tan questionnaire.

    The system prompt, paper title, and entire cleaned paper text are placed FIRST
    as a byte-for-byte identical prefix across all batches. The batch questionnaire
    items and required structured keys are appended at the very end as a dynamic suffix.
    """
    selected_items = items or TAN_QUESTIONNAIRE_ITEMS
    questions_block = "\n".join(
        f"- [{item['item_id']}] (Section: \"{item['section']}\")\n"
        f"  Question: \"{item['question']}\"\n"
        f"  Allowed Sections: {', '.join(item['allowed_source_sections'])}\n"
        f"  Routing Rule: {item['routing_rule']}\n"
        f"  Required `structured_details` keys: {json.dumps(item.get('structured_fields', []))}"
        for item in selected_items
    )

    no_think_directive = "/no_think\n" if include_no_think else ""

    system_prompt = f"""{no_think_directive}You are an expert regulatory PBPK/TK model evaluator (US EPA / FDA / OECD GD 331 standard) executing the Tan et al. PBPK Model Reporting Questionnaire on a scientific paper converted to Markdown.

==================================================
1. STRICT OUTPUT & TOKEN BUDGET RULES
==================================================
- Output ONLY a single valid JSON object. Do NOT emit `<think>` blocks, markdown code fences, or conversational preamble.
- Return all {len(selected_items)} requested items inside the `"items"` array in the exact order listed.
- Use the EXACT field names defined below (`item_id`, `section`, `question`, `response`, `details`, `structured_details`, `evidence`). NEVER use `"rationale"` in place of `"details"`.
- Keep `"details"` concise and information-dense (1–2 sentences, <= 35 words) summarizing the exact factual answer.
- Populate `"structured_details"` as a JSON dictionary mapping each item's `Required structured_details keys` to the concrete values extracted from the paper (use `null` or `[]` if not reported).

==================================================
2. RESPONSE DECISION RUBRIC (`response` enum)
==================================================
Choose `"response"` strictly from `["yes", "partially", "no", "not_applicable", "i_cannot_answer"]`:
- `"yes"`: All core aspects of the question are explicitly reported in the allowed sections of the paper, backed by a verbatim quote.
- `"partially"`: Some aspects are explicitly reported (e.g., software name is stated, but ODE solver algorithm or version is omitted; or model compartments are listed, but mathematical equations are only partially shown), backed by a verbatim quote.
- `"no"`: The paper explicitly states that an expected step/analysis was NOT performed (e.g., "no sensitivity analysis was conducted").
- `"not_applicable"`: The paper explicitly establishes that the mechanism does not apply (e.g., gestational/lactational barrier transfer `TAN_2.4.3.8` in an adult-only non-pregnant model, or metabolism `TAN_2.4.3.6` when the compound is explicitly stated to be metabolically inert/unmetabolized).
- `"i_cannot_answer"`: The required information is absent from the allowed sections or cannot be verified with a concrete quote/location.
- SPECIAL RULE FOR `TAN_1.3`: Always set `"response": "yes"`, `"details": "Assessment metadata recorded by APEX pipeline."`, and `"structured_details": {{"assessment_date": "2026-11-09", "reviewer": "APEX Automated Tan Assessor", "pipeline_version": "Refined-Tan-PBPK-v1"}}`.

==================================================
3. SECTION ROUTING & ANTI-HALLUCINATION RULES
==================================================
- BLOCK INTRODUCTION BACKGROUND: Never use generic Introduction/Background literature (toxicity history, epidemiology, manufacturing) as evidence. Only the final study-objective paragraph of the Introduction may be used for Purpose items (`TAN_2.1.1`, `TAN_2.1.2`, `TAN_2.3.1`).
- VERBATIM EVIDENCE MANDATE: Every item rated `"yes"`, `"partially"`, `"no"`, or `"not_applicable"` (except `TAN_1.3`) MUST include at least 1 entry in `"evidence"` with:
  * `"source_page"`: Integer page number from the `<!-- PAGE X -->` or `### [Page X]` marker (or `null` if unknown).
  * `"source_section"`: Section heading name (e.g., `"Abstract"`, `"Materials and Methods"`, `"Table 1"`, `"Results"`).
  * `"source_location"`: Specific location (e.g., `"Page 3, Model Structure"`, `"Page 5, Table 1"`, `"Page 8, Sensitivity Analysis"`).
  * `"source_quote"`: Exact verbatim substring copied from the Markdown text (<= 30 words). Never paraphrase inside `source_quote`.
- Do NOT invent equations, parameter values, solver names, or goodness-of-fit criteria from general PBPK knowledge.

==================================================
4. REQUIRED JSON STRUCTURE EXAMPLE
==================================================
{{
  "model_identification": {{
    "model_name": "3-compartment TK model for PFOA, PFOS, and PFHxS",
    "target_compounds": ["PFOA", "PFOS", "PFHxS"],
    "authors": ["Author A", "Author B"],
    "publication_year": 2025,
    "journal": "Toxicological Sciences",
    "doi_pmid": "10.1093/toxsci/kfaf087"
  }},
  "items": [
    {{
      "item_id": "TAN_1.1",
      "section": "1. Model identification",
      "question": "Name the PBPK model and target compound(s), including parent, active metabolites, and CAS/identifiers when stated.",
      "response": "yes",
      "details": "The study adapts a 3-compartment toxicokinetic model for PFOA, PFOS, and PFHxS in nonhuman primates and humans; no active metabolites are modeled.",
      "structured_details": {{
        "model_name": "3-compartment TK model",
        "target_compounds": ["PFOA", "PFOS", "PFHxS"],
        "parent_or_metabolites": "Parent compounds only",
        "identifiers": null
      }},
      "evidence": [
        {{
          "source_page": 1,
          "source_section": "Abstract",
          "source_location": "Page 1, Abstract",
          "source_quote": "Here, we evaluate the use of a 3-compartment TK model for PFOA, PFOS, and PFHxS..."
        }}
      ]
    }}
  ],
  "overall_fit_for_purpose": "Brief 1-sentence summary of reporting completeness.",
  "key_gaps": [],
  "reviewer_notes": []
}}"""

    header = f"PAPER TITLE: {paper_title}\n\n" if paper_title else ""
    user_prompt = (
        f"{header}==================================================\n"
        f"SCIENTIFIC PAPER TEXT (MARKDOWN WITH PAGE MARKERS):\n"
        f"==================================================\n"
        f"{clean_paper_md}\n\n"
        f"==================================================\n"
        f"EVALUATE THE FOLLOWING {len(selected_items)} TAN PBPK QUESTIONNAIRE ITEMS FOR THE PAPER ABOVE:\n"
        f"==================================================\n"
        f"{questions_block}\n"
    )
    think_closer = "<think>\n</think>\n" if pre_close_think else ""
    return f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\n{user_prompt}<|im_end|>\n<|im_start|>assistant\n{think_closer}"


def evaluate_tan_from_markdown(
    markdown_text: str,
    paper_title: Optional[str] = None,
) -> TanPBPKAssessment:
    """Create a deterministic baseline Tan assessment by scanning Markdown text for evidence."""
    lines = markdown_text.splitlines()
    text_lower = markdown_text.lower()

    # 1. Identify Title and Authors from headers
    title = paper_title
    doi = None
    journal = None
    for line in lines[:45]:
        stripped = line.strip()
        if not title and stripped.startswith("# ") and "page " not in stripped.lower():
            title = stripped.lstrip("#* ").rstrip("* ")
        if not doi and "doi.org" in stripped:
            doi = stripped
        if not journal and ("journal" in stripped.lower() or "toxicological sciences" in stripped.lower() or "environment" in stripped.lower()):
            journal = stripped.strip("*_ ")

    # 2. Collect Markdown tables
    has_tables = bool(re.search(r"\|[ -]+(?:\|[ -]+)+\|", markdown_text) or "<table" in text_lower)

    # 3. Collect equations (LaTeX $$ ... $$, \( ... \), d[A-Z]/dt)
    has_equations = bool(
        "$$" in markdown_text
        or "\\[" in markdown_text
        or re.search(r"d[A-Za-z_]+/dt\s*=", markdown_text)
        or re.search(r"\\frac\{d", markdown_text)
    )

    # 4. Search for software tools
    software_terms = [
        "mrgsolve", "mcsim", "r package", "r version", "desolve",
        "matlab", "simcyp", "gastroplus", "pk-sim", "berkeley madonna",
        "python", "scipy", "stan", "nlmixr", "monolix", "nonmem", "acslx"
    ]
    detected_software: List[str] = [term for term in software_terms if term in text_lower]

    # 5. Search for ADME keywords & assumptions
    has_absorption = any(w in text_lower for w in ["oral absorption", "absorption rate", "bioavailability", "uptake", "kabs", "ka "])
    has_binding = any(w in text_lower for w in ["protein binding", "free fraction", "fraction unbound", "albumin", "fu "])
    has_metabolism = any(w in text_lower for w in ["vmax", "km", "metabolism", "michaelis-menten", "clearance", "metabolite"])
    has_excretion = any(w in text_lower for w in ["renal clearance", "urinary excretion", "reabsorption", "elimination rate", "fecal"])

    # 6. Search for sensitivity and validation metrics
    has_sensitivity = any(w in text_lower for w in ["sensitivity analysis", "morris", "sobol", "parameter sensitivity", "sensitivity coefficient"])
    has_gof = any(w in text_lower for w in ["aafe", "rmse", "r2", "r^2", "mfe", "goodness-of-fit", "fold-error", "fold error"])

    items: List[TanQuestionnaireItem] = []

    for item_def in TAN_QUESTIONNAIRE_ITEMS:
        item_id = item_def["item_id"]
        evidence: List[EvidenceReference] = []
        details = "No model-specific evidence was captured from the Markdown text."
        response = ResponseOption.I_CANNOT_ANSWER

        if item_id == "TAN_1.1":
            if title:
                response = ResponseOption.PARTIALLY
                details = f"Model title and context identified from Markdown header: {title}"
                evidence.append(_evidence(page=1, location="Markdown header", quote=title[:120], section="Title"))
        elif item_id == "TAN_1.2":
            if doi or journal:
                response = ResponseOption.PARTIALLY
                details = f"Bibliographic information identified: {doi or journal}"
                evidence.append(_evidence(page=1, location="Header metadata", quote=str(doi or journal)[:120], section="Metadata"))
        elif item_id == "TAN_1.3":
            response = ResponseOption.YES
            details = "Assessment metadata is assigned deterministically by APEX."
        elif item_id in {"TAN_2.1.1", "TAN_2.1.2", "TAN_2.3.1"}:
            abstract_m = re.search(r"(?i)#+\s*abstract\s*\n(.*?)(?=\n#+|$)", markdown_text, re.DOTALL)
            if abstract_m:
                quote = abstract_m.group(1).strip()[:200]
                response = ResponseOption.PARTIALLY
                details = "Purpose and executive summary evidence extracted from Abstract section."
                evidence.append(_evidence(page=1, location="Abstract section", quote=quote, section="Abstract"))
        elif item_id == "TAN_2.1.3":
            response = ResponseOption.I_CANNOT_ANSWER
            details = "Quantitative conclusions require structured LLM evaluation of Results/Discussion."
        elif item_id in {"TAN_2.4.3.3", "TAN_2.4.3.4", "TAN_2.4.3.5", "TAN_2.4.3.6", "TAN_2.4.3.7"}:
            phase_checks = {
                "TAN_2.4.3.3": ("absorption", has_absorption),
                "TAN_2.4.3.4": ("binding/distribution", has_binding),
                "TAN_2.4.3.5": ("tissue partitioning", "partition" in text_lower),
                "TAN_2.4.3.6": ("metabolism", has_metabolism),
                "TAN_2.4.3.7": ("excretion", has_excretion),
            }
            phase_name, present = phase_checks[item_id]
            if present:
                response = ResponseOption.PARTIALLY
                details = f"ADME {phase_name} mechanisms identified in Markdown methods/results."
                evidence.append(_evidence(location="Methods text", quote=f"Mentions of {phase_name} in model text", section="Methods"))
        elif item_id == "TAN_2.4.4":
            if has_equations:
                response = ResponseOption.PARTIALLY
                details = "Mathematical equations or rate equations detected in Markdown."
                evidence.append(_evidence(location="Equations section", quote="Mathematical equations present in text", section="Methods"))
        elif item_id in {"TAN_2.4.5A", "TAN_2.4.5B"}:
            if has_tables:
                response = ResponseOption.PARTIALLY
                details = "Parameter table(s) detected in Markdown text."
                evidence.append(_evidence(location="Table block", quote="Markdown parameter table present", section="Tables"))
        elif item_id == "TAN_2.4.7":
            if detected_software:
                response = ResponseOption.PARTIALLY
                details = f"Software / solver references detected: {', '.join(detected_software)}"
                evidence.append(_evidence(location="Methods text", quote=f"Software: {detected_software[0]}", section="Methods"))
        elif item_id in {"TAN_2.5.1A", "TAN_2.5.1B"}:
            if has_gof:
                response = ResponseOption.PARTIALLY
                details = "Goodness-of-fit metrics or validation terminology detected in Results/Discussion."
                evidence.append(_evidence(location="Results text", quote="Evaluation / goodness-of-fit metrics present", section="Results"))
        elif item_id in {"TAN_2.5.2A", "TAN_2.5.2B"}:
            if has_sensitivity:
                response = ResponseOption.PARTIALLY
                details = "Sensitivity analysis terms detected in Markdown text."
                evidence.append(_evidence(location="Methods / Results text", quote="Sensitivity analysis mentioned", section="Methods"))

        items.append(_make_item(item_def, response, details, evidence, require_evidence=(item_id != "TAN_1.3")))

    model_metadata = {
        "model_name": title,
        "authors": lines[0] if lines else None,
        "doi_pmid": doi,
        "journal": journal,
    }
    cannot_count = sum(it.response == ResponseOption.I_CANNOT_ANSWER for it in items)
    return TanPBPKAssessment(
        template_name="Tan et al. PBPK Reporting Template (Markdown Baseline)",
        template_version="Refined-Tan-PBPK-Research-v1",
        assessment_scope="Deterministic scan of Markdown text; generic Introduction/Background excluded.",
        model_identification=model_metadata,
        items=items,
        overall_fit_for_purpose=f"{len(items) - cannot_count}/{len(items)} Tan items supported by Markdown evidence; {cannot_count}/{len(items)} require deeper extraction.",
        key_gaps=[f"{it.item_id}: evidence incomplete in Markdown text" for it in items if it.response == ResponseOption.I_CANNOT_ANSWER],
        reviewer_notes=[
            "Deterministic baseline generated from paper Markdown text.",
            "Confidence levels computed from auditable evidence references.",
        ],
    )


async def assess_tan_from_markdown(
    markdown_text: str,
    extractor: Optional[Any] = None,
    paper_title: Optional[str] = None,
    mode: str = "sections",
    max_new_tokens: int = 12000,
) -> TanPBPKAssessment:
    """Asynchronously evaluate all Tan questionnaire items against a Markdown paper using the LLM."""
    if extractor is not None and hasattr(extractor, "assess_tan_from_markdown"):
        return await extractor.assess_tan_from_markdown(
            markdown_text=markdown_text,
            paper_title=paper_title,
            mode=mode,
            max_new_tokens=max_new_tokens,
        )

    try:
        from pk_pipeline.ml_services import SGLangExtractor
        ext = SGLangExtractor()
        if ext.is_loaded:
            return await ext.assess_tan_from_markdown(
                markdown_text=markdown_text,
                paper_title=paper_title,
                mode=mode,
                max_new_tokens=max_new_tokens,
            )
    except Exception:
        pass

    return evaluate_tan_from_markdown(markdown_text, paper_title=paper_title)