"""
Configuration constants for the inventory screenshot app.
"""
import pytesseract  # type: ignore

# Global hotkey (German STRG == CTRL)
# Note: If "ctrl+alt+." doesn't work, try:
#   - "ctrl+alt+period" (alternative format)
#   - "ctrl+alt+l" (letter key, more reliable)
#   - "ctrl+shift+i" (another alternative)
HOTKEY = "ctrl+alt+."

# Monitor selection for screenshot:
#   1 = primary monitor (mss default)
#   0 = all monitors combined (virtual bounding box)
#   2, 3, ... = specific monitor by mss index
MONITOR_INDEX = 3

# Optional crop rectangle (in pixels) relative to the chosen monitor's origin.
# If None, the full monitor is captured.
# The screenshot is expected to be 1360x300 pixels and will be split into 8 subimages.
# This region is hard coded based on a display resolution of 2560x1440
CROP_REGION = {"left": 835, "top": 900, "width": 1360, "height": 300}
# CROP_REGION = None

# Save each captured (cropped) screenshot and subimages to disk for debugging
SAVE_DEBUG_IMAGES = False

# Path to the CSV file that will store inventory snapshots
CSV_PATH = "G:/My Drive/Dune Awakening/inventory_log.csv"

# CSV header definition
CSV_HEADER = ["timestamp", "item_name", "available_count", "required_count"]

# Optional: path to Tesseract executable on Windows (adjust if installed elsewhere)
# Example default for 64‑bit Windows:
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# External LLM API configuration
OLLAMA_URL = "http://localhost:11434/api/generate"
# MODEL_NAME = "llama3.2-vision"
# MODEL_NAME = "qwen2.5vl:7b"
MODEL_NAME = "qwen3-vl:8b"

PROMPT = """
You receive a cropped game UI element image. The image is structured as follows:
First there is an icon on the left side. Then to the right of that are two numbers.
The first number denotes the required amount of a resource.
That is followed by a small empty space and an opening parenthesis. Inside the parentheses is
the second number, denoting the available amount.
Below those two numbers is a string that names the resource itself. The resource name can
consist of several separate words and it can wrap two lines.
The image might not contain any icon, numbers or text at all.

Return only valid JSON in this format:

{
  "item_name": "<string>",
  "required_count": <integer>,
  "available_count": <integer>
}

Numbers must be integers without thousand separators.
If the image contains no icon, numbers or text at all, set item_name to "NONE" and both counts to null.

Return ONLY the JSON object exactly as above, no explanations, no headers, no extra text.
"""

