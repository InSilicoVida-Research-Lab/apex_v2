import asyncio
import sys
import os
from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from pk_pipeline.main import get_extractor

async def main():
    extractor = get_extractor()
    img_path = "output/test_fallback/s12249-023-02680-y_page_6_screenshot.png"
    md_path = "output/test_fallback/s12249-023-02680-y_page_6_context.md"
    
    with open(md_path, "r") as f:
        md_text = f.read()
        
    img = Image.open(img_path)
    
    print("Testing with full_page role (Image + Text)...")
    try:
        res = await extractor.extract_data(img, role="full_page", evidence_text=md_text, chunk_title="Page 6")
        print(f"Extracted {len(res.parameters)} parameters using Image + Text.")
    except Exception as e:
        print(f"Image + Text failed: {e}")
        
    print("\nTesting with text only...")
    try:
        res2 = await extractor.extract_from_text(md_text, role="table_xml", chunk_title="Page 6 Text")
        print(f"Extracted {len(res2.parameters)} parameters using Text only.")
    except Exception as e:
        print(f"Text only failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
