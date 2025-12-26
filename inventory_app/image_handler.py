"""
Image handling module: screenshot capture, conversion, splitting, OCR pre-screening, and debug saving.
"""
import sys
from datetime import datetime
from typing import List

import mss
import pytesseract  # type: ignore
from PIL import Image

from inventory_app.config import CROP_REGION, MONITOR_INDEX, SAVE_DEBUG_IMAGES


def log(message: str, verbose: bool = False) -> None:
    """Print a log message only when verbose mode is enabled."""
    if verbose:
        print(message)


def take_screenshot(verbose: bool = False) -> Image.Image:
    """Capture a screenshot of the chosen monitor (optionally cropped) as a PIL Image."""
    with mss.mss() as sct:
        monitors = sct.monitors
        idx = MONITOR_INDEX
        if idx < 0 or idx >= len(monitors):
            log(f"Invalid MONITOR_INDEX={idx}, defaulting to primary (1).", verbose)
            idx = 1
        monitor = monitors[idx]

        region = monitor
        if CROP_REGION:
            try:
                region = {
                    "left": monitor["left"] + int(CROP_REGION["left"]),
                    "top": monitor["top"] + int(CROP_REGION["top"]),
                    "width": int(CROP_REGION["width"]),
                    "height": int(CROP_REGION["height"]),
                }
            except (KeyError, TypeError, ValueError) as exc:
                log(f"Bad CROP_REGION config ({exc}); falling back to full monitor.", verbose)

        sct_img = sct.grab(region)
        img = Image.frombytes("RGB", sct_img.size, sct_img.rgb)
    return img


def save_debug_image(img: Image.Image, prefix: str = "capture", verbose: bool = False) -> str:
    """Save the captured image with a timestamped filename for debugging. Returns filename."""
    if not SAVE_DEBUG_IMAGES:
        return ""
    
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"{prefix}_{ts}.png"
    try:
        img.save(filename)
        log(f"Saved debug image: {filename}", verbose)
        return filename
    except OSError as exc:
        print(f"Could not save debug image ({exc})", file=sys.stderr)
        return ""


def split_image_into_subimages(img: Image.Image) -> List[Image.Image]:
    """
    Split the input image into 8 subimages in a 4x2 grid (4 columns, 2 rows).
    Returns a list of PIL Image objects, ordered left-to-right, top-to-bottom.
    """
    width, height = img.size
    cols = 4
    rows = 2
    subimage_width = width // cols
    subimage_height = height // rows
    
    subimages = []
    for row in range(rows):
        for col in range(cols):
            left = col * subimage_width
            top = row * subimage_height
            right = left + subimage_width
            bottom = top + subimage_height
            subimg = img.crop((left, top, right, bottom))
            subimages.append(subimg)
    
    return subimages


def image_has_text(img: Image.Image, verbose: bool = False) -> bool:
    """
    Use Tesseract OCR to detect if a subimage contains any text.
    Returns True if there is at least one alphanumeric character.
    """
    try:
        gray = img.convert("L")
        text = pytesseract.image_to_string(gray, lang="eng")
        text_stripped = text.strip()
        log(f"OCR text (len={len(text_stripped)}): {repr(text_stripped[:80])}", verbose)
        return any(ch.isalnum() for ch in text_stripped)
    except Exception as exc:
        print(f"Error during OCR pre-screen: {exc}", file=sys.stderr)
        return True  # fall back to keeping the image so we don't lose data


def pre_screen_subimages(subimages: List[Image.Image], verbose: bool = False) -> List[Image.Image]:
    """
    Pre-screen subimages with Tesseract OCR; keep only those with detected text.
    Returns a filtered list of images that contain text.
    """
    screened_subimages = []
    for idx, subimg in enumerate(subimages, 1):
        if image_has_text(subimg, verbose):
            log(f"Subimage {idx} passed OCR pre-screen.", verbose)
            screened_subimages.append(subimg)
        else:
            log(f"Subimage {idx} has no OCR text; skipping.", verbose)
    return screened_subimages

