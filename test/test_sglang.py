import asyncio
import aiohttp
import json
from pk_pipeline.schemas import ExtractedPage

async def main():
    payload = {
        "text": "Extract a parameter named Clearance with value 10.",
        "sampling_params": {
            "max_new_tokens": 100,
            "temperature": 0.0,
            "json_schema": json.dumps(ExtractedPage.model_json_schema())
        }
    }
    async with aiohttp.ClientSession() as session:
        async with session.post("http://127.0.0.1:30000/generate", json=payload) as resp:
            print(f"Status: {resp.status}")
            result = await resp.json()
            print(f"Result: {result}")
            print(f"Text: {result.get('text', '')}")

asyncio.run(main())
