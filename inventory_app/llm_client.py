"""
LLM API client module: handles communication with the vision LLM API (Ollama).
"""
import base64
import json
import sys
from io import BytesIO
from typing import Any, Dict, List

import requests  # type: ignore
from PIL import Image

from inventory_app.config import MODEL_NAME, OLLAMA_URL, PROMPT


def log(message: str, verbose: bool = False) -> None:
    """Print a log message only when verbose mode is enabled."""
    if verbose:
        print(message)


def pil_to_base64(img: Image.Image) -> str:
    """Convert a PIL Image to base64-encoded PNG string."""
    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def call_llm_api(images: List[Image.Image], verbose: bool = False) -> List[Dict[str, Any]]:
    """
    Send each image individually to the Ollama API and collect the responses.
    Returns a list of JSON objects, one for each image.
    """
    results = []
    
    for i, img in enumerate(images, 1):
        log(f"Processing image {i}/{len(images)}...", verbose)
        
        # Encode single image as base64
        b64_image = pil_to_base64(img)
        
        payload = {
            "model": MODEL_NAME,
            "prompt": PROMPT,
            "stream": False,
            "images": [b64_image],  # Single image per request
        }
        
        try:
            resp = requests.post(OLLAMA_URL, json=payload, timeout=90)
            
            resp.raise_for_status()
            text = resp.json()["response"]
            
            # Parse JSON response
            item_data = json.loads(text)
            results.append(item_data)
            log("  → OK", verbose)
            
        except Exception as e:
            # Always show minimal error for visibility
            print(f"✗ Error calling LLM for image {i}: {e}", file=sys.stderr)
            # Extra details only in verbose mode
            try:
                log(f"STATUS: {resp.status_code}", verbose)
                log(f"RAW: {resp.json()}", verbose)
            except Exception:
                pass
            # Add error fallback
            results.append({
                "item_name": "ERROR",
                "required_count": None,
                "available_count": None
            })
    
    return results

