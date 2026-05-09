import easyocr
import cv2
import re

# SAFE OCR INIT (CPU ONLY)
reader = easyocr.Reader(['en'], gpu=False)


def extract_text(image_path):

    img = cv2.imread(image_path)

    if img is None:
        return ""

    # improve image for OCR
    img = cv2.resize(img, None, fx=2, fy=2)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    result = reader.readtext(gray, detail=0)

    text = " ".join(result)

    # CLEAN OCR NOISE
    text = text.replace("0", "o")
    text = text.replace("1", "l")

    return text.lower()


def extract_expiry(text):

    if not text:
        return None

    # supports formats like 2026-05-07
    match = re.search(r'(\d{4})-(\d{2})-(\d{2})', text)

    if match:
        return match.group()

    return None