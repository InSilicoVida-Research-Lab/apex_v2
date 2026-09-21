import asyncio
from pk_pipeline.schemas import ExtractionRequest
from pk_pipeline.main import run_pipeline
import json

async def test():
    print("Running pipeline test...")
    # Use the pdf provided by the user for testing
    pdf_path = "pk_pipeline/test_data/Dean et al. 2025 3 compartment (PFOA, PFOS, PFHxS).pdf"
    
    try:
        result = await run_pipeline(
            pdf_path=pdf_path,
            target_compounds=["PFOS", "PFOA", "PFHxS"]
        )
        print("Pipeline execution successful!")
        print("Result:")
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Pipeline execution failed: {e}")

if __name__ == "__main__":
    asyncio.run(test())
