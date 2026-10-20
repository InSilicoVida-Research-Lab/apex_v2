"""
apex_v2_pipeline.py
Wraps our Apex v2 pipeline (JATS XML / MinerU + Multimodal VLM + PBPK Assembler & Verifier).
Outputs the canonical ExtractedDocument JSON. Fully paper-agnostic.
"""

import os
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional

from pk_pipeline.schemas import ExtractedDocument


class ApexV2Pipeline:
    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run(self, pdf_path: str, force_rerun: bool = False) -> Dict[str, Any]:
        """Runs or loads Apex v2 extraction for the given paper."""
        pdf_file = Path(pdf_path)
        stem = pdf_file.stem
        target_json = self.output_dir / f"{stem}.json"

        # Check for existing processed output if not forcing rerun
        if target_json.exists() and not force_rerun:
            try:
                data = json.loads(target_json.read_text(encoding="utf-8"))
                return ExtractedDocument.model_validate(data).model_dump(mode="json")
            except Exception as e:
                print(f"[Apex v2] Warning: Failed reading cached {target_json}: {e}. Will rerun.")

        # Check for potential XML sidecar file (JATS/PMC XML)
        xml_path: Optional[str] = None
        candidates = list(pdf_file.parent.glob(f"{stem}*.xml"))
        if not candidates:
            # Check pbpk_data directory
            pbpk_data_dir = pdf_file.parent
            for xml_file in pbpk_data_dir.glob("*.xml"):
                if any(part in xml_file.stem.lower() for part in stem.lower().split()[:2]):
                    candidates.append(xml_file)
        if candidates:
            xml_path = str(candidates[0])
            print(f"[Apex v2] Found companion JATS XML: {candidates[0].name}")

        from pk_pipeline.main import run_pipeline
        print(f"[Apex v2] Executing live pipeline for {pdf_file.name}...")
        asyncio.run(run_pipeline(
            pdf_path=str(pdf_file),
            xml_path=xml_path,
            output_dir=str(self.output_dir)
        ))

        if target_json.exists():
            data = json.loads(target_json.read_text(encoding="utf-8"))
            return ExtractedDocument.model_validate(data).model_dump(mode="json")

        raise RuntimeError(f"Apex v2 pipeline execution finished but {target_json} was not found.")


if __name__ == "__main__":
    import sys
    test_pdf = sys.argv[1] if len(sys.argv) > 1 else "pk_pipeline/pbpk_data/Dean et al. 2025 3 compartment (PFOA, PFOS, PFHxS).pdf"
    pipeline = ApexV2Pipeline()
    res = pipeline.run(test_pdf)
    print(f"[Apex v2 Pipeline] Extracted {len(res.get('model_parameters', []))} parameters.")
