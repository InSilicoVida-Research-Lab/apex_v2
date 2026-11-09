# APEX v2 — Initial Laptop Setup Guide

A complete, step-by-step walkthrough for setting up the **APEX v2** project on any developer's laptop (Linux, macOS, or Windows).

---

## 1. System Prerequisites

Before touching the code, ensure the following core tools and system libraries are installed on your machine.

### Operating System Support
* **Linux (Ubuntu / Debian / Fedora / Arch)**: Native support.
* **macOS (Apple Silicon M1/M2/M3 or Intel)**: Native support for client/test mode.
* **Windows 10 / 11**: Supported via PowerShell/CMD (in client mode), or natively inside **WSL2 (Ubuntu)** (strongly recommended if running local GPU workloads).

---

### Step 1.1: Install Python (3.10 to 3.12) & Git

> [!IMPORTANT]
> Python **3.11** or **3.12** (64-bit) is recommended. Python 3.13 is currently too new for several scientific packages (e.g., PyTorch, Tellurium).

* **Ubuntu / Debian**:
  ```bash
  sudo apt update
  sudo apt install -y git python3 python3-venv python3-pip
  ```
* **macOS (via Homebrew)**:
  ```bash
  brew install git python@3.12
  ```
* **Windows**:
  - Download Python 3.12 from [python.org](https://www.python.org/downloads/).
  - **Check the box: "Add Python to PATH"** during installation.
  - Download and install [Git for Windows](https://git-scm.com/download/win).

---

### Step 1.2: Install System Libraries (Poppler & OpenCV support)

The pipeline uses `pdf2image` (requires Poppler) and `opencv-python` (requires rendering libraries).

* **Ubuntu / Debian**:
  ```bash
  sudo apt install -y poppler-utils libgl1 libglib2.0-0 build-essential
  ```
* **macOS**:
  ```bash
  brew install poppler
  ```
* **Windows**:
  1. Download the latest binary zip from [poppler-windows releases](https://github.com/oschwartz10612/poppler-windows/releases/).
  2. Extract it to `C:\Program Files\poppler` (or `C:\tools\poppler`).
  3. Add the `bin/` directory (e.g. `C:\Program Files\poppler\Library\bin`) to your Windows User or System `PATH`.

---

## 2. Clone the Repository

Open your terminal (or PowerShell on Windows) and clone the repository:

### Using HTTPS:
```bash
git clone https://github.com/gautampt19/apex_v2.git
cd apex_v2
```

### Or Using SSH (if you have GitHub SSH keys configured):
```bash
git clone git@github.com:gautampt19/apex_v2.git
cd apex_v2
```

---

## 3. Create & Activate the Virtual Environment (`.venv`)

Isolate your project dependencies by creating a dedicated virtual environment named `.venv`.

### On Linux & macOS:
```bash
# Create the virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate
```

### On Windows (PowerShell):
```powershell
# Create the virtual environment
python -m venv .venv

# If script execution is restricted, run this once:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Activate it
.venv\Scripts\Activate.ps1
```

### On Windows (Command Prompt `cmd.exe`):
```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

> [!TIP]
> After activation, your shell prompt should show `(.venv)`.
> Confirm your Python executable is pointing to `.venv`:
> ```bash
> which python    # (or 'where python' on Windows)
> ```

---

## 4. Install Dependencies

### Step 4.1: Upgrade Package Managers
```bash
pip install --upgrade pip setuptools wheel
```

### Step 4.2: Install Requirements
```bash
pip install -r requirements.txt
```

> [!NOTE]
> **Windows/Mac users**: The `requirements.txt` file is designed to be cross-platform. Linux-only heavy GPU serving frameworks (`sglang`, `vllm`) are automatically skipped on non-Linux platforms because on a laptop, APEX v2 connects remotely to an inference server (via the `openai` client) rather than hosting the LLM locally.

### Step 4.3: Install Testing Dependencies
```bash
pip install pytest pytest-asyncio
```

---

## 5. Configure Environment Variables (`.env`)

APEX v2 reads its configuration from a local `.env` file.

1. Copy the provided template:
   ```bash
   # Linux / macOS
   cp .env.example .env

   # Windows (CMD)
   copy .env.example .env

   # Windows (PowerShell)
   Copy-Item .env.example .env
   ```

2. Review the settings in `.env`:
   ```ini
   # --- Priority 1: Local SGLang Server (Port 30000) ---
   SGLANG_LOCAL_URL=http://127.0.0.1:30000

   # --- Priority 2: Direct DGX SGLang Server (Port 30001 via Tailscale/VPN) ---
   DGX_SGLANG_URL=http://100.85.128.70:30001

   # --- Priority 3: OpenAI-Compatible API Endpoint ---
   OPENAI_BASE_URL=http://100.85.128.70:30001/v1
   OPENAI_API_KEY=EMPTY
   OPENAI_MODEL=Qwen/Qwen3.8-27B-FP8

   # --- Backend Selection ---
   # "auto" (default: auto-detects between local, DGX, and OpenAI API), or "openai_api"
   FORCE_BACKEND=auto

   # --- Logging & Mocks ---
   LOG_LEVEL=INFO
   OUTPUT_DIR=output
   USE_MOCKS=False
   ```

### Choosing your runtime mode:
* **Mode A: Local Offline Development (No GPU / No remote server needed)**
  Set `USE_MOCKS=True` in `.env`. All LLM calls will return stubbed responses, allowing you to run unit tests and verify pipeline flows offline.
* **Mode B: Connected to DGX / Lab Server (Requires VPN / Tailscale)**
  Ensure your VPN or Tailscale is active and reachable:
  ```bash
  curl -s http://100.85.128.70:30001/v1/models
  ```
  Keep `USE_MOCKS=False` and `FORCE_BACKEND=auto`.

---

## 6. Verify the Setup

Ensure your working directory is in `PYTHONPATH` before running tests or scripts.

### Set `PYTHONPATH`:
* **Linux / macOS**:
  ```bash
  export PYTHONPATH=.
  ```
* **Windows (PowerShell)**:
  ```powershell
  $env:PYTHONPATH="."
  ```
* **Windows (CMD)**:
  ```cmd
  set PYTHONPATH=.
  ```

---

### Step 6.1: Validate Curated PBPK Reference Corpus (0 GPU, <2s)
Verify that the dataset manifest, checksums, and schema contracts match:
```bash
python -m pk_pipeline.corpus validate
```
Expected output:
```text
Validation succeeded: 5 paper(s) verified against manifest.
```

---

### Step 6.2: Run Fast Offline Unit Tests (~15s)
Run all unit tests (ignoring live LLM network calls):
```bash
pytest test/test_tan_assessor.py test/test_tan_markdown_assessment.py \
  -k "not test_llm_answers_tan_questions_from_markdown" \
  -v --tb=short
```
Expected result: **15 passed**.

---

### Step 6.3: Run a Dry-Run Pipeline Assessment (~10s)
Perform an end-to-end dry-run conversion of a test paper:
```bash
python test/test_tan_markdown_assessment.py --paper dean --dry-run
```
This tests PDF-to-Markdown conversion, table extraction, section splitting, and questionnaire routing without consuming LLM tokens.

---

## 7. Daily Workflow Cheat Sheet

Whenever you start a new session:

```bash
# 1. Navigate to project
cd apex_v2

# 2. Activate environment
source .venv/bin/activate       # (or .venv\Scripts\Activate.ps1 on Windows)

# 3. Ensure PYTHONPATH is set
export PYTHONPATH=.             # (or $env:PYTHONPATH="." on Windows)

# 4. Run pipeline on a paper
python -m pk_pipeline.main "pk_pipeline/test_data/Dean et al. 2025 3 compartment (PFOA, PFOS, PFHxS).pdf"
```

---

## 8. Common Gotchas & Troubleshooting

| Error | Root Cause | Solution |
| :--- | :--- | :--- |
| `pdf2image.exceptions.PDFInfoNotInstalledError: Unable to get page count` | **Poppler is not installed or not on PATH.** | Install Poppler: `sudo apt install poppler-utils` (Linux), `brew install poppler` (macOS), or download Windows binary and add `bin/` to system PATH. |
| `ModuleNotFoundError: No module named 'pk_pipeline'` | Python does not know the project root directory. | Run `export PYTHONPATH=.` (Linux/Mac) or `$env:PYTHONPATH="."` (PowerShell). |
| `FileNotFoundError: .env` or defaults not loading | `.env` has not been created. | Copy from template: `cp .env.example .env`. |
| `Connection refused: http://100.85.128.70:30001` | DGX server unreachable. | Ensure your Tailscale/VPN is connected. If offline, set `USE_MOCKS=True` in `.env` to work locally. |
| Windows build errors with `flashinfer` or `triton` | Tried installing Linux-only GPU packages on Windows. | Do not install `sglang` or `vllm` directly on Windows. Use `pip install -r requirements.txt` which skips them via platform markers. |
| `ImportError: libGL.so.1: cannot open shared object file` (Linux) | Missing system rendering library for OpenCV. | Run: `sudo apt install -y libgl1 libglib2.0-0`. |

