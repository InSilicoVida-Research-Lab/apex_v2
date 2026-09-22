import asyncio
from PIL import Image
from ml_services import SGLangExtractor
import json

async def main():
    img = Image.open('test_data/Loccisano 2013_vlm_inputs/page_07.png') # Page 34 is 7th in the list
    extractor = SGLangExtractor(use_4bit=True)
    res = await extractor.extract_data(img)
    print(json.dumps(res.model_dump(), indent=2))

if __name__ == "__main__":
    asyncio.run(main())
