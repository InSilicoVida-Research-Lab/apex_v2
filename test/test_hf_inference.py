from transformers import AutoModelForObjectDetection, AutoImageProcessor
import torch
import cv2
import pymupdf as fitz
from PIL import Image
import numpy as np

pdf_path = "pk_pipeline/test_data/s12249-023-02680-y.pdf"
doc = fitz.open(pdf_path)
page = doc[5] # Page 6
pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
img_path = "test_page6_transformers.jpg"
pix.save(img_path)

model_id = "PaddlePaddle/PP-OCRv6_medium_det_safetensors"
processor = AutoImageProcessor.from_pretrained(model_id)
model = AutoModelForObjectDetection.from_pretrained(model_id)

image = Image.open(img_path).convert("RGB")
inputs = processor(images=image, return_tensors="pt")

with torch.no_grad():
    outputs = model(**inputs)

target_sizes = torch.tensor([image.size[::-1]])
results = processor.post_process_object_detection(outputs, threshold=0.5, target_sizes=target_sizes)[0]

img_cv2 = cv2.imread(img_path)
print(f"Detected {len(results['scores'])} objects.")
for score, label, box in zip(results["scores"], results["labels"], results["boxes"]):
    box = [round(i, 2) for i in box.tolist()]
    x_min, y_min, x_max, y_max = [int(i) for i in box]
    cv2.rectangle(img_cv2, (x_min, y_min), (x_max, y_max), (0, 255, 0), 2)

cv2.imwrite("test_page6_transformers_bboxes.jpg", img_cv2)
print("Saved image with bounding boxes.")
