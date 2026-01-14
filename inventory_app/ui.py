"""
UI module for displaying and configuring application settings.
"""
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Any, Dict

import inventory_app.config as config


class ConfigUI:
    """Simple UI window to display and configure application settings."""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Inventory Screenshot App")
        self.root.geometry("600x550")
        self.app_running = False
        
        # Create main frame with padding
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights for resizing
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="Configuration", font=("Arial", 14, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # Get configuration values
        config_values = self._get_config_values()
        
        # Display configuration (read-only for step 1)
        row = 1
        for key, value in config_values.items():
            self._add_config_row(main_frame, key, value, row)
            row += 1
        
        # Status label
        self.status_label = ttk.Label(main_frame, text="App Status: Not Running", 
                                      font=("Arial", 9, "italic"), foreground="gray")
        self.status_label.grid(row=row, column=0, columnspan=2, pady=(20, 10))
        row += 1
        
        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=row, column=0, columnspan=2, pady=(10, 0))
        
        # Start App button
        self.start_button = ttk.Button(button_frame, text="Start App", 
                                       command=self._start_app, width=15)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        # Close button
        close_button = ttk.Button(button_frame, text="Close", 
                                  command=self.root.destroy, width=15)
        close_button.pack(side=tk.LEFT, padx=5)
    
    def _start_app(self) -> None:
        """Start the main application in a background thread."""
        if self.app_running:
            messagebox.showwarning("Already Running", "The app is already running!")
            return
        
        try:
            # Import start_app function directly to avoid circular imports
            from main import start_app
            
            # Start app in background thread
            self.app_running = True
            self.start_button.config(state=tk.DISABLED, text="Starting...")
            self.status_label.config(text="App Status: Starting...", foreground="orange")
            
            def run_app():
                try:
                    start_app(verbose=False)
                except Exception as e:
                    # Show error in UI
                    self.root.after(0, lambda: self._show_error(str(e)))
                finally:
                    self.root.after(0, self._app_stopped)
            
            thread = threading.Thread(target=run_app, daemon=True)
            thread.start()
            
            self.status_label.config(text="App Status: Running (check console for output)", 
                                    foreground="green")
            self.start_button.config(text="Running...", state=tk.DISABLED)
            
            messagebox.showinfo("App Started", 
                               f"App is now running in the background.\n\n"
                               f"Hotkey: {config.HOTKEY}\n"
                               f"Check the console window for output.\n\n"
                               f"You can close this window - the app will continue running.")
            
        except Exception as e:
            self._show_error(f"Failed to start app: {e}")
            self._app_stopped()
    
    def _app_stopped(self) -> None:
        """Called when the app stops."""
        self.app_running = False
        self.start_button.config(state=tk.NORMAL, text="Start App")
        self.status_label.config(text="App Status: Not Running", foreground="gray")
    
    def _show_error(self, error_msg: str) -> None:
        """Show an error message."""
        messagebox.showerror("Error", error_msg)
        self._app_stopped()
    
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
