# PK Pipeline (Pharmacokinetic Data Extraction)

This pipeline automatically extracts structured pharmacokinetic (PK) parameters and compartmental model structures from scientific papers (PDFs). It uses a combination of specialized layout parsers, object detection, and Vision-Language Models (VLMs) to accurately retrieve tabular and text-based data.

## Pipeline Architecture

1. **MinerU Fast-Path Extraction (Primary)**
   - Attempts to read pre-processed structured layout JSON from `MinerU`.
   - If found, it rapidly processes text chunks and image chunks using the VLM.

2. **PyMuPDF + TATR Fallback (Secondary)**
   - If no MinerU layout is found, the pipeline falls back to extracting markdown using `pymupdf4llm`.
   - Uses Table Transformer (`TATR`) to perform object detection on every page.
   - For any page containing a table, a bright red bounding box is drawn over the table to guide the vision model.
   - The full-page image (with drawn boundaries) and text are passed to the Vision Model.

3. **VLM Extraction (SGLang + Qwen3-VL-8B)**
   - Extracts data strictly according to a predefined Pydantic schema using FSM-constrained decoding.
   - Identifies PK parameters (e.g. clearance, volume of distribution, half-life) alongside biological context (e.g. compound, subject species).

4. **Post-Processing**
   - Automatically handles comma-separated compound formulations (e.g., splitting "Compound A, Compound B").
   - Performs a regex-based sweep over the raw text to recover parameters commonly missed in dense text (e.g., specific transfer ratios).

## Setup & Requirements

- Python 3.10+
- `sglang` (for VLM inference)
- `Qwen/Qwen3-VL-8B-Instruct` model weights
- PyTorch (with CUDA support)

## Usage

Ensure the SGLang server is running in the background:
```bash
python -m sglang.launch_server \
  --model-path Qwen/Qwen3-VL-8B-Instruct \
  --port 30000 --host 127.0.0.1
```

Run the pipeline on a single PDF:
```bash
python -m pk_pipeline.main path/to/paper.pdf
```

The output will be generated as a highly structured JSON file in the `output/` directory, named after the input document.
