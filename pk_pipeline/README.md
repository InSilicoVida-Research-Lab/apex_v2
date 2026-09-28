# PK Pipeline (Pharmacokinetic Data Extraction)

This pipeline automatically extracts structured pharmacokinetic (PK) parameters and compartmental model structures from scientific papers (PDFs). It uses a combination of specialized layout parsers, object detection, and Vision-Language Models (VLMs) to accurately retrieve tabular and text-based data.

## Pipeline Architecture

1. **Document Triage & Filtering (Laya)**
   - Pre-flight model classification (`pbpk`, `compartmental`, `nca`) in ~20ms using `convaiinnovations/laya`.
   - Filters out irrelevant narrative pages, saving VLM compute.

2. **WeVisDoc-4B High-Fidelity Table Transcription**
   - Uses `Tencent/WeVisDoc-4B` to transcribe candidate table pages into structured Markdown with native HTML tables (`<table>`, `<tr>`, `<td>`, `rowspan`, `colspan`) and LaTeX formulas.
   - Provides clean, structured HTML evidence to the extraction model, resolving column merges and scientific notation.

3. **PyMuPDF + TATR Fallback & Boundary Guidance**
   - Uses Table Transformer (`TATR`) to perform object detection on pages.
   - Draws bounding box guidance and coordinates page imagery with extracted table context.

4. **VLM Extraction (SGLang + Qwen3-VL-8B)**
   - Extracts data strictly according to a predefined Pydantic schema using FSM-constrained decoding.
   - Identifies PK parameters (e.g. clearance, volume of distribution, half-life) alongside biological context (e.g. compound, subject species).

5. **Post-Processing**
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
