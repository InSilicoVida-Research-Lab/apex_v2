from transformers import AutoImageProcessor, TableTransformerForObjectDetection
import torch
from PIL import Image
import pymupdf as fitz
import cv2

# Extract image
pdf_path = "pk_pipeline/test_data/Verner et al. 2016 2 compartment (PFOA, PFOS, PFHxS).pdf"
doc = fitz.open(pdf_path)
page = doc[3] # Page 6
pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
img_path = "test_page6_tatr.jpg"
pix.save(img_path)

image = Image.open(img_path).convert("RGB")

print("Loading Table Transformer model...")
processor = AutoImageProcessor.from_pretrained("microsoft/table-transformer-detection")
model = TableTransformerForObjectDetection.from_pretrained("microsoft/table-transformer-detection")

print("Running inference...")
inputs = processor(images=image, return_tensors="pt")
outputs = model(**inputs)

# Convert outputs (bounding boxes and class logits) to Pascal VOC format (xmin, ymin, xmax, ymax)
target_sizes = torch.tensor([image.size[::-1]])
results = processor.post_process_object_detection(outputs, threshold=0.7, target_sizes=target_sizes)[0]

img_cv2 = cv2.imread(img_path)
tables_found = 0
for score, label, box in zip(results["scores"], results["labels"], results["boxes"]):
    if label.item() == 0:  # Class 0 is 'table' in table-transformer
        tables_found += 1
        box = [int(i) for i in box.tolist()]
        x_min, y_min, x_max, y_max = box
        print(f"Found table with score {score.item():.3f} at {box}")
        cv2.rectangle(img_cv2, (x_min, y_min), (x_max, y_max), (0, 0, 255), 3)

cv2.imwrite("test_page6_tatr_bboxes.jpg", img_cv2)
print(f"Detected {tables_found} tables. Saved image to test_page6_tatr_bboxes.jpg")
