import re

with open("pk_pipeline/main.py", "r") as f:
    content = f.read()

# Fix the initializations (all 3 occurrences)
# Find final_document = { ... "model_structure": None, ... } and inject the new fields.
init_pattern = r'("model_classification":.*?,\n\s*)("model_structure": None,)'
replacement = r'\1"model_context": None,\n                "biological_basis": None,\n                \2\n                "metabolic_pathways": [],'
content = re.sub(init_pattern, replacement, content)

# Fix the XML aggregation (around line 611)
xml_agg_pattern = r'(if extracted_page and extracted_page\.model_structure and not final_document\["model_structure"\]:\n\s*final_document\["model_structure"\] = extracted_page\.model_structure\.model_dump\(by_alias=True, exclude_none=True\))'
xml_agg_replace = r'''if extracted_page and extracted_page.model_context and not final_document["model_context"]:
                        final_document["model_context"] = extracted_page.model_context.model_dump(by_alias=True, exclude_none=True)
                    if extracted_page and extracted_page.biological_basis and not final_document["biological_basis"]:
                        final_document["biological_basis"] = extracted_page.biological_basis.model_dump(by_alias=True, exclude_none=True)
                    \1
                    if extracted_page and extracted_page.metabolic_pathways:
                        final_document["metabolic_pathways"].extend([m.model_dump(by_alias=True, exclude_none=True) for m in extracted_page.metabolic_pathways])'''
content = re.sub(xml_agg_pattern, xml_agg_replace, content)

# Fix the PDF aggregation (around line 1062)
# It's essentially the exact same block but with less indentation. 
pdf_agg_pattern = r'(# Merge structure \(take the first one we find\)\n\s*if extracted_page\.model_structure and not final_document\["model_structure"\]:\n\s*final_document\["model_structure"\] = extracted_page\.model_structure\.model_dump\(by_alias=True, exclude_none=True\))'
pdf_agg_replace = r'''# Merge model_context, biological_basis, structure, pathways
        if extracted_page.model_context and not final_document["model_context"]:
            final_document["model_context"] = extracted_page.model_context.model_dump(by_alias=True, exclude_none=True)
        if extracted_page.biological_basis and not final_document["biological_basis"]:
            final_document["biological_basis"] = extracted_page.biological_basis.model_dump(by_alias=True, exclude_none=True)
        \1
        if extracted_page.metabolic_pathways:
            final_document["metabolic_pathways"].extend([m.model_dump(by_alias=True, exclude_none=True) for m in extracted_page.metabolic_pathways])'''
content = re.sub(pdf_agg_pattern, pdf_agg_replace, content)


with open("pk_pipeline/main.py", "w") as f:
    f.write(content)

print("Updated main.py successfully!")
