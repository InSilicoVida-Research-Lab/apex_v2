"""
pk_pipeline/verifier.py
=======================
Two-tier post-extraction verification system.

Tier 1 — Deterministic Rule Engine (~0-5ms, zero GPU cost)
    Fast Python rules that flag obvious anomalies:
    - Biologically implausible values
    - Missing required fields
    - Unit consistency issues
    - Duplicate/conflicting entries
    - Species/compound cross-contamination

Tier 2 — Optional LLM Critic (async, only on flagged entries)
    Uses a smaller/faster LLM to review only the flagged parameters.
    This is OPTIONAL and OFF by default. It does NOT block the main pipeline.

Design Principle: Verification adds near-ZERO latency.
    - Tier 1 is pure Python loops — completed in <10ms for any realistic document.
    - Tier 2 is async: results are appended to the output as `verification_report`
      and never block the main JSON write.
"""

from __future__ import annotations

import re
import time
import logging
from typing import Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger("pk_pipeline")

# ---------------------------------------------------------------------------
# Biological plausibility bounds for common PK parameter symbols/names
# Each entry: (name_fragments, unit_fragments, lo, hi)
# Values outside [lo, hi] get flagged as suspicious (not necessarily wrong).
# ---------------------------------------------------------------------------
_PLAUSIBILITY_RULES: list[tuple[list[str], list[str], float, float]] = [
    # Volumes (L or L/kg)
    (["volume", "vd", "vc", "vp", "vcc", "vpc"],      ["l/kg", "l kg"],   0.001, 500.0),
    (["volume", "vd", "vc", "vp", "vcc", "vpc"],      ["l", "litre"],     0.001, 500.0),
    # Clearances (L/h or L/h/kg)
    (["clearance", "cl", "clr", "clh", "q"],          ["l/h", "l/day"],   0.0,   5000.0),
    (["clearance", "cl", "clr", "clh", "q"],          ["ml/min"],         0.0,   5000.0),
    # Half-lives (h)
    (["half", "t1/2", "t1/2", "t_half", "thalf"],     ["h", "hr", "day"], 0.001, 50000.0),
    # Rate constants (1/h)
    (["rate", "ka", "kel", "k12", "k21", "k10"],      ["1/h", "h-1"],     0.0,   100.0),
    # Bioavailability (unitless fraction)
    (["bioavailability", "fraction", "fa", "fg"],     ["%", "fraction"],  0.0,   100.0),
    # Protein binding (fraction bound)
    (["binding", "fu", "unbound", "fraction unbound"],["%", "fraction"],  0.0,   100.0),
    # AUC (microgram*h/mL)
    (["auc"],                                          ["ug", "ng", "microg"], 0.0, 1e8),
    # Cmax (ug/mL or ng/mL)
    (["cmax", "c_max", "peak"],                        ["ug", "ng", "microg"], 0.0, 1e6),
]

# Known common PK parameter abbreviations for symbol completeness check
_KNOWN_SYMBOLS = {
    "vd", "vc", "vp", "vpc", "vcc", "cl", "clr", "clh", "q",
    "ka", "kel", "k10", "k12", "k21", "t1/2", "auc", "cmax",
    "tmax", "fu", "fa", "fg", "mrt", "ke", "kabs", "km", "vmax",
    "clint", "clp", "clm", "clrenal", "clhepatic"
}


# ---------------------------------------------------------------------------
# Verification result dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ParameterFlag:
    """Represents a single verification flag on one parameter."""
    param_index: int
    param_name: str
    severity: str          # "warning" | "error"
    rule: str              # Short rule ID
    message: str           # Human-readable explanation
    suggested_fix: Optional[str] = None


@dataclass
class VerificationReport:
    """Full verification report attached to the document output."""
    tier: int                              # 1 = rule-based only, 2 = +LLM critic
    elapsed_ms: float = 0.0
    total_parameters: int = 0
    flagged_count: int = 0
    error_count: int = 0
    warning_count: int = 0
    flags: list = field(default_factory=list)
    summary: str = ""
    clean: bool = True                    # True if no errors/warnings found

    def to_dict(self) -> dict:
        return {
            "tier": self.tier,
            "elapsed_ms": round(self.elapsed_ms, 2),
            "total_parameters": self.total_parameters,
            "flagged_count": self.flagged_count,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "clean": self.clean,
            "summary": self.summary,
            "flags": [
                {
                    "param_index": f.param_index,
                    "param_name": f.param_name,
                    "severity": f.severity,
                    "rule": f.rule,
                    "message": f.message,
                    "suggested_fix": f.suggested_fix,
                }
                for f in self.flags
            ],
        }


# ---------------------------------------------------------------------------
# Tier 1: Deterministic Rule Engine
# ---------------------------------------------------------------------------

class Tier1Verifier:
    """
    Pure-Python rule engine. Runs in <5ms for any document.
    No GPU, no network, no model loading.
    """

    def verify(self, document: dict) -> VerificationReport:
        t0 = time.monotonic()
        params: list[dict] = document.get("parameters", [])
        flags: list[ParameterFlag] = []

        for i, p in enumerate(params):
            name = p.get("parameter_name", "")
            symbol = p.get("symbol", "") or ""
            ctx = p.get("context", {}) or {}
            qdata = p.get("quantitative_data", {}) or {}
            prov = p.get("provenance", {}) or {}

            # Rule 1: Missing parameter_name
            if not name or name.strip() == "":
                flags.append(ParameterFlag(
                    param_index=i, param_name="<UNNAMED>",
                    severity="error", rule="MISSING_NAME",
                    message="parameter_name is empty or null.",
                    suggested_fix="Provide a descriptive name or the printed symbol."
                ))

            # Rule 2: Missing compound
            compound = ctx.get("compound")
            if not compound:
                flags.append(ParameterFlag(
                    param_index=i, param_name=name,
                    severity="warning", rule="MISSING_COMPOUND",
                    message="context.compound is null; cannot attribute this parameter to a chemical.",
                    suggested_fix="Infer from paper title/abstract or mark as unknown."
                ))

            # Rule 3: Missing unit when value exists
            unit = qdata.get("unit")
            value_raw = qdata.get("value")
            value = None
            if value_raw is not None:
                try:
                    value = float(value_raw)
                except (ValueError, TypeError):
                    pass
            value_text = qdata.get("value_text")
            if value_text and not unit:
                flags.append(ParameterFlag(
                    param_index=i, param_name=name,
                    severity="warning", rule="MISSING_UNIT",
                    message=f"value_text='{value_text}' present but unit is null.",
                    suggested_fix="Check if unit appears in a table column header."
                ))

            # Rule 4: value vs value_text mismatch (>5% relative error)
            if value is not None and value_text:
                try:
                    # Strip any trailing letter-footnotes like '5a' -> '5'
                    cleaned = re.sub(r"[^0-9.\-eE+]", "", str(value_text).split()[0])
                    if cleaned:
                        parsed = float(cleaned)
                        if abs(parsed - value) > abs(parsed) * 0.05 + 1e-9:
                            flags.append(ParameterFlag(
                                param_index=i, param_name=name,
                                severity="warning", rule="VALUE_MISMATCH",
                                message=f"value={value} does not match parsed value_text='{value_text}' ({parsed}).",
                                suggested_fix="Re-check the source cell."
                            ))
                except (ValueError, IndexError):
                    pass  # value_text has letters/qualifiers — expected

            # Rule 5: Biologically implausible numeric value
            if value is not None and unit:
                unit_lc = unit.lower().strip()
                name_lc = name.lower()
                sym_lc = symbol.lower()
                for name_frags, unit_frags, lo, hi in _PLAUSIBILITY_RULES:
                    name_hit = any(f in name_lc or f in sym_lc for f in name_frags)
                    unit_hit = any(f in unit_lc for f in unit_frags)
                    if name_hit and unit_hit:
                        if not (lo <= value <= hi):
                            flags.append(ParameterFlag(
                                param_index=i, param_name=name,
                                severity="warning", rule="IMPLAUSIBLE_VALUE",
                                message=(
                                    f"value={value} {unit} is outside the expected "
                                    f"plausible range [{lo}, {hi}] for '{name}'."
                                ),
                                suggested_fix=(
                                    "Verify unit conversion or check for a magnitude "
                                    "error (e.g. mL vs L)."
                                )
                            ))
                        break

            # Rule 6: Negative value for inherently positive parameters
            if value is not None and value < 0:
                name_lc = name.lower()
                sym_lc = symbol.lower()
                inherently_positive = [
                    "volume", "clearance", "half", "auc", "cmax", "rate constant"
                ]
                if any(k in name_lc or k in sym_lc for k in inherently_positive):
                    flags.append(ParameterFlag(
                        param_index=i, param_name=name,
                        severity="error", rule="NEGATIVE_VALUE",
                        message=f"value={value} is negative for a parameter that must be positive.",
                        suggested_fix="Check for sign errors or inverted table row."
                    ))

            # Rule 7: Inverted range (range_low > range_high)
            try:
                r_lo = float(qdata.get("range_low")) if qdata.get("range_low") is not None else None
                r_hi = float(qdata.get("range_high")) if qdata.get("range_high") is not None else None
            except (ValueError, TypeError):
                r_lo, r_hi = None, None

            if r_lo is not None and r_hi is not None and r_lo > r_hi:
                flags.append(ParameterFlag(
                    param_index=i, param_name=name,
                    severity="error", rule="INVERTED_RANGE",
                    message=f"range_low={r_lo} > range_high={r_hi}.",
                    suggested_fix="Swap low and high values."
                ))

            # Rule 8: Placeholder compound strings
            if compound:
                bad_placeholders = [
                    "compound", "chemical", "drug", "substance", "analyte", "xxx", "tbd"
                ]
                if any(bp in compound.lower() for bp in bad_placeholders):
                    flags.append(ParameterFlag(
                        param_index=i, param_name=name,
                        severity="warning", rule="PLACEHOLDER_COMPOUND",
                        message=f"context.compound='{compound}' looks like a placeholder.",
                        suggested_fix="Replace with the actual chemical name from the paper."
                    ))

            # Rule 9: High-confidence entry missing source_quote
            source_quote = prov.get("source_quote")
            if not source_quote and prov.get("confidence") == "high":
                flags.append(ParameterFlag(
                    param_index=i, param_name=name,
                    severity="warning", rule="MISSING_QUOTE_HIGH_CONF",
                    message=(
                        "confidence='high' but source_quote is null; "
                        "high confidence requires a direct quote."
                    ),
                    suggested_fix="Add verbatim text from the source cell or sentence."
                ))

            # Rule 10: Exact duplicate detection
            for j in range(i + 1, len(params)):
                p2 = params[j]
                name2 = p2.get("parameter_name", "")
                ctx2 = p2.get("context", {}) or {}
                compound2 = ctx2.get("compound", "")
                val2_raw = (p2.get("quantitative_data", {}) or {}).get("value")
                val2 = None
                if val2_raw is not None:
                    try:
                        val2 = float(val2_raw)
                    except (ValueError, TypeError):
                        pass

                if (
                    name.lower() == name2.lower()
                    and compound
                    and compound == compound2
                    and value is not None
                    and val2 is not None
                    and abs(value - val2) < 1e-9
                ):
                    flags.append(ParameterFlag(
                        param_index=i, param_name=name,
                        severity="warning", rule="DUPLICATE_ENTRY",
                        message=(
                            f"Exact duplicate of parameter at index {j} "
                            f"(same name, compound='{compound}', value={value})."
                        ),
                        suggested_fix=(
                            "Deduplicate; keep only the entry with higher provenance confidence."
                        )
                    ))

        # Build report
        errors   = [f for f in flags if f.severity == "error"]
        warnings = [f for f in flags if f.severity == "warning"]
        elapsed  = (time.monotonic() - t0) * 1000

        report = VerificationReport(
            tier=1,
            elapsed_ms=elapsed,
            total_parameters=len(params),
            flagged_count=len(flags),
            error_count=len(errors),
            warning_count=len(warnings),
            flags=flags,
            clean=len(flags) == 0,
        )
        report.summary = _build_summary(report)
        return report



# ---------------------------------------------------------------------------
# Tier 2: LLM Critic — real implementation
# ---------------------------------------------------------------------------
#
# Design goals:
#   • Uses its OWN small CriticVerdict JSON schema — NOT ExtractedPage.
#     This makes constrained decoding 10-20x faster (tiny schema vs large one).
#   • Calls the SGLang /generate endpoint directly via aiohttp.
#     No coupling to SGLangExtractor's ExtractedPage parsing.
#   • Only reviews parameters with severity="error" from Tier 1
#     (warnings are informational — LLM would add little signal).
#   • Patches corrected values back into document["parameters"] in-place
#     so the final JSON already contains the best data.
#   • Emits a concise "llm_verification" block in the document.
# ---------------------------------------------------------------------------

# Compact verdict schema — constrained decoding keeps this fast
_CRITIC_VERDICT_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {
            "type": "string",
            "enum": ["ok", "fix", "reject"],
            "description": (
                "'ok' = parameter is correct as-is, flag was a false positive. "
                "'fix' = parameter has real errors; corrected_fields contains fixes. "
                "'reject' = parameter is entirely wrong/fabricated and should be removed."
            )
        },
        "reasoning": {
            "type": "string",
            "description": "One-sentence justification for the verdict."
        },
        "corrected_fields": {
            "type": "object",
            "description": (
                "Flat dict of dot-notation field paths -> corrected values. "
                "Only populate when verdict='fix'. "
                "Example: {\"context.compound\": \"PFOA\", \"quantitative_data.unit\": \"L/h\"}"
            ),
            "additionalProperties": True
        }
    },
    "required": ["verdict", "reasoning"]
}

_CRITIC_SYSTEM_PROMPT = """\
You are a pharmacokinetics data quality auditor. You will be given:
  1. A single extracted parameter (JSON)
  2. Automated rule violations detected by Tier 1 verification

Your job: decide if the parameter is correct, needs fixing, or should be rejected.

Rules:
- Answer ONLY with valid JSON matching the CriticVerdict schema.
- verdict="ok"     → The parameter is acceptable; the rule flag was a false positive.
- verdict="fix"    → Real errors exist. Populate corrected_fields with ONLY the fields
                     that need changing, using dot-notation paths.
- verdict="reject" → The parameter is hallucinated, has no traceable source, or is
                     so corrupted it cannot be salvaged.
- corrected_fields keys use dot notation: "context.compound", "quantitative_data.value",
  "quantitative_data.unit", "provenance.source_quote", etc.
- Keep reasoning under 80 words.
- NEVER invent data. If you cannot determine the correct value, use verdict="ok"
  (leave the needs_review flag) rather than guessing.
"""


def _build_critic_prompt(param: dict, flags: list) -> str:
    """Build the full Qwen3 chat-format prompt for one parameter."""
    import json as _json
    flag_lines = "\n".join(
        f"  [{f.rule}] {f.severity.upper()}: {f.message}"
        for f in flags
    )
    user_content = (
        f"Parameter to review:\n```json\n{_json.dumps(param, indent=2)}\n```\n\n"
        f"Tier 1 violations detected:\n{flag_lines or '(none)'}\n\n"
        f"Return a CriticVerdict JSON object."
    )
    return (
        f"<|im_start|>system\n{_CRITIC_SYSTEM_PROMPT}<|im_end|>\n"
        f"<|im_start|>user\n{user_content}<|im_end|>\n"
        f"<|im_start|>assistant\n"
    )


def _apply_corrected_fields(param: dict, corrected_fields: dict) -> dict:
    """
    Patch dot-notation corrected fields back into the parameter dict.
    E.g. {"context.compound": "PFOA"} -> param["context"]["compound"] = "PFOA"
    """
    import copy
    result = copy.deepcopy(param)
    for dotkey, val in corrected_fields.items():
        parts = dotkey.split(".")
        obj = result
        for part in parts[:-1]:
            if part not in obj or not isinstance(obj[part], dict):
                obj[part] = {}
            obj = obj[part]
        obj[parts[-1]] = val
    return result


class Tier2LLMCritic:
    """
    LLM-based critic that reviews parameters flagged by Tier 1.

    Calls the running SGLang server directly (port 30000) using the
    compact CriticVerdict schema — much faster than ExtractedPage decoding.

    This is OPTIONAL. It runs ASYNC and does not block the main pipeline.
    Enable with: --llm-verify flag in main.py, or call verify_document_with_llm().
    """

    def __init__(
        self,
        server_url: str = "http://127.0.0.1:30000",
        max_new_tokens: int = 512,
        concurrency: int = 4,
    ):
        self.server_url = server_url
        self.max_new_tokens = max_new_tokens
        self.concurrency = concurrency

    async def _call_llm(self, prompt: str) -> dict:
        """
        POST to the running SGLang /generate endpoint with the compact
        CriticVerdict schema for constrained decoding. Returns parsed dict.
        """
        import aiohttp
        import json as _json

        payload = {
            "text": prompt,
            "sampling_params": {
                "max_new_tokens": self.max_new_tokens,
                "temperature": 0.0,           # deterministic
                "repetition_penalty": 1.0,
                "json_schema": _json.dumps(_CRITIC_VERDICT_SCHEMA),
            },
        }
        timeout = aiohttp.ClientTimeout(total=120)   # 2-min max per param
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                f"{self.server_url}/generate", json=payload
            ) as resp:
                result = await resp.json()
                raw = result.get("text", "")
                # Strip <think>...</think> if model emits CoT
                if "</think>" in raw:
                    raw = raw.split("</think>")[-1].strip()
                return _json.loads(raw)

    async def audit_flagged(
        self,
        document: dict,
        tier1_report: "VerificationReport",
        max_params: int = 15,
        include_warnings: bool = False,
    ) -> dict:
        """
        Reviews Tier-1-flagged parameters.

        Args:
            document:         The extracted document dict (will be patched in-place).
            tier1_report:     Output of Tier1Verifier.verify().
            max_params:       Hard cap on number of LLM calls (cost/latency guard).
            include_warnings: If True, also reviews warning-level flags (not just errors).

        Returns a summary dict written to document["llm_verification"].
        """
        import json as _json
        import asyncio
        import time as _time

        t0 = _time.monotonic()
        params = document.get("parameters", [])

        # Build a map: param_index -> [flags]
        target_severities = {"error"}
        if include_warnings:
            target_severities.add("warning")

        flags_by_idx: dict[int, list] = {}
        for f in tier1_report.flags:
            if f.severity in target_severities:
                flags_by_idx.setdefault(f.param_index, []).append(f)

        # Sort by error count desc (worst first), cap at max_params
        ranked = sorted(flags_by_idx.items(), key=lambda kv: len(kv[1]), reverse=True)
        ranked = ranked[:max_params]

        if not ranked:
            result = {
                "reviewed": 0,
                "patched": 0,
                "rejected": 0,
                "elapsed_s": 0.0,
                "verdicts": [],
                "skipped_reason": "No error-level flags from Tier 1.",
            }
            document["llm_verification"] = result
            return result

        print(f"\n{'='*65}")
        print(f" TIER 2 LLM CRITIC  (reviewing {len(ranked)} flagged parameters)")
        print(f"{'='*65}")

        sem = asyncio.Semaphore(self.concurrency)
        verdicts = []

        async def _review_one(param_idx: int, flags: list) -> dict:
            async with sem:
                if param_idx >= len(params):
                    return {"param_index": param_idx, "status": "skipped", "reason": "index out of range"}
                param = params[param_idx]
                prompt = _build_critic_prompt(param, flags)
                try:
                    verdict_dict = await self._call_llm(prompt)
                    verdict     = verdict_dict.get("verdict", "ok")
                    reasoning   = verdict_dict.get("reasoning", "")
                    corrections = verdict_dict.get("corrected_fields", {})

                    icon = {"ok": "OK ", "fix": "FIX", "reject": "DEL"}.get(verdict, "???")
                    name_short = (param.get("parameter_name") or "?")[:50]
                    print(f"  [{icon}] #{param_idx} '{name_short}' — {reasoning[:70]}")

                    return {
                        "param_index": param_idx,
                        "verdict": verdict,
                        "reasoning": reasoning,
                        "corrected_fields": corrections,
                        "status": "reviewed",
                    }
                except Exception as e:
                    logger.warning(f"Tier2 LLM critic failed for param #{param_idx}: {e}")
                    return {"param_index": param_idx, "status": "failed", "error": str(e)}

        tasks = [_review_one(idx, flgs) for idx, flgs in ranked]
        verdicts = await asyncio.gather(*tasks, return_exceptions=True)
        verdicts = [v for v in verdicts if not isinstance(v, Exception)]

        # --- Apply corrections and rejections back into document ---
        patched_count  = 0
        rejected_count = 0
        rejected_indices = set()

        for v in verdicts:
            idx = v.get("param_index")
            if idx is None or idx >= len(params):
                continue

            if v.get("verdict") == "fix" and v.get("corrected_fields"):
                params[idx] = _apply_corrected_fields(params[idx], v["corrected_fields"])
                params[idx]["needs_review"] = True   # still flag for human check
                params[idx]["llm_corrected"] = True
                patched_count += 1

            elif v.get("verdict") == "reject":
                rejected_indices.add(idx)
                rejected_count += 1

        # Remove rejected parameters (reverse order to preserve indices)
        for idx in sorted(rejected_indices, reverse=True):
            if idx < len(params):
                rejected_param_name = params[idx].get("parameter_name", "?")
                logger.info(f"Tier2: Rejected parameter #{idx} '{rejected_param_name}'")
                del params[idx]

        elapsed = _time.monotonic() - t0
        print(f"  * Reviewed:  {len(verdicts)} parameters")
        print(f"  * Patched:   {patched_count}")
        print(f"  * Rejected:  {rejected_count}")
        print(f"  * Elapsed:   {elapsed:.1f}s")
        print(f"{'='*65}\n")

        summary = {
            "reviewed": len(verdicts),
            "patched": patched_count,
            "rejected": rejected_count,
            "elapsed_s": round(elapsed, 2),
            "verdicts": [
                {k: v for k, v in vd.items() if k != "corrected_fields"}
                for vd in verdicts
                if vd.get("status") == "reviewed"
            ],
        }
        document["llm_verification"] = summary
        return summary


# ---------------------------------------------------------------------------
# Primary entry points for the pipeline
# ---------------------------------------------------------------------------

def verify_document(document: dict, verbose: bool = True) -> "VerificationReport":
    """
    Run Tier 1 verification on an extracted document dict.
    Attaches the report to document['verification'] and returns it.

    Latency: <5ms (pure Python, no GPU, no network).
    """
    verifier = Tier1Verifier()
    report = verifier.verify(document)
    document["verification"] = report.to_dict()

    if verbose:
        _print_verification_summary(report)

    return report


async def verify_document_with_llm(
    document: dict,
    verbose: bool = True,
    server_url: str = "http://127.0.0.1:30000",
    max_params: int = 15,
    include_warnings: bool = False,
) -> tuple:
    """
    Run Tier 1 (instant) + Tier 2 LLM critic (async, on flagged only).

    Returns: (tier1_report, llm_summary_dict)

    The document is patched in-place:
      - document["verification"]     ← Tier 1 report
      - document["llm_verification"] ← Tier 2 verdicts + corrections applied
    """
    # Tier 1 always runs first
    tier1 = verify_document(document, verbose=verbose)

    if tier1.clean:
        logger.info("Tier 1 passed cleanly — skipping Tier 2 LLM critic.")
        llm_summary = {
            "reviewed": 0,
            "patched": 0,
            "rejected": 0,
            "elapsed_s": 0.0,
            "verdicts": [],
            "skipped_reason": "Tier 1 was clean — no LLM review needed.",
        }
        document["llm_verification"] = llm_summary
        return tier1, llm_summary

    critic = Tier2LLMCritic(server_url=server_url)
    llm_summary = await critic.audit_flagged(
        document,
        tier1,
        max_params=max_params,
        include_warnings=include_warnings,
    )

    # Refresh Tier 1 on patched document so the stored report is accurate
    if llm_summary.get("patched", 0) > 0 or llm_summary.get("rejected", 0) > 0:
        logger.info("Re-running Tier 1 on LLM-patched document...")
        tier1_refreshed = Tier1Verifier().verify(document)
        document["verification"] = tier1_refreshed.to_dict()
        document["verification"]["note"] = "Re-run after Tier 2 LLM patching."

    return tier1, llm_summary


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_summary(report: "VerificationReport") -> str:
    if report.clean:
        return (
            f"All {report.total_parameters} parameters passed Tier 1 verification."
        )
    parts = []
    if report.error_count:
        parts.append(f"{report.error_count} error(s)")
    if report.warning_count:
        parts.append(f"{report.warning_count} warning(s)")
    return (
        f"{report.flagged_count}/{report.total_parameters} parameters flagged: "
        + ", ".join(parts)
        + f". Elapsed: {report.elapsed_ms:.1f}ms."
    )


def _print_verification_summary(report: "VerificationReport") -> None:
    print(f"\n{'='*65}")
    print(f" TIER 1 VERIFICATION REPORT")
    print(f"{'='*65}")
    print(f"  * Parameters checked:  {report.total_parameters}")
    print(f"  * Elapsed time:        {report.elapsed_ms:.1f}ms (zero GPU cost)")
    print(f"  * Errors:              {report.error_count}")
    print(f"  * Warnings:            {report.warning_count}")
    if report.clean:
        print(f"  * Status:              CLEAN -- no issues detected")
    else:
        print(f"  * Status:              ISSUES FOUND")
        for f in report.flags[:10]:
            icon = "[ERROR]" if f.severity == "error" else "[WARN] "
            print(f"    {icon} [{f.rule}] #{f.param_index} '{f.param_name[:45]}': {f.message}")
        if len(report.flags) > 10:
            print(
                f"    ... and {len(report.flags) - 10} more. "
                f"See 'verification' key in JSON output."
            )
    print(f"{'='*65}\n")
