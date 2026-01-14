"""
UI module for displaying and configuring application settings.
"""
import tkinter as tk
from tkinter import ttk
from typing import Any, Dict

import inventory_app.config as config


class ConfigUI:
    """Simple UI window to display and configure application settings."""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Inventory Screenshot App - Configuration")
        self.root.geometry("600x500")
        
        # Create main frame with padding
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights for resizing
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="Current Configuration", font=("Arial", 14, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # Get configuration values
        config_values = self._get_config_values()
        
        # Display configuration (read-only for step 1)
        row = 1
        for key, value in config_values.items():
            self._add_config_row(main_frame, key, value, row)
            row += 1
        
        # Close button
        close_button = ttk.Button(main_frame, text="Close", command=self.root.destroy)
        close_button.grid(row=row, column=0, columnspan=2, pady=(20, 0))
    
    def _get_config_values(self) -> Dict[str, Any]:
        """Extract configuration values from config module (excluding PROMPT)."""
        values = {}
        
        # Hotkey
        values["Hotkey"] = config.HOTKEY
        
        # Monitor Index
        monitor_desc = {
            0: "All monitors (virtual desktop)",
            1: "Primary monitor",
        }
        if config.MONITOR_INDEX in monitor_desc:
            values["Monitor Index"] = f"{config.MONITOR_INDEX} ({monitor_desc[config.MONITOR_INDEX]})"
        else:
            values["Monitor Index"] = f"{config.MONITOR_INDEX} (monitor {config.MONITOR_INDEX})"
        
        # Crop Region
        if config.CROP_REGION:
            crop_str = f"left={config.CROP_REGION['left']}, top={config.CROP_REGION['top']}, "
            crop_str += f"width={config.CROP_REGION['width']}, height={config.CROP_REGION['height']}"
            values["Crop Region"] = crop_str
        else:
            values["Crop Region"] = "None (full monitor)"
        
        # Save Debug Images
        values["Save Debug Images"] = "Yes" if config.SAVE_DEBUG_IMAGES else "No"
        
        # CSV Path
        values["CSV File Path"] = config.CSV_PATH
        
        # Tesseract Path
        values["Tesseract Executable"] = config.pytesseract.pytesseract.tesseract_cmd
        
        # Ollama URL
        values["Ollama API URL"] = config.OLLAMA_URL
        
        # Model Name
        values["LLM Model Name"] = config.MODEL_NAME
        
        return values
    
    def _add_config_row(self, parent: ttk.Frame, label: str, value: Any, row: int) -> None:
        """Add a configuration row to the UI."""
        # Label
        label_widget = ttk.Label(parent, text=f"{label}:", font=("Arial", 9, "bold"))
        label_widget.grid(row=row, column=0, sticky=tk.W, pady=5, padx=(0, 10))
        
        # Value (read-only text widget for multi-line or long values)
        if isinstance(value, str) and (len(value) > 60 or '\n' in value):
            # Use Text widget for long strings
            value_frame = ttk.Frame(parent)
            value_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
            value_frame.columnconfigure(0, weight=1)
            
            text_widget = tk.Text(value_frame, height=2 if '\n' in value else 1, wrap=tk.WORD, 
                                 state=tk.DISABLED, bg=parent.cget("background"), 
                                 relief=tk.FLAT, font=("Arial", 9))
            text_widget.grid(row=0, column=0, sticky=(tk.W, tk.E))
            text_widget.config(state=tk.NORMAL)
            text_widget.insert("1.0", str(value))
            text_widget.config(state=tk.DISABLED)
        else:
            # Use Label for short values
            value_label = ttk.Label(parent, text=str(value), font=("Arial", 9))
            value_label.grid(row=row, column=1, sticky=tk.W, pady=5)


def show_config_ui() -> None:
    """Create and display the configuration UI window."""
    root = tk.Tk()
    app = ConfigUI(root)
    root.mainloop()


if __name__ == "__main__":
    # Allow running the UI standalone for testing
    show_config_ui()
