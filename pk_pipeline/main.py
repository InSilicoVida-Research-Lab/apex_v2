from fastapi import FastAPI, HTTPException
import os
from pdf2image import convert_from_path
import pandas as pd

from schemas import ExtractionRequest
from ml_services import ColQwenRetriever, SGLangExtractor
from config import logger

app = FastAPI(title="PK Parameter Extraction API")

# Initialize models lazily
retriever = None
extractor = None

def get_retriever():
    global retriever
    if retriever is None:
        retriever = ColQwenRetriever()
    return retriever

def get_extractor():
    global extractor
    if extractor is None:
        extractor = SGLangExtractor()
    return extractor

def convert_pdf_to_images(pdf_path: str):
    logger.debug(f"Attempting to convert PDF to images: {pdf_path}")
    if not os.path.exists(pdf_path):
        logger.error(f"File not found: {pdf_path}")
        raise FileNotFoundError(f"File not found: {pdf_path}")
    
    try:
        # 200 DPI as recommended in the document
        images = convert_from_path(pdf_path, dpi=200)
        logger.info(f"Successfully converted PDF to {len(images)} images.")
        return images
    except Exception as e:
        logger.error(f"Failed to convert PDF: {str(e)}")
        raise

@app.post("/extract_pk/")
async def extract_pk_data(request: ExtractionRequest):
    logger.info(f"Received request to extract PK data from: {request.pdf_path}")
    try:
        # 1. Convert PDF to images
        logger.debug("Step 1: Rasterization")
        images = convert_pdf_to_images(request.pdf_path)
        
        # 2. Run ColQwen2.5 filter to find the exact pages
        logger.debug("Step 2: Intra-Document Search")
        
        # Build a dynamic query to allow steering without hardcoding
        search_query = "Pharmacokinetic parameters table"
        if request.target_compounds:
            search_query += f" for {', '.join(request.target_compounds)}"
            
        target_images = get_retriever().find_top_pages(
            images, 
            top_k=5, 
            query=search_query
        )
        
        # 3. Extract data using SGLang with schema enforcement
        logger.debug("Step 3: Targeted Extraction across multiple pages")
        extracted_pages = []
        for img in target_images:
            extracted_page = await get_extractor().extract_data(img)
            extracted_pages.append(extracted_page.model_dump())
        
        logger.info("Successfully completed extraction pipeline.")
        return extracted_pages

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Pipeline error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting FastAPI server on port 8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
