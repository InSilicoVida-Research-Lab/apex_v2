#!/usr/bin/env python3
"""
test/test_wevisdoc.py
=====================
Test script and runner for Tencent/WeVisDoc-4B (and WeVisDoc-2B).
WeVisDoc is an end-to-end document parser fine-tuned from Qwen3-VL that converts
page images into structured Markdown with LaTeX math formulas and HTML tables.

Reference: https://huggingface.co/tencent/WeVisDoc-4B

Usage:
    # Run test on default sample PDF page
    python test/test_wevisdoc.py

    # Run on a specific PDF and page
    python test/test_wevisdoc.py --pdf "pk_pipeline/test_data/s12249-023-02680-y.pdf" --page 6

    # Run on a direct image file
    python test/test_wevisdoc.py --image "my_page.png" --model "Tencent/WeVisDoc-4B"
"""

import os
import sys
import argparse
from pathlib import Path
from PIL import Image

# Ensure repository root is on PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Default system prompt for WeVisDoc (preserves Markdown structure, LaTeX math, HTML tables)
DEFAULT_SYSTEM_PROMPT = (
    "You are an AI assistant specialized in converting PDF images to Markdown format. "
    "Please follow these instructions for the conversion:\n\n"
    "1. Text Processing:\n"
    "- Accurately recognize all text content in the PDF image without guessing or inferring.\n"
    "- Convert the recognized text into Markdown format.\n"
    "- Maintain the original document structure, including headings, paragraphs, lists, etc.\n\n"
    "2. Mathematical Formula Processing:\n"
    "- Convert all mathematical formulas to LaTeX format.\n"
    "- Enclose inline formulas with \\( \\). For example: \\( E = mc^2 \\)\n"
    "- Enclose block formulas with \\[ \\]. For example: \\[ \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a} \\]\n\n"
    "3. Table Processing:\n"
    "- Convert all tables to standard HTML format using <table>, <thead>, <tbody>, <tr>, <th>, <td>.\n"
    "- Use rowspan and colspan appropriately for merged headers or cells.\n"
    "- Preserve exact numerical and textual values in table cells."
)

DEFAULT_USER_PROMPT = "Please transcribe this page image into clean Markdown following the system instructions."


def render_pdf_page_to_image(pdf_path: str, page_number: int = 1, dpi: int = 200) -> Image.Image:
    """Render a specific 1-indexed page of a PDF file to a PIL RGB image."""
    try:
        import pymupdf as fitz
    except ImportError:
        import fitz

    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found at: {pdf_path}")

    doc = fitz.open(pdf_path)
    if page_number < 1 or page_number > len(doc):
        raise IndexError(f"Page number {page_number} is out of bounds (document has {len(doc)} pages).")

    page = doc[page_number - 1]
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    return img


def run_wevisdoc_ocr(
    image: Image.Image,
    model_id: str = "Tencent/WeVisDoc-4B",
    max_new_tokens: int = 4096,
    system_prompt: str = DEFAULT_SYSTEM_PROMPT,
    user_prompt: str = DEFAULT_USER_PROMPT,
    device: str = None
) -> str:
    """
    Run WeVisDoc OCR inference on a PIL Image using HuggingFace Transformers.
    """
    import torch
    from transformers import AutoProcessor

    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32

    print(f"[WeVisDoc] Loading processor for {model_id}...")
    processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)

    print(f"[WeVisDoc] Loading model {model_id} on {device} (dtype={dtype})...")
    # Try loading with Qwen3VLForConditionalGeneration or AutoModelForVision2Seq
    device_map = {"": device} if (device and device != "cpu") else None
    try:
        from transformers import Qwen3VLForConditionalGeneration
        model = Qwen3VLForConditionalGeneration.from_pretrained(
            model_id,
            torch_dtype=dtype,
            device_map=device_map,
            trust_remote_code=True
        )
    except Exception as e:
        print(f"[WeVisDoc] Qwen3VL direct load note ({e}), falling back to AutoModelForVision2Seq...")
        from transformers import AutoModelForVision2Seq
        model = AutoModelForVision2Seq.from_pretrained(
            model_id,
            torch_dtype=dtype,
            device_map=device_map,
            trust_remote_code=True
        )

    model.eval()

    # Construct chat messages
    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": user_prompt}
            ]
        }
    ]

    print("[WeVisDoc] Preparing inputs and chat template...")
    prompt_text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = processor(
        text=[prompt_text],
        images=[image],
        padding=True,
        return_tensors="pt"
    )
    inputs = inputs.to(model.device)

    print(f"[WeVisDoc] Generating OCR Markdown (max_new_tokens={max_new_tokens})...")
    with torch.no_grad():
        generated_ids = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False
        )

    # Trim input prompt tokens from output
    generated_ids_trimmed = [
        out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
    ]
    output_text = processor.batch_decode(
        generated_ids_trimmed,
        skip_special_tokens=True,
        clean_up_tokenization_spaces=False
    )[0]

    return output_text.strip()


def test_wevisdoc():
    """Pytest test case for WeVisDoc."""
    sample_pdf = "pk_pipeline/test_data/s12249-023-02680-y.pdf"
    if not os.path.exists(sample_pdf):
        print(f"[Skip] Sample PDF not found: {sample_pdf}")
        return

    print("\n--- Running WeVisDoc Test Case ---")
    img = render_pdf_page_to_image(sample_pdf, page_number=6, dpi=150)
    assert img is not None
    assert img.width > 0 and img.height > 0
    print(f"Rendered test image: size={img.size}")


def main():
    parser = argparse.ArgumentParser(description="Test Tencent/WeVisDoc-4B Document OCR")
    parser.add_argument("--pdf", type=str, default="pk_pipeline/test_data/s12249-023-02680-y.pdf", help="Path to PDF")
    parser.add_argument("--page", type=int, default=6, help="1-indexed PDF page to render")
    parser.add_argument("--image", type=str, default=None, help="Path to existing image file (overrides --pdf)")
    parser.add_argument("--model", type=str, default="Tencent/WeVisDoc-4B", help="Model ID (e.g. Tencent/WeVisDoc-4B or Tencent/WeVisDoc-2B)")
    parser.add_argument("--max-tokens", type=int, default=4096, help="Maximum new tokens")
    parser.add_argument("--output", type=str, default="test/wevisdoc_output.md", help="Output Markdown file path")
    parser.add_argument("--dry-run", action="store_true", help="Only render image without running model")
    args = parser.parse_args()

    # 1. Obtain input image
    if args.image and os.path.exists(args.image):
        print(f"Loading image from: {args.image}")
        img = Image.open(args.image).convert("RGB")
    else:
        print(f"Rendering PDF '{args.pdf}' (Page {args.page})...")
        img = render_pdf_page_to_image(args.pdf, page_number=args.page, dpi=200)

    print(f"Input image ready: {img.size[0]}x{img.size[1]} px")

    if args.dry_run:
        print("Dry run complete. Image rendered successfully.")
        return

    # 2. Run WeVisDoc
    try:
        md_result = run_wevisdoc_ocr(
            image=img,
            model_id=args.model,
            max_new_tokens=args.max_tokens
        )

        # 3. Save and display result
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(md_result)

        print(f"\n{'='*60}")
        print(f"  WeVisDoc OCR Output Preview (first 500 chars):")
        print(f"{'='*60}")
        print(md_result[:500] + ("..." if len(md_result) > 500 else ""))
        print(f"{'='*60}")
        print(f"Full result successfully saved to: {args.output}\n")

    except Exception as e:
        print(f"\n[Error] WeVisDoc OCR execution failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
