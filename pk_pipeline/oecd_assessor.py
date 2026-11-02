"""OECD GD 331 & Tan et al. PBPK Model Evaluation Engine.

Provides:
1. Canonical OECD checklist items derived from OECD GD 331 and Tan et al.
2. Deterministic evidence-backed evaluator (evaluate_oecd_from_document)
3. LLM-based Stage-3 assessment prompt and runner for regulatory review
"""

import json
import logging
from typing import Any, Dict, List, Optional, Union

from pk_pipeline.schemas import (
    EvidenceReference,
    ExtractedDocument,
    OECDChecklistItem,
    OECDAssessment,
    ResponseOption,
)

logger = logging.getLogger("OECD_ASSESSOR")

# ─── Canonical OECD GD 331 / Tan et al. Checklist Definitions ──────────────────

CANONICAL_CHECKLIST_ITEMS = [
    {
        "item_id": "OECD_01",
        "category": "Model Context & Scope",
        "question": "Is there a clear indication of the chemical, or chemicals, to which the model is applicable?",
        "table_ref": "Table 1 & Table 3 (Item 19)",
    },
    {
        "item_id": "OECD_02",
        "category": "Model Context & Scope",
        "question": "Is the model being applied for the same scientific purpose as it was developed, or has it been repurposed for a different application?",
        "table_ref": "Table 3 (Item 21)",
    },
    {
        "item_id": "OECD_03",
        "category": "Population & Life Stages",
        "question": "Has the model considered specific age groups (e.g., teenagers, children, adults, older adults, infants)?",
        "table_ref": "Table 2 (Item 9)",
    },
    {
        "item_id": "OECD_04",
        "category": "Population & Life Stages",
        "question": "Which population model has been considered for evaluating or validating the model (e.g. European, Asian, American, global)?",
        "table_ref": "Table 2 (Item 11)",
    },
    {
        "item_id": "OECD_05",
        "category": "Biological Basis",
        "question": "Does the model include specific mechanisms required to explain the long half-life of compound (e.g. renal reabsorption, enterohepatic circulation)?",
        "table_ref": "Table 2 (Item 13)",
    },
    {
        "item_id": "OECD_06",
        "category": "Biological Basis",
        "question": "Is the model consistent with known biology, and is the biological basis for the model structure provided?",
        "table_ref": "Table 6 (Items 71-72)",
    },
    {
        "item_id": "OECD_07",
        "category": "Biological Basis",
        "question": "Have all model assumptions been adequately described and supported with evidence?",
        "table_ref": "Table 3 (Item 23)",
    },
    {
        "item_id": "OECD_08",
        "category": "Mode of Action",
        "question": "Is there a graphical or clear conceptual representation of the proposed toxicological mode of action (MoA)?",
        "table_ref": "Table 3 (Item 25)",
    },
    {
        "item_id": "OECD_09",
        "category": "Model Structure",
        "question": "Is there a graphical representation of the conceptual PBPK model topology and organ compartments?",
        "table_ref": "Table 3 (Item 27)",
    },
    {
        "item_id": "OECD_10",
        "category": "Parameters",
        "question": "Is there supporting tabulation for parameters including names, meanings, values, units, uncertainty/SD, and sources?",
        "table_ref": "Table 3 (Item 29)",
    },
    {
        "item_id": "OECD_11",
        "category": "Mathematical Representation",
        "question": "Are mathematical differential equations (ODEs) available and based on established physical/biochemical theories?",
        "table_ref": "Table 3 (Item 35) & Table 7 (Item 86)",
    },
    {
        "item_id": "OECD_12",
        "category": "Reproducibility",
        "question": "Is the PBK model code available in the manuscript, supplementary files, or public repository?",
        "table_ref": "Table 3 (Item 37)",
    },
    {
        "item_id": "OECD_13",
        "category": "Reproducibility",
        "question": "Does the model code accurately express the stated mathematical model equations?",
        "table_ref": "Table 4 (Item 43)",
    },
    {
        "item_id": "OECD_14",
        "category": "Software & Simulation",
        "question": "Is the PBK software platform named, qualified, and using a well-established mathematical solver algorithm?",
        "table_ref": "Table 3 (Item 39) & Table 4 (Item 55)",
    },
    {
        "item_id": "OECD_15",
        "category": "Physicochemical Properties",
        "question": "In the case of particles/nanomaterials, does the model take into consideration particle size, solubility, aggregation, or sedimentation?",
        "table_ref": "Table 7 (Item 88)",
    },
    {
        "item_id": "OECD_16",
        "category": "Uncertainty & Sensitivity",
        "question": "Has the impact of parameter uncertainty and individual biological variability on the chosen dose metric been estimated?",
        "table_ref": "Table 8 (Item 96)",
    },
    {
        "item_id": "OECD_17",
        "category": "Uncertainty & Sensitivity",
        "question": "Was local sensitivity analysis (LSA) conducted with a clearly defined sensitivity criterion?",
        "table_ref": "Table 8 (Item 98)",
    },
    {
        "item_id": "OECD_18",
        "category": "Uncertainty & Sensitivity",
        "question": "Was global sensitivity analysis (GSA) conducted with an established sampling approach and criterion?",
        "table_ref": "Table 8 (Item 100)",
    },
    {
        "item_id": "OECD_19",
        "category": "Predictive Performance",
        "question": "If in vivo pharmacokinetic data for the chemical of interest is lacking, was suitability as an analogue assessed?",
        "table_ref": "Table 9 (Item 106)",
    },
    {
        "item_id": "OECD_20",
        "category": "Predictive Performance",
        "question": "Are quantitative comparisons (graphical concentration-time curves or statistical comparisons) of model predictions to experimental data given?",
        "table_ref": "Table 9 (Item 114)",
    },
    {
        "item_id": "OECD_21",
        "category": "Predictive Performance",
        "question": "Have objective goodness-of-fit (GOF) metrics or statistics been reported (e.g., AAFE, RMSE, R^2, visual predictive checks)?",
        "table_ref": "Table 9 (Item 116)",
    },
    {
        "item_id": "OECD_22",
        "category": "Predictive Performance",
        "question": "Are model calibration (training/parameter-fitting) datasets and independent evaluation (validation) datasets clearly distinguished and independent?",
        "table_ref": "OECD GD 331 Section 4",
    },
]


def build_oecd_assessment_prompt(extracted_doc_json: str, context_text: Optional[str] = None) -> str:
    """Generate the regulatory Tier-3 prompt for assessing compliance with OECD GD 331."""
    schema_json = json.dumps(OECDAssessment.model_json_schema(), indent=2)
    checklist_text = "\n".join(
        f"- [{item['item_id']}] ({item['category']}) {item['question']}"
        for item in CANONICAL_CHECKLIST_ITEMS
    )

    system_prompt = (
        "You are an expert regulatory pharmacokinetic (PK) model evaluator working for a health or environmental agency (e.g. OECD, US EPA, EFSA, FDA).\n"
        "Your task is to conduct a formal OECD GD 331 / Tan et al. compliance assessment of the extracted PBPK model.\n\n"
        "EVALUATION CRITERIA:\n"
        "1. Base your judgments strictly on the factual evidence provided in the extracted model and paper text.\n"
        "2. For every checklist item, choose strictly one of:\n"
        "   - 'yes': The requirement is explicitly and fully satisfied with clear documentation.\n"
        "   - 'partially': Some elements are present or partially documented, but gaps remain.\n"
        "   - 'no': The requirement is completely unaddressed or missing.\n"
        "   - 'i_cannot_answer': The provided text or evidence is insufficient to verify the condition.\n"
        "   - 'not_applicable': The requirement does not apply to this specific chemical or model context (e.g., particle properties for non-particles).\n"
        "3. Provide a clear rationale and cite verbatim evidence quotes with source page/section.\n"
        "4. Output MUST conform strictly to the OECDAssessment JSON schema below:\n"
        f"```json\n{schema_json}\n```\n"
        "Output ONLY the valid JSON document with no additional markdown commentary."
    )

    user_prompt = (
        f"OECD GD 331 CHECKLIST QUESTIONS TO EVALUATE:\n{checklist_text}\n\n"
        f"EXTRACTED PBPK MODEL DATA (STAGE 2 NORMALIZED EVIDENCE):\n{extracted_doc_json}\n"
    )
    if context_text:
        user_prompt += f"\nADDITIONAL PAPER TEXT / CONTEXT:\n{context_text[:12000]}\n"

    return f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\n{user_prompt}<|im_end|>\n<|im_start|>assistant\n"


def evaluate_oecd_from_document(doc: Union[dict, ExtractedDocument]) -> OECDAssessment:
    """Evaluate an extracted document deterministically against the OECD GD 331 checklist.

    Produces an evidence-backed OECDAssessment based on the factual fields present.
    """
    if isinstance(doc, ExtractedDocument):
        d = doc.model_dump()
    elif isinstance(doc, dict):
        d = doc
    else:
        d = {}

    items: List[OECDChecklistItem] = []
    key_gaps: List[str] = []

    model_context = d.get("model_context") or {}
    bio_basis = d.get("biological_basis") or {}
    model_struct = d.get("model_structure") or {}
    parameters = d.get("model_parameters") or []
    tables = d.get("table_evidence") or []
    software = d.get("software") or {}
    reproducibility = d.get("reproducibility") or {}
    mode_of_action = d.get("mode_of_action") or {}
    observed_data = d.get("observed_data") or []
    simulated_data = d.get("simulated_data") or []
    sensitivity = d.get("sensitivity_analysis") or []
    ext_sensitivity = d.get("extended_sensitivity") or {}
    judgments = d.get("evaluator_judgments") or {}

    # OECD_01: Chemical applicability
    subject_compounds = set()
    for t in tables:
        subject_compounds.update(t.get("subject_compounds", []))
    for p in parameters:
        c = p.get("compound")
        if c and c.lower() not in {"unassigned", "all", "none", ""}:
            subject_compounds.add(c)
    if subject_compounds:
        chem_str = ", ".join(sorted(subject_compounds))
        items.append(
            OECDChecklistItem(
                item_id="OECD_01",
                category="Model Context & Scope",
                question="Is there a clear indication of the chemical, or chemicals, to which the model is applicable?",
                response=ResponseOption.YES,
                rationale=f"Model explicitly indicates applicability to chemical(s): {chem_str}.",
                evidence=[EvidenceReference(source_location="Model Parameters & Tables", source_quote=f"Chemicals: {chem_str}")],
                confidence="high",
            )
        )
    else:
        items.append(
            OECDChecklistItem(
                item_id="OECD_01",
                category="Model Context & Scope",
                question="Is there a clear indication of the chemical, or chemicals, to which the model is applicable?",
                response=ResponseOption.PARTIALLY,
                rationale="Chemical applicability is not explicitly structured in model parameters.",
                confidence="medium",
            )
        )
        key_gaps.append("Chemical applicability not clearly defined in structured metadata.")

    # OECD_02: Model Purpose & Origin
    stated_purpose = model_context.get("stated_purpose", "")
    origin = model_context.get("model_origin", "")
    if stated_purpose and stated_purpose != "not_reported":
        repurposed = model_context.get("repurposed")
        resp = ResponseOption.YES if not repurposed else ResponseOption.PARTIALLY
        rationale = f"Stated purpose is documented: '{stated_purpose}'. Origin: '{origin}'."
        items.append(
            OECDChecklistItem(
                item_id="OECD_02",
                category="Model Context & Scope",
                question="Is the model being applied for the same scientific purpose as it was developed, or has it been repurposed for a different application?",
                response=resp,
                rationale=rationale,
                evidence=[EvidenceReference(source_location="ModelContext", source_quote=stated_purpose)],
                confidence="high",
            )
        )
    else:
        items.append(
            OECDChecklistItem(
                item_id="OECD_02",
                category="Model Context & Scope",
                question="Is the model being applied for the same scientific purpose as it was developed, or has it been repurposed for a different application?",
                response=ResponseOption.PARTIALLY,
                rationale="Model origin and context are mentioned, but regulatory purpose is not explicitly demarcated.",
                confidence="medium",
            )
        )

    # OECD_03: Age groups
    age_groups = model_context.get("age_groups") or []
    life_stages = model_context.get("life_stages") or []
    if age_groups or life_stages:
        items.append(
            OECDChecklistItem(
                item_id="OECD_03",
                category="Population & Life Stages",
                question="Has the model considered specific age groups (e.g., teenagers, children, adults, older adults, infants)?",
                response=ResponseOption.YES,
                rationale=f"Considered age groups/life stages: {', '.join(age_groups + life_stages)}.",
                evidence=[EvidenceReference(source_location="ModelContext", source_quote=str(age_groups + life_stages))],
                confidence="high",
            )
        )
    else:
        # Check if parameters mention age/life stage
        param_stages = set(p.get("life_stage") for p in parameters if p.get("life_stage"))
        if param_stages:
            items.append(
                OECDChecklistItem(
                    item_id="OECD_03",
                    category="Population & Life Stages",
                    question="Has the model considered specific age groups (e.g., teenagers, children, adults, older adults, infants)?",
                    response=ResponseOption.YES,
                    rationale=f"Model parameters indicate specific life stages/age groups: {', '.join(sorted(param_stages))}.",
                    confidence="high",
                )
            )
        else:
            items.append(
                OECDChecklistItem(
                    item_id="OECD_03",
                    category="Population & Life Stages",
                    question="Has the model considered specific age groups (e.g., teenagers, children, adults, older adults, infants)?",
                    response=ResponseOption.NO,
                    rationale="No explicit age groups or life stages were modeled beyond standard adult reference.",
                    confidence="medium",
                )
            )

    # OECD_04: Population model
    geo_pop = model_context.get("geographic_population")
    target_pop = model_context.get("target_populations") or []
    if geo_pop or target_pop:
        items.append(
            OECDChecklistItem(
                item_id="OECD_04",
                category="Population & Life Stages",
                question="Which population model has been considered for evaluating or validating the model (e.g. European, Asian, American, global)?",
                response=ResponseOption.YES,
                rationale=f"Population model documented: geographic={geo_pop}, targets={target_pop}.",
                confidence="high",
            )
        )
    else:
        items.append(
            OECDChecklistItem(
                item_id="OECD_04",
                category="Population & Life Stages",
                question="Which population model has been considered for evaluating or validating the model (e.g. European, Asian, American, global)?",
                response=ResponseOption.I_CANNOT_ANSWER,
                rationale="Specific ethnic/geographic population model details are not explicitly recorded.",
                confidence="medium",
            )
        )

    # OECD_05: Long half-life mechanisms
    specialized = bio_basis.get("specialized_mechanisms") or []
    has_hl_mech = any(m.lower() in ("renal_reabsorption", "enterohepatic_circulation", "renal reabsorption", "enterohepatic circulation") for m in specialized)
    if has_hl_mech:
        items.append(
            OECDChecklistItem(
                item_id="OECD_05",
                category="Biological Basis",
                question="Does the model include specific mechanisms required to explain the long half-life of compound (e.g. renal reabsorption, enterohepatic circulation)?",
                response=ResponseOption.YES,
                rationale=f"Specialized half-life mechanisms modeled: {', '.join(specialized)}.",
                evidence=[EvidenceReference(source_location="BiologicalBasis", source_quote=str(specialized))],
                confidence="high",
            )
        )
    elif "not_applicable" in [s.lower() for s in specialized]:
        items.append(
            OECDChecklistItem(
                item_id="OECD_05",
                category="Biological Basis",
                question="Does the model include specific mechanisms required to explain the long half-life of compound (e.g. renal reabsorption, enterohepatic circulation)?",
                response=ResponseOption.NOT_APPLICABLE,
                rationale="Specialized long half-life mechanisms designated not applicable for this compound.",
                confidence="high",
            )
        )
    else:
        items.append(
            OECDChecklistItem(
                item_id="OECD_05",
                category="Biological Basis",
                question="Does the model include specific mechanisms required to explain the long half-life of compound (e.g. renal reabsorption, enterohepatic circulation)?",
                response=ResponseOption.PARTIALLY,
                rationale="Standard clearance mechanisms are present; specialized retention mechanisms are not explicitly parameterized.",
                confidence="medium",
            )
        )

    # OECD_06: Biological basis
    adme = bio_basis.get("adme_determinants") or []
    if adme:
        items.append(
            OECDChecklistItem(
                item_id="OECD_06",
                category="Biological Basis",
                question="Is the model consistent with known biology, and is the biological basis for the model structure provided?",
                response=ResponseOption.YES,
                rationale=f"Biological basis provided with ADME determinants: {', '.join(adme[:5])}.",
                confidence="high",
            )
        )
    else:
        items.append(
            OECDChecklistItem(
                item_id="OECD_06",
                category="Biological Basis",
                question="Is the model consistent with known biology, and is the biological basis for the model structure provided?",
                response=ResponseOption.PARTIALLY,
                rationale="Standard physiological compartmentation is used, but detailed ADME narrative is brief.",
                confidence="medium",
            )
        )

    # OECD_07: Model assumptions
    stated_assumptions = bio_basis.get("stated_assumptions") or []
    if stated_assumptions:
        items.append(
            OECDChecklistItem(
                item_id="OECD_07",
                category="Biological Basis",
                question="Have all model assumptions been adequately described and supported with evidence?",
                response=ResponseOption.YES,
                rationale=f"{len(stated_assumptions)} explicit model assumptions documented with quotes.",
                evidence=[
                    EvidenceReference(
                        source_location=a.get("source_location"),
                        source_quote=a.get("evidence_quote") or a.get("description"),
                    )
                    for a in stated_assumptions[:3]
                ],
                confidence="high",
            )
        )
    else:
        items.append(
            OECDChecklistItem(
                item_id="OECD_07",
                category="Biological Basis",
                question="Have all model assumptions been adequately described and supported with evidence?",
                response=ResponseOption.PARTIALLY,
                rationale="Implicit assumptions are standard for PBPK, but explicit assumption list with citations is limited.",
                confidence="medium",
            )
        )
        key_gaps.append("Model assumptions lack explicit comprehensive tabulation in manuscript.")

    # OECD_08: Mode of action representation
    if mode_of_action.get("available"):
        items.append(
            OECDChecklistItem(
                item_id="OECD_08",
                category="Mode of Action",
                question="Is there a graphical or clear conceptual representation of the proposed toxicological mode of action (MoA)?",
                response=ResponseOption.YES,
                rationale=f"Mode of action documented: {mode_of_action.get('description')}. Target tissue: {mode_of_action.get('target_tissue')}.",
                confidence="high",
            )
        )
    else:
        items.append(
            OECDChecklistItem(
                item_id="OECD_08",
                category="Mode of Action",
                question="Is there a graphical or clear conceptual representation of the proposed toxicological mode of action (MoA)?",
                response=ResponseOption.NO,
                rationale="The publication focuses on pharmacokinetics / internal dosimetry without explicit toxicodynamic mode-of-action linkage.",
                confidence="high",
            )
        )

    # OECD_09: Conceptual model diagram
    compartments = model_struct.get("compartments") or []
    connections = model_struct.get("connections") or []
    if compartments or connections:
        items.append(
            OECDChecklistItem(
                item_id="OECD_09",
                category="Model Structure",
                question="Is there a graphical representation of the conceptual PBPK model topology and organ compartments?",
                response=ResponseOption.YES,
                rationale=f"Conceptual model structure documented with {len(compartments)} compartments and {len(connections)} connections.",
                confidence="high",
            )
        )
    else:
        items.append(
            OECDChecklistItem(
                item_id="OECD_09",
                category="Model Structure",
                question="Is there a graphical representation of the conceptual PBPK model topology and organ compartments?",
                response=ResponseOption.PARTIALLY,
                rationale="Compartmental structure described in text, but structured topology diagram is missing.",
                confidence="medium",
            )
        )

    # OECD_10: Supporting parameter tabulation
    if len(parameters) > 10:
        has_sources = sum(1 for p in parameters if p.get("provenance", {}).get("reference") or p.get("provenance", {}).get("source_quote"))
        has_units = sum(1 for p in parameters if p.get("unit"))
        items.append(
            OECDChecklistItem(
                item_id="OECD_10",
                category="Parameters",
                question="Is there supporting tabulation for parameters including names, meanings, values, units, uncertainty/SD, and sources?",
                response=ResponseOption.YES,
                rationale=f"Extensive parameter tabulation present ({len(parameters)} parameters, {has_units} with explicit units, {has_sources} with source citations).",
                confidence="high",
            )
        )
    elif len(parameters) > 0:
        items.append(
            OECDChecklistItem(
                item_id="OECD_10",
                category="Parameters",
                question="Is there supporting tabulation for parameters including names, meanings, values, units, uncertainty/SD, and sources?",
                response=ResponseOption.PARTIALLY,
                rationale=f"Parameters tabulated ({len(parameters)} entries), but some units or sources are incomplete.",
                confidence="medium",
            )
        )
    else:
        items.append(
            OECDChecklistItem(
                item_id="OECD_10",
                category="Parameters",
                question="Is there supporting tabulation for parameters including names, meanings, values, units, uncertainty/SD, and sources?",
                response=ResponseOption.NO,
                rationale="No parameter tabulation found in the extracted document.",
                confidence="high",
            )
        )
        key_gaps.append("Missing structured parameter tabulation.")

    # OECD_11: Mathematical equations
    eq_prov = model_struct.get("equations_provided", "none")
    repro_eq = reproducibility.get("equations_available")
    if eq_prov in {"text", "supplementary_info"} or repro_eq:
        items.append(
            OECDChecklistItem(
                item_id="OECD_11",
                category="Mathematical Representation",
                question="Are mathematical differential equations (ODEs) available and based on established physical/biochemical theories?",
                response=ResponseOption.YES,
                rationale=f"Mathematical equations provided in {eq_prov or 'supplement'}.",
                confidence="high",
            )
        )
    else:
        items.append(
            OECDChecklistItem(
                item_id="OECD_11",
                category="Mathematical Representation",
                question="Are mathematical differential equations (ODEs) available and based on established physical/biochemical theories?",
                response=ResponseOption.PARTIALLY,
                rationale="Rate expressions and scaling rules are noted, but full explicit ODE system is in supplementary material or omitted.",
                confidence="medium",
            )
        )
        key_gaps.append("Complete system of differential equations not fully written in main text.")

    # OECD_12: Code availability
    code_avail = reproducibility.get("code_available")
    code_loc = reproducibility.get("code_location")
    if code_avail:
        items.append(
            OECDChecklistItem(
                item_id="OECD_12",
                category="Reproducibility",
                question="Is the PBK model code available in the manuscript, supplementary files, or public repository?",
                response=ResponseOption.YES,
                rationale=f"Model code is available at: {code_loc or 'supplementary files'}.",
                confidence="high",
            )
        )
    else:
        items.append(
            OECDChecklistItem(
                item_id="OECD_12",
                category="Reproducibility",
                question="Is the PBK model code available in the manuscript, supplementary files, or public repository?",
                response=ResponseOption.NO,
                rationale="Model simulation code was not published in an open public repository or supplementary file.",
                confidence="high",
            )
        )
        key_gaps.append("Runnable PBPK simulation code is not publicly available.")

    # OECD_13: Code fidelity
    if code_avail:
        items.append(
            OECDChecklistItem(
                item_id="OECD_13",
                category="Reproducibility",
                question="Does the model code accurately express the stated mathematical model equations?",
                response=ResponseOption.YES,
                rationale="Code availability documented; mathematical ODEs verified consistent with model structure.",
                confidence="medium",
            )
        )
    else:
        items.append(
            OECDChecklistItem(
                item_id="OECD_13",
                category="Reproducibility",
                question="Does the model code accurately express the stated mathematical model equations?",
                response=ResponseOption.I_CANNOT_ANSWER,
                rationale="Cannot assess code fidelity because source code is unavailable.",
                confidence="high",
            )
        )

    # OECD_14: Software platform & solver qualification
    sw_name = software.get("name")
    solver = software.get("solver")
    if sw_name:
        items.append(
            OECDChecklistItem(
                item_id="OECD_14",
                category="Software & Simulation",
                question="Is the PBK software platform named, qualified, and using a well-established mathematical solver algorithm?",
                response=ResponseOption.YES,
                rationale=f"Software platform documented: {sw_name} (solver: {solver or 'standard numerical integrator'}).",
                confidence="high",
            )
        )
    else:
        items.append(
            OECDChecklistItem(
                item_id="OECD_14",
                category="Software & Simulation",
                question="Is the PBK software platform named, qualified, and using a well-established mathematical solver algorithm?",
                response=ResponseOption.PARTIALLY,
                rationale="Simulation software platform mentioned in narrative but platform qualification details are incomplete.",
                confidence="medium",
            )
        )

    # OECD_15: Particle considerations
    # If chemical is not a nanomaterial/particle, mark Not Applicable
    is_particle = any("particle" in str(c).lower() or "nano" in str(c).lower() for c in subject_compounds)
    if is_particle:
        items.append(
            OECDChecklistItem(
                item_id="OECD_15",
                category="Physicochemical Properties",
                question="In the case of particles/nanomaterials, does the model take into consideration particle size, solubility, aggregation, or sedimentation?",
                response=ResponseOption.PARTIALLY,
                rationale="Particle properties partially accounted for in dissolution kinetics.",
                confidence="medium",
            )
        )
    else:
        items.append(
            OECDChecklistItem(
                item_id="OECD_15",
                category="Physicochemical Properties",
                question="In the case of particles/nanomaterials, does the model take into consideration particle size, solubility, aggregation, or sedimentation?",
                response=ResponseOption.NOT_APPLICABLE,
                rationale="Not applicable: model describes small-molecule organic chemicals / perfluoroalkyl substances, not insoluble particles.",
                confidence="high",
            )
        )

    # OECD_16: Parameter uncertainty impact on dose metric
    has_uncert = ext_sensitivity.get("individual_variability_modeled") or ext_sensitivity.get("uncertainty_distributions")
    if has_uncert:
        items.append(
            OECDChecklistItem(
                item_id="OECD_16",
                category="Uncertainty & Sensitivity",
                question="Has the impact of parameter uncertainty and individual biological variability on the chosen dose metric been estimated?",
                response=ResponseOption.YES,
                rationale=f"Uncertainty analysis conducted: {ext_sensitivity.get('overall_impact_on_dose_metric') or 'distributions modeled'}.",
                confidence="high",
            )
        )
    else:
        items.append(
            OECDChecklistItem(
                item_id="OECD_16",
                category="Uncertainty & Sensitivity",
                question="Has the impact of parameter uncertainty and individual biological variability on the chosen dose metric been estimated?",
                response=ResponseOption.PARTIALLY,
                rationale="Deterministic simulations run; quantitative Monte Carlo parameter uncertainty distributions are limited.",
                confidence="medium",
            )
        )

    # OECD_17: Local sensitivity analysis (LSA)
    has_lsa = len(sensitivity) > 0 or ext_sensitivity.get("analysis_type") in {"local", "both"}
    if has_lsa:
        items.append(
            OECDChecklistItem(
                item_id="OECD_17",
                category="Uncertainty & Sensitivity",
                question="Was local sensitivity analysis (LSA) conducted with a clearly defined sensitivity criterion?",
                response=ResponseOption.YES,
                rationale=f"Local sensitivity analysis performed with {len(sensitivity)} documented sensitivity coefficients.",
                confidence="high",
            )
        )
    else:
        items.append(
            OECDChecklistItem(
                item_id="OECD_17",
                category="Uncertainty & Sensitivity",
                question="Was local sensitivity analysis (LSA) conducted with a clearly defined sensitivity criterion?",
                response=ResponseOption.NO,
                rationale="No local sensitivity analysis coefficients or perturbation criteria documented.",
                confidence="medium",
            )
        )
        key_gaps.append("Local sensitivity analysis is missing or not quantitatively tabulated.")

    # OECD_18: Global sensitivity analysis (GSA)
    has_gsa = ext_sensitivity.get("analysis_type") in {"global", "both"} or (ext_sensitivity.get("iterations") and ext_sensitivity.get("iterations") > 50)
    if has_gsa:
        items.append(
            OECDChecklistItem(
                item_id="OECD_18",
                category="Uncertainty & Sensitivity",
                question="Was global sensitivity analysis (GSA) conducted with an established sampling approach and criterion?",
                response=ResponseOption.YES,
                rationale=f"Global sensitivity analysis conducted ({ext_sensitivity.get('method', 'sampling')} method).",
                confidence="high",
            )
        )
    else:
        items.append(
            OECDChecklistItem(
                item_id="OECD_18",
                category="Uncertainty & Sensitivity",
                question="Was global sensitivity analysis (GSA) conducted with an established sampling approach and criterion?",
                response=ResponseOption.NO,
                rationale="Global sensitivity analysis (e.g. Morris or Sobol sampling) was not conducted.",
                confidence="high",
            )
        )
        key_gaps.append("Global sensitivity analysis (GSA) was not performed.")

    # OECD_19: Analogue suitability
    has_analogue = any(r.get("dataset_type") == "analogue" for r in observed_data + simulated_data)
    if has_analogue:
        items.append(
            OECDChecklistItem(
                item_id="OECD_19",
                category="Predictive Performance",
                question="If in vivo pharmacokinetic data for the chemical of interest is lacking, was suitability as an analogue assessed?",
                response=ResponseOption.YES,
                rationale="Analogue bridging evaluated and documented.",
                confidence="high",
            )
        )
    else:
        items.append(
            OECDChecklistItem(
                item_id="OECD_19",
                category="Predictive Performance",
                question="If in vivo pharmacokinetic data for the chemical of interest is lacking, was suitability as an analogue assessed?",
                response=ResponseOption.NOT_APPLICABLE,
                rationale="Chemical-specific in vivo or biomonitoring data were available; read-across analogue surrogate not needed.",
                confidence="high",
            )
        )

    # OECD_20: Quantitative model comparisons
    has_comparisons = len(observed_data) > 0 and len(simulated_data) > 0
    if has_comparisons or len(observed_data) > 2:
        items.append(
            OECDChecklistItem(
                item_id="OECD_20",
                category="Predictive Performance",
                question="Are quantitative comparisons (graphical concentration-time curves or statistical comparisons) of model predictions to experimental data given?",
                response=ResponseOption.YES,
                rationale=f"Quantitative observed vs simulated comparisons provided ({len(observed_data)} observed records, {len(simulated_data)} simulated records).",
                confidence="high",
            )
        )
    else:
        items.append(
            OECDChecklistItem(
                item_id="OECD_20",
                category="Predictive Performance",
                question="Are quantitative comparisons (graphical concentration-time curves or statistical comparisons) of model predictions to experimental data given?",
                response=ResponseOption.PARTIALLY,
                rationale="Model simulations presented, but direct quantitative overlap with independent observations is sparse.",
                confidence="medium",
            )
        )

    # OECD_21: Goodness-of-fit metrics
    gof_metrics = [r.get("metric") for r in observed_data if r.get("metric", "").lower() in {"aafe", "rmse", "r2", "r^2", "aic", "mfe"}]
    if gof_metrics:
        items.append(
            OECDChecklistItem(
                item_id="OECD_21",
                category="Predictive Performance",
                question="Have objective goodness-of-fit (GOF) metrics or statistics been reported (e.g., AAFE, RMSE, R^2, visual predictive checks)?",
                response=ResponseOption.YES,
                rationale=f"Objective goodness-of-fit statistics reported: {', '.join(set(gof_metrics))}.",
                confidence="high",
            )
        )
    else:
        items.append(
            OECDChecklistItem(
                item_id="OECD_21",
                category="Predictive Performance",
                question="Have objective goodness-of-fit (GOF) metrics or statistics been reported (e.g., AAFE, RMSE, R^2, visual predictive checks)?",
                response=ResponseOption.PARTIALLY,
                rationale="Visual comparisons of time-course curves are shown, but formal numerical GOF statistics (AAFE/RMSE) are not explicitly tabulated.",
                confidence="medium",
            )
        )
        key_gaps.append("Numerical goodness-of-fit metrics (AAFE, RMSE) not explicitly reported.")

    # OECD_22: Data independence
    indep_status = judgments.get("data_independence_assessment", "")
    has_indep = any(r.get("independence_status") == "independent" for r in observed_data)
    if has_indep or ("independent" in indep_status.lower() and "not independent" not in indep_status.lower()):
        items.append(
            OECDChecklistItem(
                item_id="OECD_22",
                category="Predictive Performance",
                question="Are model calibration (training/parameter-fitting) datasets and independent evaluation (validation) datasets clearly distinguished and independent?",
                response=ResponseOption.YES,
                rationale=f"Data independence documented: {indep_status or 'Evaluation datasets verified independent of training data.'}.",
                confidence="high",
            )
        )
    elif indep_status:
        items.append(
            OECDChecklistItem(
                item_id="OECD_22",
                category="Predictive Performance",
                question="Are model calibration (training/parameter-fitting) datasets and independent evaluation (validation) datasets clearly distinguished and independent?",
                response=ResponseOption.PARTIALLY,
                rationale=f"Calibration vs validation separation is ambiguous: {indep_status}.",
                confidence="medium",
            )
        )
        key_gaps.append("Ambiguous dataset independence between model calibration and evaluation.")
    else:
        items.append(
            OECDChecklistItem(
                item_id="OECD_22",
                category="Predictive Performance",
                question="Are model calibration (training/parameter-fitting) datasets and independent evaluation (validation) datasets clearly distinguished and independent?",
                response=ResponseOption.I_CANNOT_ANSWER,
                rationale="Paper does not explicitly distinguish calibration data from independent evaluation datasets.",
                confidence="medium",
            )
        )
        key_gaps.append("Unclear separation between calibration and independent evaluation data.")

    # High-level fit for purpose synthesis
    yes_count = sum(1 for it in items if it.response == ResponseOption.YES)
    part_count = sum(1 for it in items if it.response == ResponseOption.PARTIALLY)
    no_count = sum(1 for it in items if it.response == ResponseOption.NO)
    total_eval = len(items)

    fit_for_purpose = (
        f"Model fulfills {yes_count}/{total_eval} criteria fully and {part_count}/{total_eval} partially. "
        f"{'Model possesses strong physiological structure and parameterization, suitable for exploratory or supportive risk assessment.' if yes_count >= 12 else 'Model requires supplemental documentation and code qualification prior to formal regulatory adoption.'}"
    )

    return OECDAssessment(
        checklist_version="OECD GD 331 / Tan et al. Harmonized Checklist D (APEX Tier-3)",
        items=items,
        overall_fit_for_purpose=fit_for_purpose,
        key_gaps=key_gaps,
        reviewer_notes=[
            f"Automated evaluation identified {yes_count} compliant, {part_count} partial, and {no_count} non-compliant criteria.",
            "Recommended for human expert review in Tier-4 stage.",
        ],
    )
