import cv2
import numpy as np
from PIL import Image
from typing import Optional, List, Tuple
from config import logger


class TableCropper:
    """
    Isolates table regions from full-page PDF images before passing to the VLM.

    Two-pronged approach:
      1. Primary  — MinerU bounding boxes (if available from a layout parser)
      2. Fallback — OpenCV morphological line detection for any page including scanned images
    
    Feeding the VLM a tight crop instead of a full A4 page:
      - Maximises pixel density per table cell (critical for tiny subscripts/superscripts)
      - Reduces visual token count, lowering VRAM pressure and speeding up generation
      - Eliminates noisy regions (headers, footers, reference lists) that confuse the VLM
    """

    def __init__(self, padding: int = 25):
        """
        Args:
            padding: Extra pixels added around every detected bounding box so that
                     table footnotes and border lines are never accidentally clipped.
        """
        self.padding = padding

    # ──────────────────────────────────────────────────────────────────────────
    # Primary Method: MinerU / magic-pdf bounding boxes
    # ──────────────────────────────────────────────────────────────────────────

    def crop_from_bbox(
        self,
        pil_image: Image.Image,
        bbox: Tuple[float, float, float, float],
    ) -> Image.Image:
        """
        Crop using an (x0, y0, x1, y1) bounding box from a layout parser (e.g. MinerU).
        Applies self.padding on all sides while respecting image boundaries.
        """
        x0, y0, x1, y1 = bbox
        w, h = pil_image.size
        crop_box = (
            max(0, int(x0) - self.padding),
            max(0, int(y0) - self.padding),
            min(w, int(x1) + self.padding),
            min(h, int(y1) + self.padding),
        )
        logger.debug(f"TableCropper: MinerU bbox crop → {crop_box}")
        return pil_image.crop(crop_box)

    # ──────────────────────────────────────────────────────────────────────────
    # Fallback Method: OpenCV morphological grid detection
    # ──────────────────────────────────────────────────────────────────────────

    def crop_largest_table(self, pil_image: Image.Image) -> Image.Image:
        """
        Fallback: detects the largest table grid in the page using OpenCV morphological
        operations (horizontal + vertical line detection → contour bounding box).

        Works well for:
          - Bordered tables in digital PDFs
          - Scanned pages with visible grid lines

        Falls back to returning the original page if no grid is found (e.g. borderless tables),
        which is still fine — the VLM sees the full page in that case.
        """
        img_np = np.array(pil_image.convert("RGB"))
        img_bgr = img_np[:, :, ::-1].copy()  # RGB → BGR for OpenCV

        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

        # Otsu binarisation + invert so that lines are white on black
        _, img_bin = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        img_bin = 255 - img_bin

        page_width = img_bgr.shape[1]
        # Minimum line length: 1/80th of page width (tuned for A4 at 200–300 DPI)
        kernel_len = max(20, page_width // 80)

        # ── Detect vertical lines ──────────────────────────────────────────────
        v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, kernel_len))
        v_lines = cv2.dilate(cv2.erode(img_bin, v_kernel, iterations=3), v_kernel, iterations=3)

        # ── Detect horizontal lines ────────────────────────────────────────────
        h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_len, 1))
        h_lines = cv2.dilate(cv2.erode(img_bin, h_kernel, iterations=3), h_kernel, iterations=3)

        # ── Merge into a single grid mask ─────────────────────────────────────
        grid_mask = cv2.addWeighted(v_lines, 0.5, h_lines, 0.5, 0.0)
        # Invert and clean up small noise
        grid_mask = cv2.erode(
            255 - grid_mask,
            cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2)),
            iterations=2,
        )
        _, grid_mask = cv2.threshold(grid_mask, 128, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # ── Find contours and pick the largest plausible table region ─────────
        contours, _ = cv2.findContours(255 - grid_mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        page_area = img_bgr.shape[0] * img_bgr.shape[1]
        best_bbox: Optional[Tuple[int, int, int, int]] = None
        best_area = 0

        for c in contours:
            x, y, cw, ch = cv2.boundingRect(c)
            area = cw * ch
            # Minimum 100 × 100 px; ignore whole-page contours (> 90 % of area)
            if cw > 100 and ch > 100 and area > best_area and area < page_area * 0.90:
                best_area = area
                best_bbox = (x, y, x + cw, y + ch)

        # Only crop if the best bounding box is reasonably large (at least 3% of the page).
        # This prevents the cropper from isolating a tiny noise artifact or a single cell
        # when a borderless table is present elsewhere on the page.
        if best_bbox and best_area > page_area * 0.03:
            logger.info(f"TableCropper: OpenCV detected table at bbox {best_bbox} (area={best_area}px²)")
            return self.crop_from_bbox(pil_image, best_bbox)
        else:
            logger.warning(
                "TableCropper: No clear grid found (or grid was too small). "
                "Returning full page to VLM."
            )
            return pil_image

    # ──────────────────────────────────────────────────────────────────────────
    # Convenience: try MinerU bbox first, then OpenCV fallback
    # ──────────────────────────────────────────────────────────────────────────

    def crop(
        self,
        pil_image: Image.Image,
        mineru_bbox: Optional[Tuple[float, float, float, float]] = None,
    ) -> Image.Image:
        """
        Main entry point.
        - If `mineru_bbox` is supplied → use the precise layout-parser crop.
        - Otherwise → run the OpenCV heuristic fallback automatically.
        """
        if mineru_bbox is not None:
            return self.crop_from_bbox(pil_image, mineru_bbox)
        return self.crop_largest_table(pil_image)

    def crop_all(
        self,
        images: List[Image.Image],
        mineru_bboxes: Optional[List[Optional[Tuple]]] = None,
    ) -> List[Image.Image]:
        """
        Batch-crop a list of pages. `mineru_bboxes` can be a parallel list of
        bounding boxes (or None entries for pages where MinerU found nothing).
        """
        if mineru_bboxes is None:
            mineru_bboxes = [None] * len(images)

        cropped = []
        for i, (img, bbox) in enumerate(zip(images, mineru_bboxes)):
            logger.debug(f"TableCropper: Processing page {i + 1}/{len(images)}")
            cropped.append(self.crop(img, bbox))
        return cropped
