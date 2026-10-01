import json
import logging
from typing import Dict, List

from PIL import Image

logger = logging.getLogger(__name__)

async def digitize_figure(image_path: str, server_url: str = "http://127.0.0.1:30000") -> List[Dict]:
    """
    Uses the Vision-Language Model to extract data points from a figure.
    Returns a list of dicts: [{'series': 'PFOA', 'data': [{'time': 1.0, 'concentration': 2.5}, ...]}]
    """
    import aiohttp
    
    system_prompt = (
        "You are an expert data digitizer. "
        "This is a concentration-time plot. Extract all data series as a strict JSON array of objects. "
        "Each object should have a 'series' name (e.g. the compound or dose group) and a 'data' array "
        "of {'time': float, 'concentration': float} pairs. "
        "Do not include any text outside the JSON array."
    )
    
    prompt_text = (
        f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
        f"<|im_start|>user\n<|vision_start|><|image_pad|><|vision_end|>"
        f"Extract the data points from this plot.<|im_end|>\n"
        f"<|im_start|>assistant\n"
    )
    
    schema = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "series": {"type": "string"},
                "data": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "time": {"type": "number"},
                            "concentration": {"type": "number"}
                        },
                        "required": ["time", "concentration"]
                    }
                }
            },
            "required": ["series", "data"]
        }
    }
    
    try:
        timeout = aiohttp.ClientTimeout(total=600)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            payload = {
                "text": prompt_text,
                "image_data": image_path,
                "sampling_params": {
                    "max_new_tokens": 4000,
                    "temperature": 0.0,
                    "json_schema": json.dumps(schema)
                }
            }
            async with session.post(f"{server_url}/generate", json=payload) as resp:
                result = await resp.json()
                extracted_text = result["text"]
                
        # Parse JSON
        import re
        match = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", extracted_text, re.DOTALL)
        if match:
            extracted_text = match.group(1).strip()
        else:
            extracted_text = extracted_text.strip()
            
        return json.loads(extracted_text)
    except Exception as e:
        logger.error(f"Figure digitization failed: {e}")
        return []
