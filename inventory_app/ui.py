"""
UI module for displaying and configuring application settings.
"""
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Any, Dict, List, Tuple

import mss
import inventory_app.config as config


class MonitorOverlay:
    """Fullscreen overlay window to show on a specific monitor."""
    
    def __init__(self, root: tk.Tk, monitor_index: int, text: str = "SELECTED", duration: float = 3.0):
        self.root = root
        self.monitor_index = monitor_index
        self.text = text
        self.duration = duration
        self.window = None
    
    def show(self) -> None:
        """Show the overlay on the specified monitor."""
        try:
            with mss.mss() as sct:
                monitors = sct.monitors
                if self.monitor_index < 0 or self.monitor_index >= len(monitors):
                    return
                
                monitor = monitors[self.monitor_index]
                
                # Create Toplevel window (must be created from main thread)
                self.window = tk.Toplevel(self.root)
                self.window.overrideredirect(True)  # Remove window decorations
                self.window.attributes('-topmost', True)  # Always on top
                self.window.attributes('-alpha', 0.7)  # Semi-transparent
                self.window.configure(bg='black')
                
                # Position window on the monitor
                self.window.geometry(f"{monitor['width']}x{monitor['height']}+{monitor['left']}+{monitor['top']}")
                
                # Create label with large text
                label = tk.Label(
                    self.window,
                    text=self.text,
                    font=("Arial", 96, "bold"),
                    fg="yellow",
                    bg="black",
                    justify=tk.CENTER
                )
                label.pack(expand=True, fill=tk.BOTH)
                
                # Auto-close after duration
                self.window.after(int(self.duration * 1000), self.window.destroy)
                
                # Update to ensure window is displayed
                self.window.update()
        except Exception as e:
            print(f"Error showing overlay: {e}", file=sys.stderr)


def enumerate_monitors() -> List[Tuple[int, Dict[str, int]]]:
    """Enumerate all available monitors and return list of (index, monitor_dict)."""
    monitors = []
    with mss.mss() as sct:
        for idx, monitor in enumerate(sct.monitors):
            monitors.append((idx, monitor))
    return monitors


class ConfigUI:
    """UI window to display and configure application settings."""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Inventory Screenshot App")
        self.root.geometry("700x700")
        self.app_running = False
        self.config_widgets: Dict[str, Any] = {}
        self.selected_monitor_index = config.MONITOR_INDEX
        
        # Create scrollable frame
        canvas = tk.Canvas(root)
        scrollbar = ttk.Scrollbar(root, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Create main frame with padding
        main_frame = ttk.Frame(scrollable_frame, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="Configuration", font=("Arial", 14, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        row = 1
        
        # Hotkey (editable text)
        row = self._add_text_field(main_frame, "Hotkey", config.HOTKEY, row)
        
        # Monitor Index (special handling with buttons)
        row = self._add_monitor_selection(main_frame, row)
        
        # Crop Region (read-only for now, will handle in next step)
        if config.CROP_REGION:
            crop_str = f"left={config.CROP_REGION['left']}, top={config.CROP_REGION['top']}, "
            crop_str += f"width={config.CROP_REGION['width']}, height={config.CROP_REGION['height']}"
        else:
            crop_str = "None (full monitor)"
        row = self._add_label_field(main_frame, "Crop Region", crop_str, row)
        
        # Save Debug Images (checkbox)
        row = self._add_checkbox_field(main_frame, "Save Debug Images", config.SAVE_DEBUG_IMAGES, row)
        
        # CSV Path (editable text with browse button)
        row = self._add_file_field(main_frame, "CSV File Path", config.CSV_PATH, row, filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        
        # Tesseract Path (editable text with browse button)
        row = self._add_file_field(main_frame, "Tesseract Executable", config.pytesseract.pytesseract.tesseract_cmd, row, 
                                   filetypes=[("Executable", "*.exe"), ("All files", "*.*")])
        
        # Ollama URL (editable text)
        row = self._add_text_field(main_frame, "Ollama API URL", config.OLLAMA_URL, row)
        
        # Model Name (editable text)
        row = self._add_text_field(main_frame, "LLM Model Name", config.MODEL_NAME, row)
        
        # Status label
        self.status_label = ttk.Label(main_frame, text="App Status: Not Running", 
                                      font=("Arial", 9, "italic"), foreground="gray")
        self.status_label.grid(row=row, column=0, columnspan=2, pady=(20, 10))
        row += 1
        
        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=row, column=0, columnspan=2, pady=(10, 0))
        
        # Save button
        save_button = ttk.Button(button_frame, text="Save Config", 
                                command=self._save_config, width=15)
        save_button.pack(side=tk.LEFT, padx=5)
        
        # Start App button
        self.start_button = ttk.Button(button_frame, text="Start App", 
                                       command=self._start_app, width=15)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        # Close button
        close_button = ttk.Button(button_frame, text="Close", 
                                  command=self.root.destroy, width=15)
        close_button.pack(side=tk.LEFT, padx=5)
    
    def _add_text_field(self, parent: ttk.Frame, label: str, value: str, row: int) -> int:
        """Add an editable text field."""
        ttk.Label(parent, text=f"{label}:", font=("Arial", 9, "bold")).grid(
            row=row, column=0, sticky=tk.W, pady=5, padx=(0, 10)
        )
        entry = ttk.Entry(parent, width=50)
        entry.insert(0, str(value))
        entry.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        self.config_widgets[label] = entry
        return row + 1
    
    def _add_label_field(self, parent: ttk.Frame, label: str, value: str, row: int) -> int:
        """Add a read-only label field."""
        ttk.Label(parent, text=f"{label}:", font=("Arial", 9, "bold")).grid(
            row=row, column=0, sticky=tk.W, pady=5, padx=(0, 10)
        )
        ttk.Label(parent, text=str(value), font=("Arial", 9)).grid(
            row=row, column=1, sticky=tk.W, pady=5
        )
        return row + 1
    
    def _add_checkbox_field(self, parent: ttk.Frame, label: str, value: bool, row: int) -> int:
        """Add a checkbox field."""
        ttk.Label(parent, text=f"{label}:", font=("Arial", 9, "bold")).grid(
            row=row, column=0, sticky=tk.W, pady=5, padx=(0, 10)
        )
        var = tk.BooleanVar(value=value)
        checkbox = ttk.Checkbutton(parent, variable=var)
        checkbox.grid(row=row, column=1, sticky=tk.W, pady=5)
        self.config_widgets[label] = var
        return row + 1
    
    def _add_file_field(self, parent: ttk.Frame, label: str, value: str, row: int, 
                       filetypes: List[Tuple[str, str]] = None) -> int:
        """Add a file path field with browse button."""
        ttk.Label(parent, text=f"{label}:", font=("Arial", 9, "bold")).grid(
            row=row, column=0, sticky=tk.W, pady=5, padx=(0, 10)
        )
        frame = ttk.Frame(parent)
        frame.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        frame.columnconfigure(0, weight=1)
        
        entry = ttk.Entry(frame, width=40)
        entry.insert(0, str(value))
        entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        
        browse_button = ttk.Button(frame, text="Browse...", 
                                   command=lambda: self._browse_file(entry, filetypes))
        browse_button.grid(row=0, column=1)
        
        self.config_widgets[label] = entry
        return row + 1
    
    def _browse_file(self, entry: ttk.Entry, filetypes: List[Tuple[str, str]] = None) -> None:
        """Open file browser and update entry."""
        filename = filedialog.askopenfilename(filetypes=filetypes)
        if filename:
            entry.delete(0, tk.END)
            entry.insert(0, filename)
    
    def _add_monitor_selection(self, parent: ttk.Frame, row: int) -> int:
        """Add monitor selection with buttons."""
        ttk.Label(parent, text="Monitor Selection:", font=("Arial", 9, "bold")).grid(
            row=row, column=0, sticky=tk.W, pady=5, padx=(0, 10)
        )
        
        monitor_frame = ttk.Frame(parent)
        monitor_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        
        monitors = enumerate_monitors()
        self.monitor_buttons = []
        
        for idx, monitor_info in monitors:
            monitor_desc = self._get_monitor_description(idx, monitor_info)
            btn = ttk.Button(
                monitor_frame,
                text=f"Monitor {idx}: {monitor_desc}",
                command=lambda i=idx: self._select_monitor(i),
                width=30
            )
            btn.pack(side=tk.LEFT, padx=2)
            self.monitor_buttons.append((idx, btn))
            
            # Highlight current selection
            if idx == self.selected_monitor_index:
                btn.config(state=tk.DISABLED)
        
        return row + 1
    
    def _get_monitor_description(self, idx: int, monitor: Dict[str, int]) -> str:
        """Get a description for a monitor."""
        if idx == 0:
            return "All monitors"
        elif idx == 1:
            return f"Primary ({monitor['width']}x{monitor['height']})"
        else:
            return f"{monitor['width']}x{monitor['height']}"
    
    def _select_monitor(self, monitor_index: int) -> None:
        """Handle monitor selection - show overlay and update selection."""
        self.selected_monitor_index = monitor_index
        
        # Show overlay on selected monitor (must be called from main thread)
        overlay = MonitorOverlay(self.root, monitor_index, f"MONITOR {monitor_index}\nSELECTED", duration=3.0)
        overlay.show()
        
        # Update button states
        for idx, btn in self.monitor_buttons:
            if idx == monitor_index:
                btn.config(state=tk.DISABLED)
            else:
                btn.config(state=tk.NORMAL)
    
    def _save_config(self) -> None:
        """Save configuration to config.py file."""
        try:
            # Read current config.py
            config_path = "inventory_app/config.py"
            with open(config_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            # Update values
            updates = {
                "HOTKEY": f'"{self.config_widgets["Hotkey"].get()}"',
                "MONITOR_INDEX": str(self.selected_monitor_index),
                "SAVE_DEBUG_IMAGES": str(self.config_widgets["Save Debug Images"].get()),
                "CSV_PATH": f'"{self.config_widgets["CSV File Path"].get()}"',
                "OLLAMA_URL": f'"{self.config_widgets["Ollama API URL"].get()}"',
                "MODEL_NAME": f'"{self.config_widgets["LLM Model Name"].get()}"',
            }
            
            # Update tesseract path (special handling - it's an attribute assignment)
            tesseract_path = self.config_widgets["Tesseract Executable"].get()
            tesseract_line_pattern = "pytesseract.pytesseract.tesseract_cmd"
            
            # Write updated config
            new_lines = []
            for line in lines:
                updated = False
                
                # Special handling for tesseract path
                if tesseract_line_pattern in line and ("=" in line or "=" in line):
                    comment = ""
                    if "#" in line:
                        comment = " " + line[line.index("#"):].rstrip()
                    new_lines.append(f"{tesseract_line_pattern} = r\"{tesseract_path}\"{comment}\n")
                    updated = True
                
                # Handle other config values
                if not updated:
                    for key, value in updates.items():
                        if line.strip().startswith(key + " =") or line.strip().startswith(key + "="):
                            # Preserve comment if present
                            comment = ""
                            if "#" in line:
                                comment = " " + line[line.index("#"):].rstrip()
                            new_lines.append(f"{key} = {value}{comment}\n")
                            updated = True
                            break
                
                if not updated:
                    new_lines.append(line)
            
            with open(config_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
            
            # Reload config module to reflect changes
            import importlib
            importlib.reload(config)
            
            # Also update pytesseract path immediately
            config.pytesseract.pytesseract.tesseract_cmd = tesseract_path
            
            messagebox.showinfo("Success", "Configuration saved successfully!\n\nNote: Restart the app for changes to take effect.")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration:\n{e}")
    
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


def show_config_ui() -> None:
    """Create and display the configuration UI window."""
    root = tk.Tk()
    app = ConfigUI(root)
    root.mainloop()


if __name__ == "__main__":
    # Allow running the UI standalone for testing
    show_config_ui()
