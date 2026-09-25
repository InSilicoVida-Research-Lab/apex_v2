import asyncio
import aiohttp
import json
from pk_pipeline.schemas import ExtractedPage
import time

async def main():
    payload = {
        "text": "Extract all pharmacokinetic parameters from this table:\nTable 1\nParameter | Value\nClearance | 10 L/hr",
        "sampling_params": {
            "max_new_tokens": 1000,
            "temperature": 0.0,
            "json_schema": json.dumps(ExtractedPage.model_json_schema())
        }
    }
    
    start_t = time.time()
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20)) as session:
            async with session.post("http://127.0.0.1:30000/generate", json=payload) as resp:
                result = await resp.json()
                print(f"Time: {time.time()-start_t:.1f}s")
                print(f"Result: {result.get('text', '')}")
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(main())
