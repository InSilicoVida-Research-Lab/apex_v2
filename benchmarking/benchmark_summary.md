# PBPK Benchmark Evaluation Summary
**Method:** `1_ApexV2_LLM_VLM_Route`  
**Evaluated on:** 2026-10-14 16:45:37  

## Overall Corpus Performance
- **Strict F1 Score (Exact Compound, Species, Symbol, Value):** **60.99%**
- **Partial F1 Score (Symbol + Value):** **71.87%**
- **Parameter Value Accuracy (within ±1.5%):** **69.12%**
- **Compartment Topology Recall:** **40.00%**
- **Connection Topology Recall:** **40.00%**

## Per-Paper Results Table
| Paper ID | GT Params | Extracted | Strict F1 | Partial F1 | Value Acc | Comp Recall | Conn Recall |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `dean_2025_pfas` | 56 | 75 | 84.0% | 85.5% | 98.2% | 100.0% | 100.0% |
| `loccisano_2013_pfoa_pfos` | 102 | 118 | 76.4% | 76.4% | 82.3% | 100.0% | 100.0% |
| `mcnally_2019_dinch` | 96 | 83 | 59.2% | 72.6% | 55.2% | 0.0% | 0.0% |
| `riluzole_2023_pbpk` | 60 | 71 | 25.9% | 51.9% | 28.3% | 0.0% | 0.0% |
| `worley_2017_pfoa` | 27 | 47 | 59.5% | 73.0% | 81.5% | 0.0% | 0.0% |