from transformers import AutoModelForObjectDetection, AutoImageProcessor
import torch

model_id = "PaddlePaddle/PP-OCRv6_medium_det_safetensors"
try:
    processor = AutoImageProcessor.from_pretrained(model_id)
    model = AutoModelForObjectDetection.from_pretrained(model_id)
    print("Successfully loaded via transformers!")
except Exception as e:
    print(f"Error: {e}")
