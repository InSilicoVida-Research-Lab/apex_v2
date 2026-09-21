import os
import cv2
import numpy as np
from PIL import Image
from typing import Optional, List, Tuple
from ..config import logger

class TableCropper:
    """
    Isolates table regions from full-page PDF images before passing to the VLM.

    Two-pronged approach:
      1. Primary  — YOLOv8 Document Layout Detection (if confident)
      2. Fallback — OpenCV morphological line detection
    """

    def __init__(self):
        logger.info("Initializing TableCropper and YOLOv8 model...")
        try:
            from ultralytics import YOLO
            from huggingface_hub import hf_hub_download
            
            # Explicitly define model and revision
            repo_id = "foduucom/table-detection-and-extraction"
            filename = "best.pt"
            
            weights_path = hf_hub_download(
                repo_id=repo_id,
                filename=filename
            )
            self.yolo_model = YOLO(weights_path)
            self.device = os.getenv("TABLE_DETECTOR_DEVICE", "cpu")
            self.is_yolo_loaded = True
        except Exception as e:
            logger.error(f"Failed to load YOLO table detector: {e}")
            self.is_yolo_loaded = False

    def crop_yolo(self, pil_image: Image.Image) -> Optional[Tuple[Image.Image, Tuple[int, int, int, int]]]:
        if not self.is_yolo_loaded:
            return None
            
        # Run inference
        results = self.yolo_model(pil_image, device=self.device, verbose=False)
        if not results or len(results[0].boxes) == 0:
            return None
            
        w, h = pil_image.size
        page_area = w * h
        best_bbox = None
        best_conf = 0.0
        
        for box in results[0].boxes:
            conf = float(box.conf[0])
            cls_id = int(box.cls[0])
            cls_name = self.yolo_model.names[cls_id].lower()
            
            # Check confidence and class
            if conf < 0.3 or "table" not in cls_name:
                continue
                
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            box_w = x2 - x1
            box_h = y2 - y1
            area = box_w * box_h
            
            # Area checks (prevent extreme false positives)
            if area < page_area * 0.01 or area > page_area * 0.95:
                continue
                
            # Aspect ratio checks (tables shouldn't be 100x taller than wide)
            if box_w == 0 or box_h / box_w > 10.0:
                continue
                
            if conf > best_conf:
                best_conf = conf
                
                # Asymmetric padding: 5% left/right, 10% top (caption), 15% bottom (footnotes)
                pad_x = int(w * 0.05)
                pad_y_top = int(h * 0.10)
                pad_y_bottom = int(h * 0.15)
                
                # Clamp to image boundaries
                best_bbox = (
                    max(0, x1 - pad_x),
                    max(0, y1 - pad_y_top),
                    min(w, x2 + pad_x),
                    min(h, y2 + pad_y_bottom)
                )

        if best_bbox:
            logger.info(f"TableCropper: YOLO detected table at bbox {best_bbox} (conf={best_conf:.2f})")
            return (pil_image.crop(best_bbox), best_bbox)
            
        return None

    def crop_opencv(self, pil_image: Image.Image) -> Optional[Tuple[Image.Image, Tuple[int, int, int, int]]]:
        img_np = np.array(pil_image.convert("RGB"))
        img_bgr = img_np[:, :, ::-1].copy()

        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        _, img_bin = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        img_bin = 255 - img_bin

        page_width = img_bgr.shape[1]
        kernel_len = max(20, page_width // 80)

        v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, kernel_len))
        v_lines = cv2.dilate(cv2.erode(img_bin, v_kernel, iterations=3), v_kernel, iterations=3)

        h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_len, 1))
        h_lines = cv2.dilate(cv2.erode(img_bin, h_kernel, iterations=3), h_kernel, iterations=3)

        grid_mask = cv2.addWeighted(v_lines, 0.5, h_lines, 0.5, 0.0)
        grid_mask = cv2.erode(
            255 - grid_mask,
            cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2)),
            iterations=2,
        )
        _, grid_mask = cv2.threshold(grid_mask, 128, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        contours, _ = cv2.findContours(255 - grid_mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        page_area = img_bgr.shape[0] * img_bgr.shape[1]
        best_bbox: Optional[Tuple[int, int, int, int]] = None
        best_area = 0

        for c in contours:
            x, y, cw, ch = cv2.boundingRect(c)
            area = cw * ch
            if cw > 100 and ch > 100 and area > best_area and area < page_area * 0.90:
                best_area = area
                
                # Standard symmetric padding for OpenCV 25px
                padding = 25
                w, h = pil_image.size
                best_bbox = (
                    max(0, x - padding),
                    max(0, y - padding),
                    min(w, x + cw + padding),
                    min(h, y + ch + padding),
                )

        if best_bbox and best_area > page_area * 0.08:
            logger.info(f"TableCropper: OpenCV detected table at bbox {best_bbox} (area={best_area}px²)")
            return (pil_image.crop(best_bbox), best_bbox)
            
        return None

    def crop(self, pil_image: Image.Image) -> Tuple[Image.Image, Optional[Tuple[int, int, int, int]]]:
        # 1. Try YOLO layout detection
        yolo_crop = self.crop_yolo(pil_image)
        if yolo_crop is not None:
            return yolo_crop
            
        # 2. Fallback to OpenCV contour detection
        opencv_crop = self.crop_opencv(pil_image)
        if opencv_crop is not None:
            return opencv_crop
            
        # 3. Fallback to original image
        logger.warning("TableCropper: Both YOLO and OpenCV failed. Returning full original image.")
        return (pil_image, None)

    def crop_all(self, images: List[Image.Image]) -> List[Tuple[Image.Image, Optional[Tuple[int, int, int, int]]]]:
        cropped = []
        for i, img in enumerate(images):
            logger.debug(f"TableCropper: Processing page {i + 1}/{len(images)}")
            cropped.append(self.crop(img))
        return cropped
