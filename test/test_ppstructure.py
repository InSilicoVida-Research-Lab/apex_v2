import cv2
import pymupdf as fitz
from paddleocr import PPStructureV3

pdf_path = "pk_pipeline/test_data/s12249-023-02680-y.pdf"
doc = fitz.open(pdf_path)
page = doc[6] # Page 6
pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
img_path = "test_page6.jpg"
pix.save(img_path)

print("Running PPStructure...")
table_engine = PPStructureV3()
img = cv2.imread(img_path)
result = table_engine(img)

print(f"Detected {len(result)} elements.")
for res in result:
    print(f"Type: {res['type']}, bbox: {res['bbox']}")
    if res['type'] == 'table':
        print("Found table!")
        x_min, y_min, x_max, y_max = res['bbox']
        crop_img = img[y_min:y_max, x_min:x_max]
        cv2.imwrite("test_page6_table_crop.jpg", crop_img)
        print("Saved cropped table to test_page6_table_crop.jpg")
