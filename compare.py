import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
input_path = ROOT / "pk_pipeline" / "test_data" / "Dean et al. 2025 3 compartment (PFOA, PFOS, PFHxS).json"

with open(input_path, 'r') as f:
    benchmark = json.load(f)

# Pipeline extracted values
pipeline_values = [
    "k12", "k21", "Vcc × BW", "k12/k21 × Vc", "VfilC × BW", "k12 × Vc", "QfilC × QCC × BW^0.74", "Tmc × BW", "Kt",
    "0.3", "0.5", "12.5",
    "5", "19.8", "0.15", "4.00E-04", "0.9", "0.17", "0.21", "0.004", "0.0009", "3.3", "3.4", "132",
    "70", "12.5", "0.47", "5.3"
]

# Benchmark values
benchmark_params = benchmark.get("parameters", [])
benchmark_values = []
for p in benchmark_params:
    if "quantitative_data" in p and p["quantitative_data"] is not None:
        q = p["quantitative_data"]
        val = q.get("value_text")
        if val is None:
            val = q.get("value")
        if val is not None:
            benchmark_values.append(str(val))
    elif p.get("value_text") is not None:
        benchmark_values.append(str(p["value_text"]))
    elif p.get("value") is not None:
        benchmark_values.append(str(p["value"]))

# Clean up values for comparison
pipeline_clean = [v.split()[0] if "(" in v else v for v in pipeline_values]

matched = []
unmatched_pipeline = list(pipeline_clean)
unmatched_benchmark = list(benchmark_values)

for pv in pipeline_clean:
    found = False
    for bv in unmatched_benchmark:
        try:
            if float(pv) == float(bv):
                matched.append((pv, bv))
                unmatched_benchmark.remove(bv)
                unmatched_pipeline.remove(pv)
                found = True
                break
        except ValueError:
            if pv == bv:
                matched.append((pv, bv))
                unmatched_benchmark.remove(bv)
                unmatched_pipeline.remove(pv)
                found = True
                break

print(f"Total pipeline values extracted: {len(pipeline_values)}")
print(f"Total benchmark values expected: {len(benchmark_values)}")
print(f"Values perfectly matched: {len(matched)}")
print("\nMatched pairs:")
for p, b in matched:
    print(f"  Pipeline: {p} == Benchmark: {b}")

print("\nUnmatched from Pipeline:")
for u in unmatched_pipeline:
    print(f"  {u}")

print("\nUnmatched from Benchmark:")
for u in unmatched_benchmark:
    print(f"  {u}")

