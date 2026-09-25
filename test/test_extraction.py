import asyncio
from pk_pipeline.main import run_pipeline
import traceback

async def test():
    try:
        await run_pipeline("pk_pipeline/test_data/Verner et al. 2016 2 compartment (PFOA, PFOS, PFHxS).pdf")
    except Exception as e:
        print(f"FAILED: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
