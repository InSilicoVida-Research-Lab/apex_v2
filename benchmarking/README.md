# PBPK Extraction Benchmarking & Comparison Suite

This folder provides a complete evaluation and benchmarking framework comparing the `apex_v2` LLM/VLM route against GROBID, GLiNER, and NuExtract across the 5 reference PBPK publications in `pk_pipeline/pbpk_data/`.

## Contents

- **[`pbpk_extraction_methods_comparison.md`](pbpk_extraction_methods_comparison.md)**:
  Detailed architectural and technical comparison report analyzing all four approaches across the 6-stage PBPK extraction lifecycle, head-to-head evaluation matrix, paper-by-paper stress testing, and architectural recommendations.
- **[`benchmark_extractors.py`](benchmark_extractors.py)**:
  Executable benchmarking framework that evaluates extracted JSON outputs against ground truth references across 7 standardized metrics (Strict & Partial F1, Value Accuracy, Unit Accuracy, Context Attribution, 95% CI Accuracy, and Topology Recall).
- **[`compare_results.py`](compare_results.py)**:
  CLI tool to inspect parameter-level matches, missed parameters, and false positives for individual papers or the entire corpus.
- **[`benchmark_results.json`](benchmark_results.json)**:
  Serialized evaluation metrics and per-paper scores.
- **[`benchmark_summary.md`](benchmark_summary.md)**:
  Summary markdown table of corpus-level performance.

## How to Run

### 1. Run All 4 Methods on the Same Paper
Runs `apex_v2`, `grobid`, `gliner`, and `nuextract` on the paper, validates all outputs into the canonical `ExtractedDocument` schema, and evaluates them against the ground truth reference:
```bash
PYTHONPATH=. .venv/bin/python benchmarking/run_all_pipelines.py \
  --pdf "pk_pipeline/pbpk_data/Dean et al. 2025 3 compartment (PFOA, PFOS, PFHxS).pdf" \
  --ref "pk_pipeline/pbpk_data/dean_pfas_compartment_update.json" \
  --paper-id "dean_2025_pfas"
```
*Outputs are saved to `benchmarking/outputs/{paper_id}/`:*
- `apex_v2.json`
- `grobid.json`
- `gliner.json`
- `nuextract.json`
- `result_template.json` (Machine-readable comparison metrics)
- `comparison_report.md` (Executive comparison report)

---

### 2. Run a Single Extraction Method for a Paper
You can run any specific method using the `--method` flag:

#### A. Run Apex v2 (Our Multimodal VLM Route)
```bash
PYTHONPATH=. .venv/bin/python benchmarking/run_all_pipelines.py \
  --pdf "pk_pipeline/pbpk_data/Dean et al. 2025 3 compartment (PFOA, PFOS, PFHxS).pdf" \
  --method apex_v2
```

#### B. Run GROBID (TEI-XML Table Pipeline)
```bash
PYTHONPATH=. .venv/bin/python benchmarking/run_all_pipelines.py \
  --pdf "pk_pipeline/pbpk_data/Dean et al. 2025 3 compartment (PFOA, PFOS, PFHxS).pdf" \
  --method grobid
```

#### C. Run GLiNER (Zero-Shot Span NER Pipeline)
```bash
PYTHONPATH=. .venv/bin/python benchmarking/run_all_pipelines.py \
  --pdf "pk_pipeline/pbpk_data/Dean et al. 2025 3 compartment (PFOA, PFOS, PFHxS).pdf" \
  --method gliner
```

#### D. Run NuExtract (Schema-Conditioned LLM Pipeline)
```bash
PYTHONPATH=. .venv/bin/python benchmarking/run_all_pipelines.py \
  --pdf "pk_pipeline/pbpk_data/Dean et al. 2025 3 compartment (PFOA, PFOS, PFHxS).pdf" \
  --method nuextract
```

---

### 3. Run Individual Pipeline Scripts Directly
Each pipeline in `benchmarking/pipelines/` can also be run standalone:
```bash
# Apex v2
PYTHONPATH=. .venv/bin/python benchmarking/pipelines/apex_v2_pipeline.py "path/to/paper.pdf"

# GROBID
PYTHONPATH=. .venv/bin/python benchmarking/pipelines/grobid_pipeline.py "path/to/paper.pdf"

# GLiNER
PYTHONPATH=. .venv/bin/python benchmarking/pipelines/gliner_pipeline.py "path/to/paper.pdf"

# NuExtract
PYTHONPATH=. .venv/bin/python benchmarking/pipelines/nuextract_pipeline.py "path/to/paper.pdf"
```

---

### 4. Evaluate and Inspect Diff Results Against Ground Truth
```bash
# Run 7-metric evaluation across all 5 benchmark papers
PYTHONPATH=. .venv/bin/python benchmarking/benchmark_extractors.py

# Inspect parameter-by-parameter diff for a specific paper
PYTHONPATH=. .venv/bin/python benchmarking/compare_results.py --paper dean_2025_pfas

# Inspect parameter-level diffs across the entire corpus
PYTHONPATH=. .venv/bin/python benchmarking/compare_results.py --all
```
