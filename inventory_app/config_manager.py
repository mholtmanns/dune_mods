"""
Configuration manager for loading and saving user-specific configuration.
Supports JSON and YAML formats, with fallback to Python config.py defaults.
"""
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import yaml  # type: ignore
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

# File to store the last used config file path
LAST_CONFIG_PATH_FILE = ".last_config_path"

# Default values (used when no user config file exists)
# These match the defaults in config.py but are defined here to avoid circular imports
_DEFAULT_HOTKEY = "ctrl+alt+."
_DEFAULT_MONITOR_INDEX = 1
_DEFAULT_CROP_REGION = {"left": 835, "top": 900, "width": 1360, "height": 300}
_DEFAULT_SAVE_DEBUG_IMAGES = False
_DEFAULT_CSV_PATH = "inventory_log.csv"
_DEFAULT_TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
_DEFAULT_OLLAMA_URL = "http://localhost:12000/api/generate"
_DEFAULT_MODEL_NAME = "qwen3-vl:8b"
_DEFAULT_OLLAMA_TIMEOUT_SECONDS = 180
_DEFAULT_OLLAMA_RETRIES = 2


def get_last_config_path() -> Optional[str]:
    """Read the last used config file path from .last_config_path file."""
    try:
        if os.path.exists(LAST_CONFIG_PATH_FILE):
            with open(LAST_CONFIG_PATH_FILE, 'r', encoding='utf-8') as f:
                path = f.read().strip()
                if path and os.path.exists(path):
                    return path
    except Exception as e:
        print(f"Warning: Could not read last config path: {e}", file=sys.stderr)
    return None


def save_last_config_path(config_path: str) -> None:
    """Save the config file path to .last_config_path file."""
    try:
        with open(LAST_CONFIG_PATH_FILE, 'w', encoding='utf-8') as f:
            f.write(config_path)
    except Exception as e:
        print(f"Warning: Could not save last config path: {e}", file=sys.stderr)


class ConfigManager:
    """Manages user-specific configuration file (JSON or YAML)."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize config manager.
        
        Args:
            config_path: Path to user config file. If None, checks for last used path,
                        then falls back to default location.
        """
        if config_path:
            self.config_path = Path(config_path)
        else:
            # Check for last used config path
            last_path = get_last_config_path()
            if last_path:
                self.config_path = Path(last_path)
            else:
                # Default: config.json in the project directory
                self.config_path = Path("config.json")
        
        self.config_data: Dict[str, Any] = {}
        self._load_config()
        
        # Save the path we're using (if it's a valid file)
        if self.config_path.exists():
            save_last_config_path(str(self.config_path))
    
    def _load_config(self) -> None:
        """Load configuration from file, or use defaults if file doesn't exist."""
        if self.config_path.exists():
            try:
                if self.config_path.suffix.lower() == '.yaml' or self.config_path.suffix.lower() == '.yml':
                    if not YAML_AVAILABLE:
                        print(f"Warning: YAML not available, install pyyaml to use {self.config_path}", file=sys.stderr)
                        self._load_defaults()
                        return
                    with open(self.config_path, 'r', encoding='utf-8') as f:
                        self.config_data = yaml.safe_load(f) or {}
                else:
                    # Default to JSON
                    with open(self.config_path, 'r', encoding='utf-8') as f:
                        self.config_data = json.load(f)
            except Exception as e:
                print(f"Error loading config file {self.config_path}: {e}", file=sys.stderr)
                print("Using default configuration.", file=sys.stderr)
                self._load_defaults()
        else:
            # File doesn't exist, use defaults
            self._load_defaults()
    
    def _load_defaults(self) -> None:
        """Load default values (defined here to avoid circular dependency with config.py)."""
        self.config_data = {
            "hotkey": _DEFAULT_HOTKEY,
            "monitor_index": _DEFAULT_MONITOR_INDEX,
            "crop_region": _DEFAULT_CROP_REGION,
            "save_debug_images": _DEFAULT_SAVE_DEBUG_IMAGES,
            "csv_path": _DEFAULT_CSV_PATH,
            "tesseract_cmd": _DEFAULT_TESSERACT_CMD,
            "ollama_url": _DEFAULT_OLLAMA_URL,
            "model_name": _DEFAULT_MODEL_NAME,
            "ollama_timeout_seconds": _DEFAULT_OLLAMA_TIMEOUT_SECONDS,
            "ollama_retries": _DEFAULT_OLLAMA_RETRIES,
        }
    
    def save_config(self) -> None:
        """Save current configuration to file."""
        try:
            # Ensure directory exists
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            if self.config_path.suffix.lower() == '.yaml' or self.config_path.suffix.lower() == '.yml':
                if not YAML_AVAILABLE:
                    raise ValueError("YAML support not available. Install pyyaml: pip install pyyaml")
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    yaml.dump(self.config_data, f, default_flow_style=False, sort_keys=False)
            else:
                # Default to JSON
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    json.dump(self.config_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise IOError(f"Failed to save config to {self.config_path}: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self.config_data.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set a configuration value."""
        self.config_data[key] = value
    
    def get_config_path(self) -> str:
        """Get the current config file path."""
        return str(self.config_path)
    
    def set_config_path(self, path: str) -> None:
        """Change the config file path and reload."""
        self.config_path = Path(path)
        self._load_config()
        # Save the new path as the last used
        save_last_config_path(str(self.config_path))


# Global config manager instance (initialized on first import)
_config_manager: Optional[ConfigManager] = None


def get_config_manager(config_path: Optional[str] = None) -> ConfigManager:
    """Get or create the global config manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager(config_path)
    elif config_path and str(_config_manager.config_path) != config_path:
        # Path changed, recreate manager
        _config_manager = ConfigManager(config_path)
    return _config_manager


def reload_config(config_path: Optional[str] = None) -> None:
    """Reload configuration from file."""
    global _config_manager
    if config_path:
        _config_manager = ConfigManager(config_path)
    elif _config_manager:
        _config_manager._load_config()
