import cv2
import numpy as np
from rapidocr import RapidOCR
import asyncio
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)
engine = RapidOCR(config_path="default_rapidocr.yaml")

@dataclass
class OCRBox:
    text: str
    confidence: float
    x: float
    y: float
    width: float
    height: float

@dataclass
class OCRResult:
    boxes: list[OCRBox]
    raw_text: str
    quality_issues: list[str] = None

    def has_field_candidate(self, min_confidence: float = 0.0) -> list[OCRBox]:
        return [b for b in self.boxes if b.confidence >= min_confidence]
    
def get_receipt_area_ratio(img) -> float:
    """
    Hitung rasio area struk vs total foto.
    Return float 0.0 - 1.0
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Blur dulu buat reduce noise
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Threshold — pisahin struk putih dari background gelap
    _, thresh = cv2.threshold(blurred, 127, 255, cv2.THRESH_BINARY)
    
    # Find contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        return 0.0
    
    # Ambil contour terbesar — harusnya struk
    largest = max(contours, key=cv2.contourArea)
    receipt_area = cv2.contourArea(largest)
    
    # Total area foto
    total_area = img.shape[0] * img.shape[1]
    
    ratio = receipt_area / total_area
    return ratio

def assess_image_quality(img) -> dict:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
    brightness = np.mean(gray)
    contrast = np.std(gray)
    receipt_ratio = get_receipt_area_ratio(img)
    
    issues = []
    if blur_score < 100:
        issues.append("blurry")
    if brightness < 80:
        issues.append("too_dark")
    if brightness > 220:
        issues.append("too_bright")
    if contrast < 30:
        issues.append("low_contrast")
    if receipt_ratio < 0.3:  # struk kurang dari 30% frame
        issues.append("receipt_too_small")
    
    return {
        "blur_score": blur_score,
        "brightness": brightness,
        "contrast": contrast,
        "receipt_ratio": receipt_ratio,
        "issues": issues,
        "is_acceptable": len(issues) == 0
    }

def check_and_fix_inversion(gray: np.ndarray) -> np.ndarray:
    """
    Thermal receipts sometimes photograph as white-on-dark.
    If mean pixel < 127, the image is inverted — fix it.
    """
    if np.mean(gray) < 127:
        logger.debug("Inverted image detected — flipping")
        return cv2.bitwise_not(gray)
    return gray

def deskew(image: np.ndarray) -> np.ndarray:
    """Straighten tilted receipt"""
    inverted = cv2.bitwise_not(image)
    coords = np.column_stack(np.where(inverted > 0))

    if len(coords) == 0:
        return image

    angle = cv2.minAreaRect(coords)[-1]

    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    if abs(angle) < 0.5:
        return image

    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)

    return cv2.warpAffine(
        image, M, (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE
    )


def crop_receipt(img):
    """
    Crop struk dari background.
    Return cropped image, atau original kalau crop gagal.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Threshold — struk putih vs background gelap
    _, thresh = cv2.threshold(blurred, 127, 255, cv2.THRESH_BINARY)
    
    # Find contours
    contours, _ = cv2.findContours(
        thresh, 
        cv2.RETR_EXTERNAL, 
        cv2.CHAIN_APPROX_SIMPLE
    )
    
    if not contours:
        logger.warning("No contours found — skipping crop")
        return img
    
    # Ambil contour terbesar
    largest = max(contours, key=cv2.contourArea)
    
    # Validasi — contour harus cukup besar (min 20% frame)
    total_area = img.shape[0] * img.shape[1]
    if cv2.contourArea(largest) < total_area * 0.2:
        logger.warning("Largest contour too small — skipping crop")
        return img  # fallback ke original
    
    # Bounding box dengan padding
    x, y, w, h = cv2.boundingRect(largest)
    pad = 20
    x = max(0, x - pad)
    y = max(0, y - pad)
    w = min(img.shape[1] - x, w + 2 * pad)
    h = min(img.shape[0] - y, h + 2 * pad)
    
    cropped = img[y:y+h, x:x+w]
    logger.info(f"Cropped receipt: {w}x{h} from {img.shape[1]}x{img.shape[0]}")

    cv2.imwrite("debug_cropped_image.jpg", cropped)
    
    return cropped

def _parse_ocr_result(result) -> list[OCRBox]:
    """
    RapidOCR 3.6.0 returns RapidOCROutput dataclass.
    Access via result.boxes, result.txts, result.scores — NOT iterable directly.
    
    result.boxes  → np.ndarray shape (N, 4, 2) — 4 corners per box
    result.txts   → Tuple[str]                 — text per box
    result.scores → Tuple[float]               — confidence per box
    """
    if result is None:
        return []

    # Guard: if no boxes detected at all
    if result.boxes is None or result.txts is None or result.scores is None:
        return []

    boxes = []
    for box, text, score in zip(result.boxes, result.txts, result.scores):
        # box shape: [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
        xs = [pt[0] for pt in box]
        ys = [pt[1] for pt in box]

        boxes.append(OCRBox(
            text=text,
            confidence=float(score),
            x=float(min(xs)),
            y=float(min(ys)),
            width=float(max(xs) - min(xs)),
            height=float(max(ys) - min(ys)),
        ))

    # Sort top→bottom, left→right
    boxes.sort(key=lambda b: (b.y, b.x))
    return boxes
    
# async def ocr_image(image_path: str) -> str:



#     try:
#         loop = asyncio.get_event_loop()

#         def process():
#             img = cv2.imread(image_path)
#             if img is None: return ""
#             gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
#             # gray = img[:, :, 1]
#             # # bright = cv2.convertScaleAbs(gray, alpha=1.4, beta=40)
#             # denoised = cv2.fastNlMeansDenoising(gray, h=15)
#             # clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
#             # enhanced = clahe.apply(denoised)
#             # _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
#             # binary = cv2.adaptiveThreshold( enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, blockSize=15, C=2)
    
#             # Debug — save intermediate results
#             cv2.imwrite("debug_enhanced.jpg", img)
    
#             deskewed = deskew(gray)
#             # binary = deskew(binary)
#             # upscaled = cv2.resize(enhanced, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)

#             result = engine(deskewed)
#             if result and hasattr(result, 'txts'):
#                 #  print("--- OCR RESULT START ---")
#                  print(result.txts)
#                 #  print("--- OCR RESULT END ---")
#                  return "\n".join(result.txts)
#             return "No text found"

#         logger.info(f"Starting OCR processing for image: {image_path}")
#         raw_text = await loop.run_in_executor(None, process)

#         return raw_text
#     except Exception as e:
#         logger.error(f"OCR failed for image {image_path}: {e}")
#         return ""

def reconstruct_lines(boxes: list[OCRBox], y_tolerance: int = 24) -> str:
    """
    Group OCRBoxes yang ada di baris yang sama (y proximity),
    sort per baris by x, join jadi lines.
    """
    if not boxes:
        return ""
    
    lines = []
    used = set()
    
    # Sort by y dulu
    sorted_boxes = sorted(boxes, key=lambda b: b.y)
    
    for i, box in enumerate(sorted_boxes):
        if i in used:
            continue
        
        # Kumpulin semua box yang y-nya dalam range tolerance
        line_boxes = [box]
        used.add(i)
        
        for j, other in enumerate(sorted_boxes):
            if j in used:
                continue
            # Cek overlap y — box dianggap satu baris kalau y center-nya deket
            box_center_y = box.y + box.height / 2
            other_center_y = other.y + other.height / 2
            
            if abs(box_center_y - other_center_y) <= y_tolerance:
                line_boxes.append(other)
                used.add(j)
        
        # Sort by x dalam satu baris
        line_boxes.sort(key=lambda b: b.x)
        line_text = " ".join(b.text for b in line_boxes)
        lines.append(line_text)
    
    return "\n".join(lines)

async def ocr_image(image_path: str) -> OCRResult:
    """
    Returns structured OCRResult with per-box confidence scores.
    Falls back to empty OCRResult on failure.
    """
    try:
        loop = asyncio.get_event_loop()

        def process() -> OCRResult:
            img = cv2.imread(image_path)
            if img is None:
                logger.warning(f"Could not read image: {image_path}")
                return OCRResult(boxes=[], raw_text="")
            

            quality = assess_image_quality(img)

            if not quality["is_acceptable"]:
                logger.warning(f"Image quality issues: {quality['issues']}")
                return OCRResult(
            boxes=[], 
            raw_text="",
            quality_issues=quality["issues"]  # pass ke caller
            )

            img_crop = crop_receipt(img)

            # ── Step 1: Grayscale ──────────────────────────────────────────
            gray = cv2.cvtColor(img_crop, cv2.COLOR_BGR2GRAY)

            # ── Step 2: Fix inverted thermal receipts ──────────────────────
            gray = check_and_fix_inversion(gray)

            gray = img_crop[:, :, 1]
    
            # 4. Denoise
            denoised = cv2.fastNlMeansDenoising(gray, h=15)
    
            # 5. CLAHE
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(denoised)

            # ── Step 3: Deskew ─────────────────────────────────────────────
            deskewed = deskew(enhanced)

            # ── Step 4: Run OCR ────────────────────────────────────────────
            result = engine(deskewed)

            # ── Step 5: Parse structured output with confidence ────────────
            boxes = _parse_ocr_result(result)
            print(boxes)

            if not boxes:
                logger.warning(f"No text detected in: {image_path}")
                return OCRResult(boxes=[], raw_text="")

            # raw_text for backward compat with your existing LLM prompt
            raw_text = reconstruct_lines(boxes, y_tolerance=24)
            print("Reconstructed lines:")
            print(raw_text)
            logger.info(
                f"OCR complete: {len(boxes)} boxes, "
                f"avg confidence: {sum(b.confidence for b in boxes)/len(boxes):.3f}"
            )

            return OCRResult(boxes=boxes, raw_text=raw_text)

        return await loop.run_in_executor(None, process)

    except Exception as e:
        logger.error(f"OCR failed for {image_path}: {e}")
        return OCRResult(boxes=[], raw_text="")