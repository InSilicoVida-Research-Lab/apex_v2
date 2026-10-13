"""Versioned curated PBPK reference corpus and deterministic evaluator.

This module deliberately has no model or network dependency.  Reference data
is used for validation and quality reporting only; it is never passed to live
extraction prompts.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import re
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

from pydantic import BaseModel, Field

from pk_pipeline.schemas import ExtractedDocument


REPORT_VERSION = "1.0"
MATCHER_VERSION = "1.0"
DEFAULT_RELATIVE_TOLERANCE = 0.05
DEFAULT_ABSOLUTE_TOLERANCE = 1e-9


class CorpusError(ValueError):
    """Raised when corpus data or an evaluation input is invalid."""


class ReferencePaper(BaseModel):
    paper_id: str
    pdf_path: str
    reference_path: str
    title: str
    year: int
    expected_parameter_count: int = Field(ge=0)
    pdf_sha256: str
    reference_sha256: str


class CorpusManifest(BaseModel):
    corpus_version: str
    papers: list[ReferencePaper]


@dataclass(frozen=True)
class MatchProposal:
    prediction_index: int
    reference_index: int
    score: int


def default_corpus_dir() -> Path:
    return Path(__file__).resolve().parent / "pbpk_data"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CorpusError(f"Could not read JSON file '{path}': {exc}") from exc
    if not isinstance(value, dict):
        raise CorpusError(f"JSON document '{path}' must contain an object at its root")
    return value


def load_manifest(corpus_dir: Optional[Path | str] = None) -> CorpusManifest:
    root = Path(corpus_dir) if corpus_dir else default_corpus_dir()
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        raise CorpusError(f"Corpus manifest not found: {manifest_path}")
    manifest = CorpusManifest.model_validate(_read_json(manifest_path))
    ids = [paper.paper_id for paper in manifest.papers]
    if len(ids) != len(set(ids)):
        raise CorpusError("Corpus manifest contains duplicate paper_id values")
    return manifest


def list_papers(corpus_dir: Optional[Path | str] = None) -> list[ReferencePaper]:
    return load_manifest(corpus_dir).papers


def _paper_paths(paper: ReferencePaper, corpus_dir: Optional[Path | str] = None) -> tuple[Path, Path]:
    root = Path(corpus_dir) if corpus_dir else default_corpus_dir()
    return root / paper.pdf_path, root / paper.reference_path


def get_paper(paper_id: str, corpus_dir: Optional[Path | str] = None) -> ReferencePaper:
    for paper in list_papers(corpus_dir):
        if paper.paper_id == paper_id:
            return paper
    choices = ", ".join(p.paper_id for p in list_papers(corpus_dir))
    raise CorpusError(f"Unknown reference '{paper_id}'. Available paper IDs: {choices}")


def load_reference(paper_id: str, corpus_dir: Optional[Path | str] = None) -> ExtractedDocument:
    paper = get_paper(paper_id, corpus_dir)
    _, reference_path = _paper_paths(paper, corpus_dir)
    if not reference_path.is_file():
        raise CorpusError(f"Reference JSON missing for '{paper_id}': {reference_path}")
    try:
        return ExtractedDocument.model_validate(_read_json(reference_path))
    except Exception as exc:
        raise CorpusError(f"Reference JSON for '{paper_id}' violates ExtractedDocument: {exc}") from exc


def validate_corpus(
    corpus_dir: Optional[Path | str] = None,
    *,
    raise_on_error: bool = True,
) -> dict[str, Any]:
    """Validate every reference pair, manifest hash, and canonical document."""
    manifest = load_manifest(corpus_dir)
    reports: list[dict[str, Any]] = []
    total_parameters = 0
    failures: list[str] = []
    for paper in manifest.papers:
        pdf_path, reference_path = _paper_paths(paper, corpus_dir)
        errors: list[str] = []
        document: Optional[ExtractedDocument] = None
        if not pdf_path.is_file():
            errors.append(f"missing PDF: {pdf_path}")
        elif _sha256(pdf_path) != paper.pdf_sha256:
            errors.append("PDF SHA-256 does not match manifest")
        if not reference_path.is_file():
            errors.append(f"missing reference JSON: {reference_path}")
        elif _sha256(reference_path) != paper.reference_sha256:
            errors.append("reference JSON SHA-256 does not match manifest")
        if not errors:
            try:
                document = ExtractedDocument.model_validate(_read_json(reference_path))
                parameter_count = len(document.model_parameters)
                if parameter_count != paper.expected_parameter_count:
                    errors.append(
                        f"expected {paper.expected_parameter_count} model_parameters, found {parameter_count}"
                    )
                if document.page_metadata.title != paper.title:
                    errors.append("manifest title does not match reference page_metadata.title")
                if document.page_metadata.year != paper.year:
                    errors.append("manifest year does not match reference page_metadata.year")
                total_parameters += parameter_count
            except Exception as exc:
                errors.append(f"invalid reference JSON: {exc}")
        report = {
            "paper_id": paper.paper_id,
            "valid": not errors,
            "parameter_count": len(document.model_parameters) if document else 0,
            "errors": errors,
        }
        reports.append(report)
        failures.extend(f"{paper.paper_id}: {error}" for error in errors)
    result = {
        "corpus_version": manifest.corpus_version,
        "paper_count": len(manifest.papers),
        "total_parameters": total_parameters,
        "valid": not failures,
        "papers": reports,
    }
    if failures and raise_on_error:
        raise CorpusError("Corpus validation failed:\n- " + "\n- ".join(failures))
    return result


def _normal_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).strip().casefold())


def _normal_identifier(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", _normal_text(value))


def _normal_unit(value: Any) -> str:
    unit = _normal_text(value).replace("μ", "u").replace("µ", "u")
    unit = unit.replace(" ", "").replace("*", "")
    unit = re.sub(r"([a-z]+)\^-1", r"/\1", unit)
    unit = unit.replace("per", "/")
    return unit


def _record_id(parameter: dict[str, Any], index: int) -> str:
    return str(parameter.get("parameter_id") or f"index:{index}")


def _context_value(parameter: dict[str, Any], field: str) -> str:
    value = (parameter.get("context") or {}).get(field)
    if field == "formulation" and isinstance(value, list):
        return "|".join(sorted(_normal_identifier(item) for item in value))
    return _normal_identifier(value)


def _parameter_identifiers(parameter: dict[str, Any]) -> tuple[set[str], set[str]]:
    names = {
        _normal_identifier(parameter.get(key))
        for key in ("parameter_name_standardized", "parameter_name_original")
        if _normal_identifier(parameter.get(key))
    }
    symbols = {
        _normal_identifier(parameter.get(key))
        for key in ("symbol_standardized", "symbol_original")
        if _normal_identifier(parameter.get(key))
    }
    return names, symbols


def _candidate_score(reference: dict[str, Any], prediction: dict[str, Any]) -> Optional[int]:
    ref_names, ref_symbols = _parameter_identifiers(reference)
    pred_names, pred_symbols = _parameter_identifiers(prediction)
    name_match = bool(ref_names & pred_names)
    symbol_match = bool(ref_symbols & pred_symbols)
    if not name_match and not symbol_match:
        return None

    # Conflicting known biological contexts make a candidate invalid. Missing
    # context lowers confidence but is not treated as a contradiction.
    context_fields = ("compound", "species", "life_stage", "population", "organ", "formulation")
    score = 8 if name_match else 0
    score += 7 if symbol_match else 0
    for field in context_fields:
        ref_value = _context_value(reference, field)
        pred_value = _context_value(prediction, field)
        if ref_value and pred_value:
            if ref_value != pred_value:
                return None
            score += 2
    ref_table = _normal_identifier((reference.get("provenance") or {}).get("source_table"))
    pred_table = _normal_identifier((prediction.get("provenance") or {}).get("source_table"))
    if ref_table and pred_table and ref_table == pred_table:
        score += 2
    return score


def _parameter_matches(
    reference_parameters: list[dict[str, Any]],
    predicted_parameters: list[dict[str, Any]],
) -> tuple[list[MatchProposal], list[dict[str, Any]], set[int], set[int]]:
    proposals: list[MatchProposal] = []
    ambiguities: list[dict[str, Any]] = []
    ambiguous_predictions: set[int] = set()
    for pred_idx, prediction in enumerate(predicted_parameters):
        candidates = [
            MatchProposal(pred_idx, ref_idx, score)
            for ref_idx, reference in enumerate(reference_parameters)
            if (score := _candidate_score(reference, prediction)) is not None
        ]
        if not candidates:
            continue
        best_score = max(candidate.score for candidate in candidates)
        best = [candidate for candidate in candidates if candidate.score == best_score]
        if len(best) > 1:
            ambiguous_predictions.add(pred_idx)
            ambiguities.append({
                "predicted_parameter_id": _record_id(prediction, pred_idx),
                "candidate_reference_parameter_ids": [
                    _record_id(reference_parameters[candidate.reference_index], candidate.reference_index)
                    for candidate in best
                ],
                "score": best_score,
            })
            continue
        proposals.append(best[0])

    matches: list[MatchProposal] = []
    used_reference: set[int] = set()
    used_prediction: set[int] = set()
    for proposal in sorted(proposals, key=lambda item: (-item.score, item.reference_index, item.prediction_index)):
        if proposal.reference_index in used_reference or proposal.prediction_index in used_prediction:
            continue
        matches.append(proposal)
        used_reference.add(proposal.reference_index)
        used_prediction.add(proposal.prediction_index)
    return matches, ambiguities, used_reference, used_prediction | ambiguous_predictions


def _field_result(expected: Any, actual: Any, *, normalizer=_normal_text) -> dict[str, Any]:
    if expected is None and actual is None:
        return {"state": "not_compared", "expected": expected, "actual": actual}
    if normalizer(expected) == normalizer(actual):
        return {"state": "match", "expected": expected, "actual": actual}
    return {"state": "mismatch", "expected": expected, "actual": actual}


def _numeric_result(expected: Any, actual: Any, relative_tolerance: float, absolute_tolerance: float) -> dict[str, Any]:
    if expected is None and actual is None:
        return {"state": "not_compared", "expected": expected, "actual": actual}
    if expected is None or actual is None:
        return {"state": "mismatch", "expected": expected, "actual": actual}
    try:
        is_match = math.isclose(float(expected), float(actual), rel_tol=relative_tolerance, abs_tol=absolute_tolerance)
    except (TypeError, ValueError):
        is_match = False
    return {"state": "match" if is_match else "mismatch", "expected": expected, "actual": actual}


def _compare_parameter(
    reference: dict[str, Any],
    prediction: dict[str, Any],
    relative_tolerance: float,
    absolute_tolerance: float,
) -> dict[str, dict[str, Any]]:
    ref_context = reference.get("context") or {}
    pred_context = prediction.get("context") or {}
    ref_quant = reference.get("quantitative_data") or {}
    pred_quant = prediction.get("quantitative_data") or {}
    ref_provenance = reference.get("provenance") or {}
    pred_provenance = prediction.get("provenance") or {}
    fields: dict[str, dict[str, Any]] = {
        "parameter_class": _field_result(reference.get("parameter_class"), prediction.get("parameter_class")),
        "parameter_subclass": _field_result(reference.get("parameter_subclass"), prediction.get("parameter_subclass")),
        "parameter_name": _field_result(
            reference.get("parameter_name_standardized") or reference.get("parameter_name_original"),
            prediction.get("parameter_name_standardized") or prediction.get("parameter_name_original"),
            normalizer=_normal_identifier,
        ),
        "symbol": _field_result(
            reference.get("symbol_standardized") or reference.get("symbol_original"),
            prediction.get("symbol_standardized") or prediction.get("symbol_original"),
            normalizer=_normal_identifier,
        ),
        "value": _numeric_result(ref_quant.get("value"), pred_quant.get("value"), relative_tolerance, absolute_tolerance),
        "unit": _field_result(
            ref_quant.get("unit_standardized") or ref_quant.get("unit_original"),
            pred_quant.get("unit_standardized") or pred_quant.get("unit_original"),
            normalizer=_normal_unit,
        ),
        "provenance_status": _field_result(ref_provenance.get("status"), pred_provenance.get("status")),
        "source_table": _field_result(ref_provenance.get("source_table"), pred_provenance.get("source_table"), normalizer=_normal_identifier),
        "source_page": _field_result(ref_provenance.get("source_page"), pred_provenance.get("source_page"), normalizer=lambda value: str(value)),
    }
    for field in ("compound", "species", "life_stage", "population", "organ", "formulation"):
        fields[f"context.{field}"] = _field_result(
            ref_context.get(field), pred_context.get(field), normalizer=lambda value: _context_value({"context": {field: value}}, field)
        )
    return fields


def _field_summary(matches: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    counts: dict[str, Counter] = {}
    for match in matches:
        for name, result in match["fields"].items():
            counts.setdefault(name, Counter())[result["state"]] += 1
    return {
        name: {
            "compared": counter["match"] + counter["mismatch"],
            "matched": counter["match"],
            "mismatched": counter["mismatch"],
            "not_compared": counter["not_compared"],
            "agreement": (
                counter["match"] / (counter["match"] + counter["mismatch"])
                if counter["match"] + counter["mismatch"] else None
            ),
        }
        for name, counter in sorted(counts.items())
    }


def _json_identity(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _collection_agreement(reference: list[Any], prediction: list[Any]) -> dict[str, Any]:
    ref_counts = Counter(_json_identity(value) for value in reference)
    pred_counts = Counter(_json_identity(value) for value in prediction)
    matched = sum((ref_counts & pred_counts).values())
    return {"reference_count": len(reference), "prediction_count": len(prediction), "matched": matched}


def _document_agreement(reference: dict[str, Any], prediction: dict[str, Any]) -> dict[str, Any]:
    metadata_fields = {
        field: _field_result((reference.get("page_metadata") or {}).get(field), (prediction.get("page_metadata") or {}).get(field), normalizer=lambda value: _json_identity(value) if isinstance(value, list) else _normal_text(value))
        for field in ("title", "authors", "journal", "year")
    }
    classification = _field_result(
        (reference.get("model_classification") or {}).get("model_type"),
        (prediction.get("model_classification") or {}).get("model_type"),
    )
    context_fields = {
        field: _field_result((reference.get("model_context") or {}).get(field), (prediction.get("model_context") or {}).get(field))
        for field in ("model_origin", "stated_purpose", "dose_metric")
    }
    structure_ref = reference.get("model_structure") or {}
    structure_pred = prediction.get("model_structure") or {}
    basis_ref = reference.get("biological_basis") or {}
    basis_pred = prediction.get("biological_basis") or {}
    return {
        "metadata": metadata_fields,
        "model_classification": classification,
        "model_context": context_fields,
        "model_structure": {
            "reported_compartment_count": _field_result(structure_ref.get("reported_compartment_count"), structure_pred.get("reported_compartment_count"), normalizer=lambda value: str(value)),
            "compartments": _collection_agreement(structure_ref.get("compartments", []), structure_pred.get("compartments", [])),
            "connections": _collection_agreement(structure_ref.get("connections", []), structure_pred.get("connections", [])),
        },
        "biological_basis": {
            "adme_determinants": _collection_agreement(basis_ref.get("adme_determinants", []), basis_pred.get("adme_determinants", [])),
            "specialized_mechanisms": _collection_agreement(basis_ref.get("specialized_mechanisms", []), basis_pred.get("specialized_mechanisms", [])),
            "stated_assumptions": _collection_agreement(basis_ref.get("stated_assumptions", []), basis_pred.get("stated_assumptions", [])),
        },
        "collections": {
            name: _collection_agreement(reference.get(name, []), prediction.get(name, []))
            for name in (
                "metabolic_pathways", "dosing", "observed_data", "simulated_data",
                "formulation_characterization", "qualitative_findings",
                "parameter_mentions_without_values", "sensitivity_analysis",
            )
        },
    }


def _prediction_document(raw: dict[str, Any]) -> ExtractedDocument:
    """Load a canonical prediction while allowing the empty-output failure case."""
    prepared = copy.deepcopy(raw)
    prepared.setdefault("model_parameters", [])
    params = prepared["model_parameters"]
    prepared.setdefault("system_specific_parameters", [p for p in params if p.get("parameter_class") == "physiological"])
    prepared.setdefault("compound_specific_parameters", [p for p in params if p.get("parameter_class") != "physiological"])
    return ExtractedDocument.model_validate(prepared, context={"allow_empty_parameters": True})


def evaluate_documents(
    reference: ExtractedDocument,
    prediction: ExtractedDocument,
    *,
    paper_id: str,
    corpus_version: str,
    reference_hash: Optional[str] = None,
    prediction_hash: Optional[str] = None,
    relative_tolerance: float = DEFAULT_RELATIVE_TOLERANCE,
    absolute_tolerance: float = DEFAULT_ABSOLUTE_TOLERANCE,
) -> dict[str, Any]:
    reference_data = reference.model_dump(mode="json")
    prediction_data = prediction.model_dump(mode="json")
    ref_params = reference_data["model_parameters"]
    pred_params = prediction_data["model_parameters"]
    proposals, ambiguities, used_ref, used_pred = _parameter_matches(ref_params, pred_params)
    matches = []
    for proposal in proposals:
        ref_param = ref_params[proposal.reference_index]
        pred_param = pred_params[proposal.prediction_index]
        matches.append({
            "reference_parameter_id": _record_id(ref_param, proposal.reference_index),
            "predicted_parameter_id": _record_id(pred_param, proposal.prediction_index),
            "score": proposal.score,
            "fields": _compare_parameter(ref_param, pred_param, relative_tolerance, absolute_tolerance),
        })
    matched_count = len(matches)
    precision = matched_count / len(pred_params) if pred_params else 0.0
    recall = matched_count / len(ref_params) if ref_params else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "report_version": REPORT_VERSION,
        "matcher_version": MATCHER_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "corpus_version": corpus_version,
        "paper_id": paper_id,
        "inputs": {"reference_sha256": reference_hash, "prediction_sha256": prediction_hash},
        "tolerances": {"relative": relative_tolerance, "absolute": absolute_tolerance},
        "parameter_metrics": {
            "reference_count": len(ref_params),
            "prediction_count": len(pred_params),
            "matched_count": matched_count,
            "precision": precision,
            "recall": recall,
            "f1": f1,
        },
        "field_agreement": _field_summary(matches),
        "matches": matches,
        "unmatched_reference_parameter_ids": [
            _record_id(parameter, idx) for idx, parameter in enumerate(ref_params) if idx not in used_ref
        ],
        "unmatched_predicted_parameter_ids": [
            _record_id(parameter, idx) for idx, parameter in enumerate(pred_params) if idx not in used_pred
        ],
        "ambiguous_matches": ambiguities,
        "document_agreement": _document_agreement(reference_data, prediction_data),
    }


def evaluate_file(
    paper_id: str,
    prediction_path: Path | str,
    *,
    corpus_dir: Optional[Path | str] = None,
    relative_tolerance: float = DEFAULT_RELATIVE_TOLERANCE,
    absolute_tolerance: float = DEFAULT_ABSOLUTE_TOLERANCE,
) -> dict[str, Any]:
    paper = get_paper(paper_id, corpus_dir)
    _, reference_path = _paper_paths(paper, corpus_dir)
    prediction_file = Path(prediction_path)
    if not prediction_file.is_file():
        raise CorpusError(f"Prediction JSON not found: {prediction_file}")
    reference = load_reference(paper_id, corpus_dir)
    try:
        prediction = _prediction_document(_read_json(prediction_file))
    except Exception as exc:
        raise CorpusError(f"Prediction JSON violates ExtractedDocument: {exc}") from exc
    return evaluate_documents(
        reference,
        prediction,
        paper_id=paper_id,
        corpus_version=load_manifest(corpus_dir).corpus_version,
        reference_hash=_sha256(reference_path),
        prediction_hash=_sha256(prediction_file),
        relative_tolerance=relative_tolerance,
        absolute_tolerance=absolute_tolerance,
    )


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _load_predictions_manifest(path: Path) -> dict[str, str]:
    raw = _read_json(path)
    entries = raw.get("predictions", raw)
    if isinstance(entries, dict):
        return {str(paper_id): str(prediction_path) for paper_id, prediction_path in entries.items()}
    if isinstance(entries, list):
        try:
            return {str(entry["paper_id"]): str(entry["prediction_path"]) for entry in entries}
        except (TypeError, KeyError) as exc:
            raise CorpusError("Prediction manifest list entries require paper_id and prediction_path") from exc
    raise CorpusError("Prediction manifest must be an object or contain a predictions object/list")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Validate and evaluate the curated PBPK reference corpus")
    parser.add_argument("--corpus-dir", type=Path, default=default_corpus_dir(), help="Corpus directory (default: pk_pipeline/pbpk_data)")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("list", help="List available reference paper IDs")
    subparsers.add_parser("validate", help="Validate corpus files, hashes, and schemas")
    evaluate_parser = subparsers.add_parser("evaluate", help="Evaluate one prediction JSON against one reference")
    evaluate_parser.add_argument("--reference", required=True, help="Reference paper ID")
    evaluate_parser.add_argument("--prediction", type=Path, required=True, help="Pipeline output JSON")
    evaluate_parser.add_argument("--out", type=Path, required=True, help="Evaluation report JSON")
    evaluate_parser.add_argument("--relative-tolerance", type=float, default=DEFAULT_RELATIVE_TOLERANCE)
    evaluate_parser.add_argument("--absolute-tolerance", type=float, default=DEFAULT_ABSOLUTE_TOLERANCE)
    all_parser = subparsers.add_parser("evaluate-all", help="Evaluate predictions listed in a manifest")
    all_parser.add_argument("--predictions-manifest", type=Path, required=True)
    all_parser.add_argument("--out", type=Path, required=True)
    all_parser.add_argument("--relative-tolerance", type=float, default=DEFAULT_RELATIVE_TOLERANCE)
    all_parser.add_argument("--absolute-tolerance", type=float, default=DEFAULT_ABSOLUTE_TOLERANCE)
    args = parser.parse_args(argv)
    try:
        if args.command == "list":
            result: dict[str, Any] = {"papers": [paper.model_dump() for paper in list_papers(args.corpus_dir)]}
        elif args.command == "validate":
            result = validate_corpus(args.corpus_dir)
        elif args.command == "evaluate":
            result = evaluate_file(
                args.reference, args.prediction, corpus_dir=args.corpus_dir,
                relative_tolerance=args.relative_tolerance, absolute_tolerance=args.absolute_tolerance,
            )
            _write_json(args.out, result)
        else:
            predictions = _load_predictions_manifest(args.predictions_manifest)
            reports = {
                paper_id: evaluate_file(
                    paper_id, prediction_path, corpus_dir=args.corpus_dir,
                    relative_tolerance=args.relative_tolerance, absolute_tolerance=args.absolute_tolerance,
                )
                for paper_id, prediction_path in predictions.items()
            }
            result = {
                "report_version": REPORT_VERSION,
                "corpus_version": load_manifest(args.corpus_dir).corpus_version,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "reports": reports,
            }
            _write_json(args.out, result)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except CorpusError as exc:
        print(f"Corpus error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
