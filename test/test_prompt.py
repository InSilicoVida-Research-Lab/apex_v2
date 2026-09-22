import sys
import os
import asyncio
import time
import json
import argparse

# Add parent directory to path so we can import pk_pipeline
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pk_pipeline.ml_services import get_extractor

async def main():
    parser = argparse.ArgumentParser(description="Test a specific prompt file with SGLang")
    parser.add_argument("--prompt", required=True, help="Path to the .txt prompt file")
    args = parser.parse_args()
    
    prompt_path = args.prompt
    if not os.path.exists(prompt_path):
        print(f"File not found: {prompt_path}")
        sys.exit(1)
        
    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt_content = f.read()
        
    # The prompt file contains the fully formatted ChatML template (with <|im_start|>, etc.)
    # Since `extract_from_text` applies that template automatically, we need to extract 
    # just the raw Document Text to avoid double-wrapping the prompt.
    if "Document Text:\n" in prompt_content:
        doc_text = prompt_content.split("Document Text:\n")[1].replace("<|im_end|>\n<|im_start|>assistant\n", "").strip()
        role = "table_xml" if "raw HTML/XML table" in prompt_content else "narrative_xml"
    else:
        print("Error: Could not find 'Document Text:\\n' marker in the prompt.")
        sys.exit(1)
        
    print(f"Loaded prompt from: {prompt_path}")
    print(f"Inferred Role: {role}")
    
    print("\nBooting SGLang Engine (this takes ~1-2 minutes)...")
    extractor = get_extractor()
    
    print("Starting extraction...")
    start_time = time.time()
    
    # Run the extraction
    res = await extractor.extract_from_text(doc_text, role=role, chunk_title="Test_Chunk")
    
    duration = time.time() - start_time
    
    print(f"\n" + "="*80)
    print(f"✅ Extraction complete in {duration:.2f} seconds.")
    print("="*80)
    print(json.dumps(res.model_dump(), indent=2))

if __name__ == "__main__":
    asyncio.run(main())
