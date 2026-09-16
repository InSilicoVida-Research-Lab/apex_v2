import asyncio
from schemas import ExtractionRequest
from main import extract_pk_data
import json

async def test():
    print("Running pipeline test...")
    # Use the pdf provided by the user for testing
    pdf_path = "../test_data/Dean et al. 2025 3 compartment (PFOA, PFOS, PFHxS).pdf"
    request = ExtractionRequest(
        pdf_path=pdf_path,
        target_compounds=["PFOS", "PFOA", "PFHxS"] # Users can now optionally steer the retriever!
    )
    
    try:
        result = await extract_pk_data(request)
        print("Pipeline execution successful!")
        print("Result:")
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Pipeline execution failed: {e}")

if __name__ == "__main__":
    asyncio.run(test())
