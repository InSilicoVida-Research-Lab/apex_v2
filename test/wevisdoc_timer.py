import time
import argparse
import pymupdf
from PIL import Image
import io
import sys
import os

# Ensure the root directory is on PYTHONPATH so pk_pipeline modules can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pk_pipeline.ml_services import WeVisDocParser

class WeVisDocTimer:
    def __init__(self):
        print("Initializing WeVisDocParser...")
        start_init = time.time()
        self.parser = WeVisDocParser()
        print(f"Initialization took {time.time() - start_init:.2f} seconds.")

    def process_pdf(self, pdf_path: str):
        if not os.path.exists(pdf_path):
            print(f"Error: PDF not found at {pdf_path}")
            return

        print(f"\nProcessing: {pdf_path}")
        
        doc_start_time = time.time()
        
        doc = pymupdf.open(pdf_path)
        total_pages = len(doc)
        print(f"Total pages: {total_pages}\n")

        full_markdown = []
        
        for i, page in enumerate(doc):
            page_num = i + 1
            print(f"--- Converting Page {page_num}/{total_pages} ---")
            page_start = time.time()

            # Render page to image at 200 DPI (matching main.py)
            pix = page.get_pixmap(matrix=pymupdf.Matrix(200/72, 200/72))
            img = Image.open(io.BytesIO(pix.tobytes())).convert("RGB")
            
            # Run WeVisDoc-4B on the full page image
            try:
                md_text = self.parser.parse_image(img)
                full_markdown.append(md_text)
                
                page_time = time.time() - page_start
                print(f"Page {page_num} finished in {page_time:.2f} seconds. Extracted {len(md_text)} chars.")
            except Exception as e:
                print(f"Error processing page {page_num}: {e}")

        total_time = time.time() - doc_start_time
        print(f"\n{'='*50}")
        print(f"Total Time for {total_pages} pages: {total_time:.2f} seconds")
        if total_pages > 0:
            print(f"Average Time per page: {total_time / total_pages:.2f} seconds")
        print(f"{'='*50}")
        
        return "\n\n---\n\n".join(full_markdown)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test WeVisDoc-4B execution time on a full PDF")
    parser.add_argument("pdf_path", help="Path to the PDF file to test")
    args = parser.parse_args()

    timer = WeVisDocTimer()
    timer.process_pdf(args.pdf_path)
