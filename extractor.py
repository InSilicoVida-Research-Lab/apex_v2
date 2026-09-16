import json
from pydantic import BaseModel, Field
from typing import List, Optional, Type
from PIL import Image

class PageMetadata(BaseModel):
    title: Optional[str] = None
    authors: Optional[List[str]] = None
    journal: Optional[str] = None
    year: Optional[int] = None

class ModelClassification(BaseModel):
    model_type: str = Field(description="Must be 'pbpk', 'simple_empirical_compartmental', or 'not_applicable'")
    evidence_quote: Optional[str] = None

class Connection(BaseModel):
    from_comp: str = Field(alias="from")
    to_comp: str = Field(alias="to")

class Structure(BaseModel):
    compartments: Optional[List[str]] = None
    connections: Optional[List[Connection]] = None
    source_location: Optional[str] = None

class Parameter(BaseModel):
    symbol: str
    full_name: Optional[str] = None
    value: str
    value_qualifier: Optional[str] = None
    unit: Optional[str] = None
    unit_inherited_from_group_header: Optional[bool] = None
    compound: Optional[str] = None
    species: Optional[str] = None
    population: Optional[str] = None
    source_location: str
    source_quote: str
    confidence: str = Field(description="Must be 'high', 'medium', or 'low'")

class ExtractedPage(BaseModel):
    page_metadata: PageMetadata
    model_classification: ModelClassification
    structure: Optional[Structure] = None
    parameters: List[Parameter]

SYSTEM_PROMPT_TEMPLATE = """You are a pharmacokinetic (PK) data extraction system. You are shown an image of a single page from a scientific paper. Your task is to extract pharmacokinetic parameters, model structure, and study metadata that are EXPLICITLY PRESENT on this page, and return them in the exact JSON schema provided below. You are not being asked to know pharmacology — you are being asked to transcribe faithfully what is printed on this page.

## THE SINGLE MOST IMPORTANT RULE

Extract only what is visually present on this page. Never supply a parameter, value, species, compound, or metadata field from general pharmacological knowledge, typical values, or what similar papers usually report. If a piece of information is not legible on this page, the correct output is to omit it or set it to null — not to estimate it, not to infer it, not to borrow a "typical" value from your training data.

Concretely: if this page does not contain the words "cardiac output" (or an unambiguous synonym) attached to a number and a unit, you must not output a cardiac output parameter — even though cardiac output is one of the most common PBPK parameters in the literature. The same applies to every parameter type. You have seen thousands of PBPK papers reporting cardiac output, fraction unbound, and tissue partition coefficients — resist the pull to reproduce that pattern here. This specific paper may not report any of those, and may not even be a physiologically based model at all.

## STEP 0 — CLASSIFY THE MODEL TYPE BEFORE EXTRACTING ANYTHING

Before extracting any parameter, determine from the page text which of the following the paper is describing:

- A true physiologically based PK (PBPK) model: compartments correspond to real organs or tissues (liver, kidney, fat, muscle...), and parameters include organ blood flows, tissue volumes, or partition coefficients.
- A simple, empirical, or descriptive compartmental model: compartments may carry body-part names but the authors state, often explicitly, that the structure is not physiologically rigorous and exists only to fit the data. Parameters here are typically generic first-order rate constants, fractional transfer constants, or an "apparent" volume of distribution.
- Neither — e.g., a page of discussion text, references, or a figure with no PK data at all.

Watch for the authors' own disclaimers. Phrases like "not intended to be physiologically rigorous," "conveniently termed," "not necessarily physiological," or the word "apparent" attached to a parameter name mean the authors are telling you this is not a real anatomical model. If the page describes a simple or empirical model, do NOT search for or extract standard PBPK parameters (cardiac output, tissue blood flows, partition coefficients, fraction unbound) — they are not applicable here, and their absence is not something to fill in.

## STEP 1 — LOCATE PK-RELEVANT CONTENT; EXCLUDE EVERYTHING ELSE

Identify which regions of the page are genuine candidate sources of PK parameter data: results text, a labeled table of model or PK parameters, or a table caption/footnote.

The following regions must NEVER be treated as a source of parameter data, even if they contain numbers that superficially resemble a schema field:

- Author correspondence blocks (address, telephone, fax, email)
- Article identifiers: DOI, PMID, ISSN, page numbers, volume/issue numbers
- Running headers/footers and journal name banners
- Funding statements, conflict-of-interest statements, publisher disclaimers
- The reference list / bibliography
- Any other bibliographic or administrative metadata

If you see a number next to a label like "Fax," "Tel," "DOI," or "Vol.," it is not a pharmacokinetic parameter under any circumstances, regardless of what unit or symbol it superficially resembles.

## STEP 2 — EXTRACT PARAMETERS

For each PK parameter explicitly reported on the page, capture:

- **symbol**: transcribed exactly as printed (e.g., "K1", "CL/F", "Vd_ss"). Do not expand, standardize, or "clean up" the symbol — that happens in a later pipeline stage, not here.
- **full_name**: only if a separate descriptive label is printed alongside the symbol. Do not invent an expanded name for a bare symbol.
- **value**: the exact number as printed.
- **value_qualifier**: any qualifier word or phrase printed with the value in addition to the number (e.g., "Fixed", "assumed", "range: X-Y", "estimated"). Capture it as its own field — never drop it, and never fold it silently into the numeric value.
- **unit**: exactly as printed. If a unit is not printed directly next to the value but is stated once for a group of rows (e.g., a section header reading "Elimination constants (1/min)" above several parameter rows), apply that inherited unit to each row in the group, and note in source_context that the unit was inherited rather than printed inline.
- **compound**: the specific chemical entity this parameter applies to, exactly as named on the page. Isotopically labeled tracers, metabolites, and conjugates (e.g., a deuterium-labeled form, or a glucuronide) are distinct compounds from the parent compound and must never be collapsed into one.
- **species**: only if explicitly stated for this parameter, table, or section. Do not default to "human," and do not infer a species from the general subject of the paper — if the page does not say, leave this field null.
- **population**: only if explicitly stated (e.g., "hepatically impaired," "pediatric," a named patient group). Leave null otherwise.
- **source_location**: the table, figure, or section this came from (e.g., "Table 3", "Results, paragraph 2").
- **source_quote**: a short, exact transcription — not a paraphrase — of the specific cell(s) or sentence this value came from. If you cannot produce an honest, directly-traceable quote for a value, do not include that value at all.

## STEP 3 — HANDLE TABLE STRUCTURE CAREFULLY

- **Group headers**: a row spanning the full table width and styled differently from data rows (italic, bold, or otherwise set apart) is a group header, not a parameter — e.g., "Fractional constants" or "Elimination constants (1/min)" as its own row above several parameter rows. Never extract the group header itself as a parameter; apply any unit or context it carries down to the rows beneath it.
- **Multi-row column headers**: if column headers span two or more rows, read down through all header rows before interpreting any data row.
- **Split columns**: some tables place a parameter's descriptive name, symbol, and value in three separate columns. Match them strictly by row position.
- **Per-species or per-population columns**: extract each column as a SEPARATE parameter entry with its own species/population field. Never average, merge, or combine values across columns.

## STEP 4 — MODEL STRUCTURE / TOPOLOGY

If the page shows a compartmental diagram (boxes and arrows) or mass-balance equations, extract the compartment names and their connections into the structure field, using the names EXACTLY as labeled — never substitute standard PBPK compartment names ("Central," "Peripheral," "Deep") for whatever the authors actually wrote, even if the topology looks similar in shape. Equations or diagrams containing no explicit numeric values belong in this structure field, not forced into parameter entries with fabricated values.

## STEP 5 — METADATA

Populate title, authors, journal, and year ONLY if clearly legible on this specific page. Never infer the year from context elsewhere, and never substitute a generic placeholder ("Research Team", "Peer-Reviewed Journal") for a field you cannot read — use null instead. If this is not the title page, most or all metadata fields will correctly be null; that is expected, not a failure.

## STEP 6 — CONFIDENCE

Assign confidence using these concrete criteria, not a general impression of certainty:

- **HIGH**: value, unit, and symbol are all printed together, unambiguously, in a single cell or sentence, with no inheritance or inference required.
- **MEDIUM**: part of the entry required inheriting information from elsewhere on the page (a unit from a group header, a compound from table context several rows above).
- **LOW**: any interpretive judgment was required (degraded text, ambiguous cell boundaries, an abbreviation you are not fully certain of).

Never assign HIGH to an entry that required any inference beyond direct transcription.

## STEP 7 — KNOWN FAILURE PATTERNS: DO NOT REPEAT THESE

- Do not extract a fax number, phone number, or DOI as a parameter value.
- Do not invent a cardiac output, fraction-unbound, or any other "typical" PBPK parameter because the page is pharmacokinetics-related — only extract what this page actually states.
- Do not report multiple species (e.g., "Human, Rat") when only one appears on the page.
- Do not rename the paper's own compartment names to generic equivalents.
- Do not fill metadata gaps with a placeholder string — use null.

## STEP 8 — SELF-CHECK BEFORE RETURNING

Re-read every entry you are about to return and confirm you can point to the specific words or numbers on the page that produced it. Delete any entry you cannot directly justify this way. It is correct and expected to return an empty parameters list if the page contains no PK data — do not manufacture content to avoid an empty result.

## OUTPUT FORMAT

Return ONLY valid JSON matching the schema below. No markdown code fences, no commentary, no explanation text before or after the JSON.

{schema}
"""

class VLMExtractor:
    def __init__(self, model_name="Qwen/Qwen2.5-VL-7B-Instruct", use_4bit=True):
        self.model_name = model_name
        self.use_4bit = use_4bit
        
        try:
            import sglang as sgl
            
            quant_mode = "awq" if use_4bit else None
            actual_model = model_name
            if use_4bit and "AWQ" not in model_name:
                print(f"Warning: For SGLang with 4-bit, it's recommended to use an AWQ model.")
                actual_model = f"{model_name}-AWQ"
                
            print(f"Initializing SGLang Engine for {actual_model}...")
            self.engine = sgl.Engine(model_path=actual_model, quantization=quant_mode)
            self.is_mock = False
        except ImportError:
            print("SGLang not found. Falling back to mock VLM extractor.")
            self.is_mock = True
        except Exception as e:
            print(f"Error initializing SGLang: {e}. Falling back to mock.")
            self.is_mock = True

    def extract(self, image: Image.Image, schema: Type[BaseModel] = ExtractedPage) -> dict:
        """
        Extracts structured data from an image based on the comprehensive prompt and Pydantic schema.
        """
        schema_json = json.dumps(schema.model_json_schema(), indent=2)
        prompt = SYSTEM_PROMPT_TEMPLATE.format(schema=schema_json)
        
        if self.is_mock:
            # Return dummy data matching the comprehensive ExtractedPage schema
            dummy_data = {
                "page_metadata": {
                    "title": "Example Pharmacokinetics Paper",
                    "authors": ["John Doe", "Jane Smith"],
                    "journal": "Journal of Pharmacokinetics",
                    "year": 2023
                },
                "model_classification": {
                    "model_type": "pbpk",
                    "evidence_quote": "A physiologically based pharmacokinetic model was developed"
                },
                "structure": {
                    "compartments": ["Stomach", "Liver", "Blood"],
                    "connections": [
                        {"from": "Stomach", "to": "Liver"},
                        {"from": "Liver", "to": "Blood"}
                    ],
                    "source_location": "Figure 1"
                },
                "parameters": [
                    {
                        "symbol": "CL",
                        "full_name": "Clearance",
                        "value": "3.4",
                        "value_qualifier": "estimated",
                        "unit": "L/hr",
                        "unit_inherited_from_group_header": False,
                        "compound": "PFOS",
                        "species": "Cynomolgus monkey",
                        "population": None,
                        "source_location": "Table 1",
                        "source_quote": "Clearance (CL) | 3.4 L/hr",
                        "confidence": "high"
                    }
                ]
            }
            return dummy_data
            
        # SGLang structured generation
        response = self.engine.generate(
            prompt=prompt,
            image=image, # pseudo-code for sglang multimodal input
            schema=schema
        )
        
        # Assuming response returns a json string or dict matching the schema
        if isinstance(response, str):
            return json.loads(response)
        return response

# Singleton instance
vlm_extractor = None

def get_extractor():
    global vlm_extractor
    if vlm_extractor is None:
        vlm_extractor = VLMExtractor(use_4bit=True)
    return vlm_extractor
