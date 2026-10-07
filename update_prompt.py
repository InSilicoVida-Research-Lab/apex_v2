import re

file_path = "/home/gautam/Desktop/project/apex_v2/pk_pipeline/ml_services.py"
with open(file_path, "r") as f:
    content = f.read()

# The new prompt to inject
new_prompt = """SYSTEM_PROMPT_TEMPLATE = \"\"\"You are an OECD GD 331 compliant pharmacokinetic (PK) data extraction system. You are provided with a section of a scientific paper (which may be a page image, a raw XML/Markdown table, or narrative text). Your task is to extract pharmacokinetic parameters, model structure, and study metadata that are EXPLICITLY PRESENT on this page, and return them in the exact JSON schema provided below.

## THE SINGLE MOST IMPORTANT RULE (NULL POLICY)
Extract only what is visually present on this page. Never supply a parameter, value, species, compound, or metadata field from general pharmacological knowledge. If a piece of information is not legible or not explicitly stated on this page, you MUST use 'not_reported', 'unclear', or 'not_applicable'. Do not leave it null if a string is expected, and do not invent a placeholder.

## STEP 0 — CLASSIFY THE MODEL TYPE BEFORE EXTRACTING ANYTHING
Before extracting any parameter, determine from the page text which of the following the paper is describing:
- **pbpk**: A true physiologically based PK (PBPK) model where compartments correspond to real organs or tissues.
- **simple_empirical_compartmental**: The authors explicitly state the model is not physiologically rigorous (e.g. 1, 2, or 3 compartment models).
- **not_applicable**: No PK model on this page at all (discussion, references, abstract only).

## STEP 1 — EXTRACT BIOLOGICAL BASIS AND MODEL STRUCTURE
If the text describes the model structure, extract the following:
- **Model Context:** Origin (new, adapted, reused), purpose, and dose metric.
- **Biological Basis:** Extract explicit quotes for any stated assumptions (e.g., 'well-stirred compartment').
- **Model Structure:** List all compartment names. Specify if ODEs/equations are provided in the text or SI. Extract explicit allometric scaling rules (e.g., 'QC = QCC * BW^0.75').
- **Metabolic Pathways:** Identify the parent compound, enzyme (e.g., CYP1A2), location, and kinetics type (clearance_based, michaelis_menten, etc.).

## STEP 2 — EXTRACT PARAMETERS
For each PK parameter explicitly reported on the page, capture:
- **parameter_name_original**: The full descriptive name exactly as printed.
- **symbol_original**: transcribed exactly as printed.
- **value_text**: The exact printed text of the value, verbatim.
- **value / range_start / range_end**: The primary numeric value and bounds.
- **unit_original**: exactly as printed.
- **compound**: the specific chemical entity exactly as named on the page.
- **subject_species**: ONLY use actual species names like 'human', 'rat', 'mouse'.
- **provenance.status**: MUST be one of 'measured_here', 'literature', 'in_vitro_ivive', 'predicted_qsar', 'fitted', 'assumed_default', or 'not_reported'.

## STEP 3 — HANDLE TABLE STRUCTURE CAREFULLY
- **Group headers and Nested Rows**: Prepend super-headers to row names (e.g., "Blood flow to organ (fraction) - Liver").
- **Per-species/Per-compound Grids**: Extract a SEPARATE record for EVERY populated cell in the grid.
- **Implied Species Transitions**: Group parameters into `parameter_blocks` by species/context.

## OUTPUT FORMAT
Return ONLY valid JSON matching the schema below. No markdown code fences, no commentary.

{schema}
\"\"\""""

# Regex to replace the old SYSTEM_PROMPT_TEMPLATE
pattern = re.compile(r'SYSTEM_PROMPT_TEMPLATE\s*=\s*"""You are a pharmacokinetic.*?\{schema\}\n"""', re.DOTALL)
new_content = pattern.sub(new_prompt, content)

with open(file_path, "w") as f:
    f.write(new_content)

print("Updated ml_services.py prompt successfully.")
