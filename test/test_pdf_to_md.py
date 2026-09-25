import pymupdf4llm
import sys
import os

def convert_pdf_to_md(pdf_path):
    print(f"Converting {pdf_path} to Markdown using pymupdf4llm...")
    
    try:
        # Extract markdown page by page, WITH images enabled
        md_chunks = pymupdf4llm.to_markdown(pdf_path, page_chunks=True, write_images=True, image_path="output/md_pages/images")
        
        # Create output directory
        out_dir = "output/md_pages"
        os.makedirs(out_dir, exist_ok=True)
        os.makedirs(os.path.join(out_dir, "images"), exist_ok=True)
        
        stem = os.path.splitext(os.path.basename(pdf_path))[0]
        
        pages_with_data = []
        
        # Save each page to a separate markdown file
        for i, chunk in enumerate(md_chunks):
            text = chunk.get("text", "")
            out_path = os.path.join(out_dir, f"{stem}_page_{i+1}.md")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(text)
                
            # Check for tables or images
            has_table = "|---" in text
            has_image = "![" in text or (chunk.get("images") and len(chunk["images"]) > 0)
            
            if has_table or has_image:
                pages_with_data.append((i+1, text, has_table, has_image))
                
        print(f"Successfully saved {len(md_chunks)} markdown pages to '{out_dir}/' directory.")
        
        # Print out pages that contain tables or diagrams
        print("\n" + "="*80)
        print("PAGES WITH TABLES OR DIAGRAMS:")
        print("="*80)
        for page_num, text, has_tbl, has_img in pages_with_data:
            content_type = []
            if has_tbl: content_type.append("TABLE")
            if has_img: content_type.append("DIAGRAM/IMAGE")
            
            print(f"\n\n--- PAGE {page_num} (Contains: {' & '.join(content_type)}) ---")
            print(text.strip())
            print("-" * 40)
        
    except Exception as e:
        print(f"Error during conversion: {e}")

if __name__ == "__main__":
    # Default to the PDF that missed the compartment diagram
    pdf_file = sys.argv[1] if len(sys.argv) > 1 else "pk_pipeline/test_data/s12249-023-02680-y.pdf"
    if not os.path.exists(pdf_file):
        print(f"File not found: {pdf_file}")
    else:
        convert_pdf_to_md(pdf_file)
