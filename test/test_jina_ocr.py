#!/usr/bin/env python3
"""
test/test_jina_ocr.py
=====================
Test script and runner for jinaai/jina-ocr-v1.
Jina-OCR-v1 is an efficient end-to-end document parsing model built on DeepSeek-OCR
(DeepEncoder + 3B MoE with ~570M active parameters per token).

Reference: https://huggingface.co/jinaai/jina-ocr-v1

Usage:
    # Run test on default sample PDF page
    python test/test_jina_ocr.py

    # Run on a specific PDF and page
    python test/test_jina_ocr.py --pdf "pk_pipeline/test_data/s12249-023-02680-y.pdf" --page 6

    # Run on a direct image file
    python test/test_jina_ocr.py --image "my_page.png"
"""

import os
import sys
import argparse
from pathlib import Path
from PIL import Image

# Ensure repository root is on PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Default Jina OCR prompt recommended in the official model card
DEFAULT_PROMPT = (
    "Transcribe the provided document image into a clean Markdown format, preserving the natural reading order. "
    "Convert tables into standard HTML format. Turn equations and math symbols into LaTeX representation."
)


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


def run_jina_ocr_local(
    image: Image.Image,
    model_id: str = "jinaai/jina-ocr-v1",
    max_new_tokens: int = 4096,
    prompt: str = DEFAULT_PROMPT,
    device: str = None
) -> str:
    """
    Run Jina-OCR-v1 inference locally using HuggingFace Transformers.
    """
    import torch
    from transformers import AutoModelForCausalLM, AutoProcessor

    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32

    print(f"[Jina-OCR] Loading processor for {model_id} (trust_remote_code=True)...")
    processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)

    device_map = {"": device} if (device and device != "cpu") else None
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype=dtype,
        device_map=device_map,
        trust_remote_code=True
    )
    model.eval()

    print("[Jina-OCR] Preparing OCR inputs...")
    target_device = torch.device(device)
    inputs = processor.prepare_ocr_inputs(image, prompt=prompt, device=target_device)

    print(f"[Jina-OCR] Generating OCR Markdown (max_new_tokens={max_new_tokens})...")
    with torch.no_grad():
        output = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False
        )

    print("[Jina-OCR] Decoding OCR output...")
    decoded_text = processor.decode_ocr(output, inputs["input_ids"])
    return decoded_text.strip()


def run_jina_ocr_api(image: Image.Image, api_key: str = None, prompt: str = DEFAULT_PROMPT) -> str:
    """
    Optional fast-path: Call Jina Reader / Document OCR API if JINA_API_KEY is available.
    """
    import io
    import base64
    import requests

    key = api_key or os.getenv("JINA_API_KEY")
    if not key:
        raise ValueError("JINA_API_KEY is required to use the API mode.")

    print("[Jina-OCR API] Encoding image to base64...")
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG", quality=90)
    img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
    data_url = f"data:image/jpeg;base64,{img_b64}"

    url = "https://api.jina.ai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}"
    }
    payload = {
        "model": "jina-ocr-v1",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}}
                ]
            }
        ]
    }

    print("[Jina-OCR API] Sending request to api.jina.ai...")
    response = requests.post(url, headers=headers, json=payload, timeout=120)
    response.raise_for_status()
    result = response.json()
    return result["choices"][0]["message"]["content"]


def test_jina_ocr():
    """Pytest test case for Jina-OCR."""
    sample_pdf = "pk_pipeline/test_data/s12249-023-02680-y.pdf"
    if not os.path.exists(sample_pdf):
        print(f"[Skip] Sample PDF not found: {sample_pdf}")
        return

    print("\n--- Running Jina-OCR Test Case ---")
    img = render_pdf_page_to_image(sample_pdf, page_number=6, dpi=150)
    assert img is not None
    assert img.width > 0 and img.height > 0
    print(f"Rendered test image: size={img.size}")


def main():
    parser = argparse.ArgumentParser(description="Test jinaai/jina-ocr-v1 Document OCR")
    parser.add_argument("--pdf", type=str, default="pk_pipeline/test_data/s12249-023-02680-y.pdf", help="Path to PDF")
    parser.add_argument("--page", type=int, default=6, help="1-indexed PDF page to render")
    parser.add_argument("--image", type=str, default=None, help="Path to existing image file (overrides --pdf)")
    parser.add_argument("--model", type=str, default="jinaai/jina-ocr-v1", help="Model ID on Hugging Face")
    parser.add_argument("--max-tokens", type=int, default=4096, help="Maximum new tokens")
    parser.add_argument("--output", type=str, default="test/jina_ocr_output.md", help="Output Markdown file path")
    parser.add_argument("--use-api", action="store_true", help="Use Jina Hosted API instead of local model (requires JINA_API_KEY)")
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

    # 2. Run Jina-OCR
    try:
        if args.use_api:
            print("[Jina-OCR] Running via hosted Jina API...")
            md_result = run_jina_ocr_api(image=img, prompt=DEFAULT_PROMPT)
        else:
            print(f"[Jina-OCR] Running local inference with model '{args.model}'...")
            md_result = run_jina_ocr_local(
                image=img,
                model_id=args.model,
                max_new_tokens=args.max_tokens,
                prompt=DEFAULT_PROMPT
            )

        # 3. Save and display result
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(md_result)

        print(f"\n{'='*60}")
        print(f"  Jina-OCR Output Preview (first 500 chars):")
        print(f"{'='*60}")
        print(md_result[:500] + ("..." if len(md_result) > 500 else ""))
        print(f"{'='*60}")
        print(f"Full result successfully saved to: {args.output}\n")

    except Exception as e:
        print(f"\n[Error] Jina-OCR execution failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
