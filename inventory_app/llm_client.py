"""
LLM API client module: handles communication with the vision LLM API (Ollama).
"""
import base64
import json
import sys
import time
from io import BytesIO
from typing import Any, Dict, List

import requests  # type: ignore
from requests import exceptions as req_exc
from PIL import Image

from inventory_app.config import (
    MODEL_NAME,
    OLLAMA_API_KEY,
    OLLAMA_RETRIES,
    OLLAMA_TIMEOUT_SECONDS,
    OLLAMA_URL,
    PROMPT,
)


def log(message: str, verbose: bool = False) -> None:
    """Print a log message only when verbose mode is enabled."""
    if verbose:
        print(message)


def pil_to_base64(img: Image.Image) -> str:
    """Convert a PIL Image to base64-encoded PNG string."""
    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def _post_generate(
    url: str,
    payload: Dict[str, Any],
    headers: Dict[str, str] | None,
    connect_timeout: float,
    read_timeout: float,
    max_attempts: int,
    verbose: bool,
) -> requests.Response:
    """POST to Ollama with retries on transient network failures."""
    last_err: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            resp = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=(connect_timeout, read_timeout),
            )
            return resp
        except (req_exc.Timeout, req_exc.ConnectionError) as e:
            last_err = e
            if attempt < max_attempts:
                delay = min(2 ** (attempt - 1), 30)
                log(
                    f"  → attempt {attempt}/{max_attempts} failed ({e!s}), retrying in {delay}s...",
                    verbose,
                )
                time.sleep(delay)
    assert last_err is not None
    raise last_err


def call_llm_api(images: List[Image.Image], verbose: bool = False) -> List[Dict[str, Any]]:
    """
    Send each image individually to the Ollama API and collect the responses.
    Returns a list of JSON objects, one for each image.
    """
    results = []

    headers: Dict[str, str] | None = None
    if OLLAMA_API_KEY:
        headers = {"Authorization": f"Bearer {OLLAMA_API_KEY}"}

    read_timeout = float(OLLAMA_TIMEOUT_SECONDS)
    connect_timeout = min(30.0, max(10.0, read_timeout / 6.0))
    max_attempts = max(1, 1 + OLLAMA_RETRIES)

    for i, img in enumerate(images, 1):
        log(f"Processing image {i}/{len(images)}...", verbose)

        b64_image = pil_to_base64(img)

        payload = {
            "model": MODEL_NAME,
            "prompt": PROMPT,
            "stream": False,
            "images": [b64_image],
        }

        resp = None
        try:
            resp = _post_generate(
                OLLAMA_URL,
                payload,
                headers,
                connect_timeout,
                read_timeout,
                max_attempts,
                verbose,
            )
            resp.raise_for_status()
            text = resp.json()["response"]

            item_data = json.loads(text)
            results.append(item_data)
            log("  → OK", verbose)

        except Exception as e:
            print(f"✗ Error calling LLM for image {i}: {e}", file=sys.stderr)
            try:
                if resp is not None:
                    log(f"STATUS: {resp.status_code}", verbose)
                    log(f"RAW: {resp.json()}", verbose)
            except Exception:
                pass
            results.append({
                "item_name": "ERROR",
                "required_count": None,
                "available_count": None,
            })

    return results
