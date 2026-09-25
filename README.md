# APEX v2 (Automated Parameter EXtraction)

APEX v2 is an advanced Pharmacokinetic (PK) parameter extraction pipeline designed to accurately parse scientific literature (PDFs) and extract structured physiological and pharmacokinetic parameters.

At its core, APEX utilizes **Qwen3-VL-8B-Instruct** (hosted via SGLang) to perform highly accurate Vision-Language extraction directly from scientific diagrams, plots, and tables. 

## Features

- **Multi-modal Extraction**: Capable of reading text, complex tables, and extracting numerical data directly from visual figures (e.g., concentration-time curves).
- **Intelligent Layout Parsing**: Uses a cascading fallback strategy for parsing complex PDF layouts:
  1. Searches for existing JATS XML or MinerU structured output.
  2. Falls back to `PyMuPDF4LLM` to chunk text and detect figures/tables.
- **Advanced Table Cropping (TATR)**: Natively integrates `microsoft/table-transformer-detection` (TATR) to automatically detect and mathematically crop borderless tables (with 40px padding), passing a clean, high-resolution image to Qwen3-VL to avoid layout distortion.
- **Concurrent Processing**: Splits documents into narrative, table, and figure chunks, processing them concurrently against the SGLang backend to maximize throughput.

## Prerequisites

- **GPU**: A dedicated GPU with sufficient VRAM to run SGLang (Qwen3-VL-8B) alongside the TATR object detection model.
- **Python**: Python 3.10+
- **SGLang**: Required for hosting the Vision-Language Model.

## Installation

1. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. *(Optional but recommended)* Start the SGLang backend server on port 30000:
   ```bash
   python -m sglang.launch_server --model-path Qwen/Qwen3-VL-8B-Instruct --port 30000
   ```

## Usage

Run the main pipeline against a target PDF:
```bash
PYTHONPATH= pk_pipeline/.venv/bin/python pk_pipeline/main.py <path_to_pdf>
```

For example:
```bash
PYTHONPATH= .venv/bin/python pk_pipeline/main.py "pk_pipeline/test_data/s12249-023-02680-y.pdf"
```

The extracted parameters will be saved as a structured JSON file in the `output/` directory alongside the original PDF.

## Architecture

* `pk_pipeline/main.py`: The core orchestrator. Handles PDF layout parsing, TATR table detection, and chunks the document into actionable LLM payloads.
* `pk_pipeline/ml_services.py`: Manages the SGLang interface, structuring prompts and schemas to enforce JSON compliance from the Vision-Language Model.
* `test_tatr.py`: Standalone script for evaluating the Microsoft Table Transformer object detection model. 
