"""
Configuration constants for the inventory screenshot app.
Provides backward-compatible access to config values via config manager.
"""
import pytesseract  # type: ignore
from inventory_app.config_manager import get_config_manager

# Initialize config manager (will use defaults if no user config exists)
_config = get_config_manager()

# CSV header definition (not user-configurable)
CSV_HEADER = ["timestamp", "item_name", "available_count", "required_count"]

# Default values (used as fallback)
_DEFAULT_HOTKEY = "ctrl+alt+."
_DEFAULT_MONITOR_INDEX = 1
_DEFAULT_CROP_REGION = {"left": 835, "top": 900, "width": 1360, "height": 300}
_DEFAULT_SAVE_DEBUG_IMAGES = False
_DEFAULT_CSV_PATH = "inventory_log.csv"
_DEFAULT_TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
_DEFAULT_OLLAMA_URL = "http://localhost:11434/api/generate"
_DEFAULT_MODEL_NAME = "qwen3-vl:8b"

# Initialize Tesseract path from config
pytesseract.pytesseract.tesseract_cmd = _config.get("tesseract_cmd", _DEFAULT_TESSERACT_CMD)

# Module-level attribute access using __getattr__ (Python 3.7+)
def __getattr__(name: str):
    """Provide backward-compatible attribute access."""
    if name == "HOTKEY":
        return _config.get("hotkey", _DEFAULT_HOTKEY)
    elif name == "MONITOR_INDEX":
        return _config.get("monitor_index", _DEFAULT_MONITOR_INDEX)
    elif name == "CROP_REGION":
        return _config.get("crop_region", _DEFAULT_CROP_REGION)
    elif name == "SAVE_DEBUG_IMAGES":
        return _config.get("save_debug_images", _DEFAULT_SAVE_DEBUG_IMAGES)
    elif name == "CSV_PATH":
        return _config.get("csv_path", _DEFAULT_CSV_PATH)
    elif name == "OLLAMA_URL":
        return _config.get("ollama_url", _DEFAULT_OLLAMA_URL)
    elif name == "MODEL_NAME":
        return _config.get("model_name", _DEFAULT_MODEL_NAME)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

# Functions to update config (for UI to use)
def update_config(**kwargs) -> None:
    """Update configuration values in the config manager."""
    if "hotkey" in kwargs:
        _config.set("hotkey", kwargs["hotkey"])
    if "monitor_index" in kwargs:
        _config.set("monitor_index", kwargs["monitor_index"])
    if "crop_region" in kwargs:
        _config.set("crop_region", kwargs["crop_region"])
    if "save_debug_images" in kwargs:
        _config.set("save_debug_images", kwargs["save_debug_images"])
    if "csv_path" in kwargs:
        _config.set("csv_path", kwargs["csv_path"])
    if "tesseract_cmd" in kwargs:
        _config.set("tesseract_cmd", kwargs["tesseract_cmd"])
        pytesseract.pytesseract.tesseract_cmd = kwargs["tesseract_cmd"]
    if "ollama_url" in kwargs:
        _config.set("ollama_url", kwargs["ollama_url"])
    if "model_name" in kwargs:
        _config.set("model_name", kwargs["model_name"])

def reload_config(config_path: str | None = None) -> None:
    """Reload configuration from file."""
    from inventory_app.config_manager import reload_config as _reload
    _reload(config_path)
    # Update pytesseract path
    pytesseract.pytesseract.tesseract_cmd = _config.get("tesseract_cmd", _DEFAULT_TESSERACT_CMD)

def get_config_manager():
    """Get the config manager instance."""
    return _config

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
