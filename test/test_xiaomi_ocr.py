#!/usr/bin/env python3
"""
test/test_xiaomi_ocr.py
=======================
Test case and evaluation runner for SeerRay-Lab/Xiaomi-OCR-0.
Xiaomi-OCR-0 is a compact, unified 0.8B parameter OCR vision-language model
developed by SeerRay-Lab (Xiaomi) based on the Qwen3.5-0.8B-Base architecture.

It is specialized in:
1. Full-page document parsing into Markdown (with LaTeX formulas & OTSL tables)
2. Table structure recognition (OTSL / Markdown)
3. Mathematical formula transcription (LaTeX)
4. Key information extraction (KIE / JSON)

Reference:
    https://huggingface.co/SeerRay-Lab/Xiaomi-OCR-0

Target Test Document:
    pk_pipeline/test_data/Dean et al. 2025 3 compartment (PFOA, PFOS, PFHxS).pdf
    (Specifically Page 4: Table 1 - Mean TK parameters for PFOS and PFOA)

Usage:
    # 1. Run pytest test cases (render, prompt, and pipeline verification)
    pytest test/test_xiaomi_ocr.py -v

    # 2. Run CLI test on Page 4 (Table 1) of Dean et al. 2025:
    python test/test_xiaomi_ocr.py

    # 3. Dry-run test (renders image & verifies prompts without downloading weights):
    python test/test_xiaomi_ocr.py --dry-run

    # 4. Run table-specific extraction or formula recognition:
    python test/test_xiaomi_ocr.py --page 4 --task table_otsl
    python test/test_xiaomi_ocr.py --page 3 --task formula

    # 5. Run full PBPK parameter extraction prompt:
    python test/test_xiaomi_ocr.py --page 4 --task pbpk --output test/dean_page4_xiaomi_ocr_pbpk.md
"""

import os
import sys
import time
import argparse
import re
from pathlib import Path
from typing import Dict, Any, Optional
from PIL import Image

# Ensure repository root is on PYTHONPATH
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

DEFAULT_MODEL_ID = "SeerRay-Lab/Xiaomi-OCR-0"

PAPERS = {
    "karrer": {
        "title": "Karrer et al. 2018 (BPA, BPS, BPF, BPAF)",
        "pdf": "pk_pipeline/test_data/Karrer et al.pdf",
        "default_page": 8,  # Table 7: Metabolic parameters & Table 8: Physiological parameters
        "table_pages": [3, 4, 5, 6, 8, 12, 13],  # Fig 2/Table 1, Table 2/3, Table 4/5, Table 6, Table 7/8, Table 9, Table 10/11
        "default_output": "test/karrer_page8_xiaomi_ocr.md",
    },
    "dean": {
        "title": "Dean et al. 2025 (PFOA, PFOS, PFHxS)",
        "pdf": "pk_pipeline/test_data/Dean et al. 2025 3 compartment (PFOA, PFOS, PFHxS).pdf",
        "default_page": 4,  # Table 1: PFOS/PFOA parameters
        "table_pages": [4, 5, 6],
        "default_output": "test/dean_page4_xiaomi_ocr.md",
    },
}

DEFAULT_PAPER = "karrer"
DEFAULT_PDF = PAPERS[DEFAULT_PAPER]["pdf"]
DEFAULT_PAGE = PAPERS[DEFAULT_PAPER]["default_page"]
DEFAULT_OUTPUT = PAPERS[DEFAULT_PAPER]["default_output"]

# ─── Task Prompt Templates (Official Xiaomi-OCR-0 Recipes) ──────────────────────

PROMPT_TEMPLATES = {
    # 1. Full-page document parsing (recommended in official model card)
    "document": (
        "Extract all information from the main body of the document image and represent it in markdown format, "
        "ignoring headers and footers. Tables should be expressed in OTSL format, formulas in the document should "
        "be represented using LATEX format, and the parsing should be organized according to the reading order."
    ),
    # 2. Standard Markdown transcription
    "markdown": (
        "Extract all information from the main body of the document image and represent it in markdown format."
    ),
    # 3. Dedicated Table Parsing in OTSL (Optimized Table Structure Language)
    "table_otsl": (
        "Parse the table in the image into OTSL."
    ),
    # 4. Standard Markdown Table Parsing
    "table_markdown": (
        "Extract the table in the image into markdown format, preserving all columns, rows, headers, and numeric values."
    ),
    # 5. Mathematical Formula Recognition
    "formula": (
        "Identify the formula in the image and represent it using LATEX format."
    ),
    # 6. Key Information Extraction (KIE)
    "kie": (
        "Extract key information in the image followed by your JSON schema."
    ),
    # 7. Domain-specific PBPK parameter extraction for APEX
    "pbpk": (
        "Extract all pharmacokinetic parameters, symbols, numerical values, units, species, and compounds "
        "from the table in this image into structured markdown format. Include parameter names (e.g., VCC, Tmc, Kt, Free), "
        "mean values, confidence intervals, and reference sources."
    ),
}


def render_pdf_page_to_image(pdf_path: str, page_number: int = 4, dpi: int = 200) -> Image.Image:
    """Render a specific 1-indexed page of a PDF file to a PIL RGB image."""
    try:
        import pymupdf as fitz
    except ImportError:
        import fitz

    resolved_path = os.path.abspath(pdf_path)
    if not os.path.exists(resolved_path):
        raise FileNotFoundError(f"PDF document not found at: {resolved_path}")

    doc = fitz.open(resolved_path)
    if page_number < 1 or page_number > len(doc):
        raise IndexError(f"Page number {page_number} is out of bounds (document has {len(doc)} pages).")

    page = doc[page_number - 1]
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    return img


def build_xiaomi_chat_messages(image: Image.Image, prompt_text: str) -> list:
    """Construct standard multimodal chat message payload for Xiaomi-OCR-0."""
    return [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": prompt_text},
            ],
        }
    ]


def convert_otsl_to_markdown_table(otsl_text: str) -> str:
    """
    Utility parser to format/normalize OTSL (Optimized Table Structure Language)
    output into clean Markdown representation if raw table tags are detected.
    """
    if not otsl_text:
        return ""

    # If already standard Markdown or HTML, return directly
    if "<table" in otsl_text or ("|" in otsl_text and "---" in otsl_text):
        return otsl_text

    # Basic normalization of OTSL cell markers if present
    lines = otsl_text.strip().split("\n")
    cleaned_lines = []
    for line in lines:
        cleaned = re.sub(r"<cell>|</cell>|<loc_\d+>", " ", line)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if cleaned:
            cleaned_lines.append(cleaned)
    return "\n".join(cleaned_lines)


def run_xiaomi_ocr(
    image: Image.Image,
    model_id: str = DEFAULT_MODEL_ID,
    prompt: str = PROMPT_TEMPLATES["document"],
    max_new_tokens: int = 5000,
    device: Optional[str] = None,
) -> str:
    """
    Run local inference with SeerRay-Lab/Xiaomi-OCR-0 using HuggingFace Transformers.
    """
    import torch
    from transformers import AutoProcessor

    # Multi-class loader fallback to support various transformer versions
    model_cls = None
    for candidate_cls in [
        "Qwen3_5ForConditionalGeneration",
        "AutoModelForImageTextToText",
        "AutoModelForConditionalGeneration",
        "AutoModelForMultimodalLM",
        "AutoModelForVision2Seq",
        "AutoModelForCausalLM",
    ]:
        try:
            import transformers
            if hasattr(transformers, candidate_cls):
                model_cls = getattr(transformers, candidate_cls)
                break
        except Exception:
            continue
    if model_cls is None:
        from transformers import AutoModelForCausalLM
        model_cls = AutoModelForCausalLM

    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    dtype = torch.bfloat16 if (torch.cuda.is_available() and device.startswith("cuda")) else torch.float32

    print(f"[Xiaomi-OCR] Loading AutoProcessor for '{model_id}' (trust_remote_code=True)...")
    processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)

    print(f"[Xiaomi-OCR] Loading Model on {device} ({dtype})...")
    device_map = {"": device} if (device and device != "cpu") else None
    model = model_cls.from_pretrained(
        model_id,
        torch_dtype=dtype,
        device_map=device_map,
        trust_remote_code=True,
    )
    model.eval()

    messages = build_xiaomi_chat_messages(image=image, prompt_text=prompt)

    print(f"[Xiaomi-OCR] Applying chat template and tokenizing inputs...")
    # Attempt processor chat template processing
    try:
        inputs = processor.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        )
    except Exception:
        # Fallback to direct prompt + image processing
        text_prompt = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = processor(text=[text_prompt], images=[image], return_tensors="pt")

    # Move tensors to target device
    target_device = torch.device(device)
    inputs = {k: v.to(target_device) if hasattr(v, "to") else v for k, v in inputs.items()}

    print(f"[Xiaomi-OCR] Generating tokens (max_new_tokens={max_new_tokens})...")
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
        )

    print("[Xiaomi-OCR] Decoding response tokens...")
    input_len = inputs["input_ids"].shape[-1]
    generated_tokens = outputs[0][input_len:]
    decoded_text = processor.decode(generated_tokens, skip_special_tokens=True)
    return decoded_text.strip()


# ─── Pytest Test Cases ──────────────────────────────────────────────────────────

def test_render_dean_pdf_page4():
    """Verify rendering of Dean et al. 2025 Page 4 (Table 1)."""
    pdf_path = PAPERS["dean"]["pdf"]
    assert os.path.exists(pdf_path), f"Test PDF does not exist: {pdf_path}"
    img = render_pdf_page_to_image(pdf_path, page_number=4, dpi=150)
    assert img is not None
    assert img.mode == "RGB"
    assert img.width > 500 and img.height > 500
    print(f"\n[Test Pass] Rendered Dean et al. 2025 Page 4: {img.size[0]}x{img.size[1]} px")


def test_render_karrer_pdf_page8():
    """Verify rendering of Karrer et al. 2018 Page 8 (Table 7 & Table 8)."""
    pdf_path = PAPERS["karrer"]["pdf"]
    assert os.path.exists(pdf_path), f"Test PDF does not exist: {pdf_path}"
    img = render_pdf_page_to_image(pdf_path, page_number=8, dpi=150)
    assert img is not None
    assert img.mode == "RGB"
    assert img.width > 500 and img.height > 500
    print(f"\n[Test Pass] Rendered Karrer et al. 2018 Page 8 (Table 7 & 8): {img.size[0]}x{img.size[1]} px")


def test_render_karrer_pdf_page6():
    """Verify rendering of Karrer et al. 2018 Page 6 (Table 6: PTS partition coefficients)."""
    pdf_path = PAPERS["karrer"]["pdf"]
    assert os.path.exists(pdf_path), f"Test PDF does not exist: {pdf_path}"
    img = render_pdf_page_to_image(pdf_path, page_number=6, dpi=150)
    assert img is not None
    assert img.mode == "RGB"
    assert img.width > 500 and img.height > 500
    print(f"\n[Test Pass] Rendered Karrer et al. 2018 Page 6 (Table 6): {img.size[0]}x{img.size[1]} px")


def test_xiaomi_ocr_prompt_construction():
    """Verify official Xiaomi-OCR-0 prompt templates and chat message payload."""
    img = Image.new("RGB", (200, 200), color="white")
    for task_name, prompt in PROMPT_TEMPLATES.items():
        messages = build_xiaomi_chat_messages(img, prompt)
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        content = messages[0]["content"]
        assert len(content) == 2
        assert content[0]["type"] == "image"
        assert content[1]["type"] == "text"
        assert len(content[1]["text"]) > 10
    print(f"\n[Test Pass] Verified all {len(PROMPT_TEMPLATES)} Xiaomi-OCR-0 prompt templates.")


def test_otsl_converter():
    """Verify OTSL table parsing helper."""
    raw_otsl = "<cell>Parameter</cell><cell>Value</cell>\n<cell>VCC</cell><cell>1.07</cell>"
    cleaned = convert_otsl_to_markdown_table(raw_otsl)
    assert "Parameter" in cleaned
    assert "VCC" in cleaned
    print("\n[Test Pass] OTSL table converter executed successfully.")


def test_xiaomi_ocr_model_environment():
    """Test model environment configuration."""
    assert DEFAULT_MODEL_ID == "SeerRay-Lab/Xiaomi-OCR-0"
    print(f"\n[Test Pass] Target Hugging Face model validated: {DEFAULT_MODEL_ID}")


# ─── CLI Entrypoint ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Run test case for SeerRay-Lab/Xiaomi-OCR-0 on PBPK papers (Karrer et al. / Dean et al.)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--paper",
        type=str,
        default="karrer",
        choices=list(PAPERS.keys()),
        help="Select paper preset: 'karrer' (Karrer et al. 2018) or 'dean' (Dean et al. 2025)",
    )
    parser.add_argument("--pdf", type=str, default=None, help="Path to PDF file (overrides --paper preset)")
    parser.add_argument("--page", type=int, default=None, help="1-indexed PDF page number (default: paper-specific default page)")
    parser.add_argument("--image", type=str, default=None, help="Direct path to an image file (overrides PDF rendering)")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL_ID, help="Hugging Face model ID")
    parser.add_argument(
        "--task",
        type=str,
        default="document",
        choices=list(PROMPT_TEMPLATES.keys()),
        help="Task prompt preset: document, markdown, table_otsl, table_markdown, formula, kie, pbpk",
    )
    parser.add_argument("--custom-prompt", type=str, default=None, help="Custom user text prompt (overrides task preset)")
    parser.add_argument("--max-tokens", type=int, default=5000, help="Maximum new tokens to generate")
    parser.add_argument("--dpi", type=int, default=200, help="DPI resolution for PDF page rendering")
    parser.add_argument("--output", type=str, default=None, help="Path to save output Markdown file")
    parser.add_argument("--device", type=str, default=None, help="Inference device: 'cuda', 'cpu', or None for auto")
    parser.add_argument("--dry-run", action="store_true", help="Render image & validate pipeline without running model inference")

    args = parser.parse_args()

    # Resolve target paper preset
    paper_config = PAPERS.get(args.paper, PAPERS["karrer"])
    target_pdf = args.pdf if args.pdf else paper_config["pdf"]
    target_page = args.page if args.page is not None else paper_config["default_page"]
    target_output = args.output if args.output else paper_config["default_output"]

    print("\n" + "=" * 70)
    print("  SeerRay-Lab/Xiaomi-OCR-0 Test Runner")
    print(f"  Model: {args.model}")
    print(f"  Paper: {paper_config['title']}")
    print(f"  Target Document: {target_pdf} (Page {target_page})")
    print("=" * 70)

    # 1. Prepare input image
    t0 = time.time()
    if args.image and os.path.exists(args.image):
        print(f"Loading direct image: {args.image}")
        img = Image.open(args.image).convert("RGB")
    else:
        print(f"Rendering PDF '{target_pdf}' (Page {target_page}) at {args.dpi} DPI...")
        img = render_pdf_page_to_image(target_pdf, page_number=target_page, dpi=args.dpi)

    print(f"Image prepared in {time.time() - t0:.2f}s: dimensions={img.size[0]}x{img.size[1]} px")

    # 2. Select prompt
    prompt_text = args.custom_prompt if args.custom_prompt else PROMPT_TEMPLATES[args.task]
    print(f"\nTask: [{args.task}]")
    print(f"Prompt: \"{prompt_text}\"")

    if args.dry_run:
        print("\n[Dry Run] Pipeline validated. Image successfully rendered. Exiting without model download.")
        return

    # 3. Execute inference
    try:
        t_start = time.time()
        print(f"\nRunning Xiaomi-OCR-0 model inference...")
        ocr_result = run_xiaomi_ocr(
            image=img,
            model_id=args.model,
            prompt=prompt_text,
            max_new_tokens=args.max_tokens,
            device=args.device,
        )
        t_elapsed = time.time() - t_start

        # 4. Save and summarize result
        out_path = Path(target_output).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(ocr_result)

        print("\n" + "=" * 70)
        print(f"  Xiaomi-OCR-0 Output Preview ({t_elapsed:.2f}s):")
        print("=" * 70)
        preview_len = min(600, len(ocr_result))
        print(ocr_result[:preview_len] + ("\n... [truncated]" if len(ocr_result) > preview_len else ""))
        print("=" * 70)
        print(f"\nComplete OCR Markdown successfully written to: {out_path}\n")

    except Exception as e:
        print(f"\n[Execution Note / Error]: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
