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


class CropSelector:
    """Interactive crop rectangle selector with visual feedback."""
    
    def __init__(self, root: tk.Tk, monitor_index: int, callback):
        self.root = root
        self.monitor_index = monitor_index
        self.callback = callback  # Called with (left, top, width, height) or None
        self.overlay_window = None
        self.canvas = None
        self.start_point = None
        self.current_rect = None
        self.final_rect = None
        self.selection_complete = False
        
    def start_selection(self) -> None:
        """Start the crop selection process."""
        try:
            with mss.mss() as sct:
                monitors = sct.monitors
                if self.monitor_index < 0 or self.monitor_index >= len(monitors):
                    return
                
                monitor = monitors[self.monitor_index]
                
                # Create fullscreen overlay window
                self.overlay_window = tk.Toplevel(self.root)
                self.overlay_window.overrideredirect(True)
                self.overlay_window.attributes('-topmost', True)
                self.overlay_window.attributes('-alpha', 0.2)  # Very transparent background
                self.overlay_window.configure(bg='black')
                self.overlay_window.geometry(f"{monitor['width']}x{monitor['height']}+{monitor['left']}+{monitor['top']}")
                
                # Make the UI window also stay on top (but below overlay) so it's more accessible
                # We'll lower it slightly when overlay is active
                try:
                    self.root.attributes('-topmost', False)  # Let overlay be on top
                except:
                    pass
                
                # Create canvas for drawing
                self.canvas = tk.Canvas(
                    self.overlay_window,
                    bg='black',
                    highlightthickness=0,
                    cursor='crosshair'
                )
                self.canvas.pack(fill=tk.BOTH, expand=True)
                
                # Bind mouse events
                self.canvas.bind('<Button-1>', self._on_click)
                self.canvas.bind('<Motion>', self._on_motion)
                
                # Bind Escape key to window
                self.overlay_window.bind('<Escape>', self._cancel)
                self.canvas.bind('<Escape>', self._cancel)
                
                # Make window and canvas focusable
                self.overlay_window.focus_set()
                self.canvas.focus_set()
                
                # Instructions text
                self.instructions = self.canvas.create_text(
                    monitor['width'] // 2,
                    50,
                    text="Click to set top-left corner, then click again for bottom-right\n(Press ESC to cancel)",
                    fill='white',
                    font=("Arial", 16),
                    anchor=tk.CENTER
                )
                
                # Add a minimize button in top-right corner to access UI
                minimize_btn = tk.Button(
                    self.overlay_window,
                    text="Minimize Overlay",
                    command=self._minimize_overlay,
                    bg='darkgray',
                    fg='white',
                    font=("Arial", 14),
                    relief=tk.RAISED,
                    bd=2
                )
                minimize_btn.place(x=monitor['width'] - 150, y=10)
                
                self.overlay_window.update()
                
        except Exception as e:
            print(f"Error starting crop selection: {e}", file=sys.stderr)
            if self.callback:
                self.callback(None)
    
    def _on_click(self, event) -> None:
        """Handle mouse click."""
        # Ignore clicks after selection is complete
        if self.selection_complete:
            return
        
        if not self.start_point:
            # First click - set top-left corner
            self.start_point = (event.x, event.y)
            if self.instructions:
                self.canvas.delete(self.instructions)
                self.instructions = None
            # Update instructions
            self.canvas.create_text(
                self.canvas.winfo_width() // 2,
                50,
                text="Click again to set bottom-right corner\n(Press ESC to cancel)",
                fill='white',
                font=("Arial", 16),
                anchor=tk.CENTER,
                tags="instructions2"
            )
        else:
            # Second click - set bottom-right corner
            end_point = (event.x, event.y)
            self._finalize_rect(self.start_point, end_point)
    
    def _on_motion(self, event) -> None:
        """Handle mouse motion - update preview rectangle."""
        if self.start_point and not self.selection_complete:
            # Delete previous preview rectangle
            if self.current_rect:
                self.canvas.delete(self.current_rect)
            
            # Draw preview rectangle
            x1, y1 = self.start_point
            x2, y2 = event.x, event.y
            
            # Ensure x1 < x2 and y1 < y2
            left = min(x1, x2)
            top = min(y1, y2)
            right = max(x1, x2)
            bottom = max(y1, y2)
            
            self.current_rect = self.canvas.create_rectangle(
                left, top, right, bottom,
                outline='red',
                width=3,
                fill='',
                stipple='gray50'
            )
    
    def _finalize_rect(self, start: Tuple[int, int], end: Tuple[int, int]) -> None:
        """Finalize the rectangle selection."""
        x1, y1 = start
        x2, y2 = end
        
        # Ensure x1 < x2 and y1 < y2
        left = min(x1, x2)
        top = min(y1, y2)
        right = max(x1, x2)
        bottom = max(y1, y2)
        
        # Delete preview rectangle and instructions
        if self.current_rect:
            self.canvas.delete(self.current_rect)
        self.canvas.delete("instructions2")
        
        # Draw final rectangle
        self.final_rect = self.canvas.create_rectangle(
            left, top, right, bottom,
            outline='red',
            width=4,
            fill='',
            stipple='gray25'
        )
        
        # Add confirmation text
        self.canvas.create_text(
            self.canvas.winfo_width() // 2,
            50,
            text="Crop region selected!\nUse Accept/Discard buttons in the UI",
            fill='yellow',
            font=("Arial", 18, "bold"),
            anchor=tk.CENTER
        )
        
        self.selection_complete = True
        
        # Get monitor offset to convert to absolute coordinates
        with mss.mss() as sct:
            monitors = sct.monitors
            monitor = monitors[self.monitor_index]
            absolute_left = monitor['left'] + left
            absolute_top = monitor['top'] + top
        
        # Calculate relative to monitor
        crop_region = {
            'left': left,
            'top': top,
            'width': right - left,
            'height': bottom - top
        }
        
        # Call callback with the crop region (keep window open until Accept/Discard)
        if self.callback:
            self.callback(crop_region)
    
    def _minimize_overlay(self) -> None:
        """Minimize the overlay to access UI window."""
        if self.overlay_window:
            # Hide the canvas temporarily
            if self.canvas:
                self.canvas.pack_forget()
            
            # Move overlay to a small window in corner
            self.overlay_window.geometry("220x140+10+10")
            self.overlay_window.attributes('-alpha', 0.95)
            
            # Create a frame for the restore button (destroy old one if exists)
            if hasattr(self, 'minimize_frame') and self.minimize_frame:
                try:
                    self.minimize_frame.destroy()
                except:
                    pass
            
            self.minimize_frame = tk.Frame(self.overlay_window, bg='#2b2b2b', relief=tk.RAISED, bd=2)
            self.minimize_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
            
            # Add status text first
            status_text = "Overlay Minimized"
            if self.selection_complete:
                status_text += "\n✓ Crop Selected"
            status_label = tk.Label(
                self.minimize_frame,
                text=status_text,
                bg='#2b2b2b',
                fg='white',
                font=("Arial", 10, "bold")
            )
            status_label.pack(pady=(10, 5))
            
            # Add restore button
            restore_btn = tk.Button(
                self.minimize_frame,
                text="Restore Overlay",
                command=self._restore_overlay,
                bg='#0066cc',
                fg='white',
                font=("Arial", 11, "bold"),
                relief=tk.RAISED,
                bd=2,
                cursor='hand2',
                activebackground='#0052a3',
                activeforeground='white'
            )
            restore_btn.pack(fill=tk.X, padx=10, pady=5)
            
            # Update window to show the frame
            self.overlay_window.update()
    
    def _restore_overlay(self) -> None:
        """Restore the overlay to fullscreen."""
        if self.overlay_window:
            # Remove minimize frame
            if hasattr(self, 'minimize_frame') and self.minimize_frame:
                try:
                    self.minimize_frame.destroy()
                    delattr(self, 'minimize_frame')
                except:
                    pass
            
            # Restore canvas
            if self.canvas:
                self.canvas.pack(fill=tk.BOTH, expand=True)
            
            with mss.mss() as sct:
                monitors = sct.monitors
                if self.monitor_index < len(monitors):
                    monitor = monitors[self.monitor_index]
                    self.overlay_window.geometry(f"{monitor['width']}x{monitor['height']}+{monitor['left']}+{monitor['top']}")
                    self.overlay_window.attributes('-alpha', 0.2)
                    self.overlay_window.update()
    
    def _cancel(self, event=None) -> None:
        """Cancel selection."""
        self.close()
        if self.callback:
            self.callback(None)
    
    def close(self) -> None:
        """Close the overlay window."""
        if self.overlay_window:
            self.overlay_window.destroy()
            self.overlay_window = None
            # Restore UI window topmost if needed
            try:
                # Don't force topmost, let it be normal
                pass
            except:
                pass


class ConfigUI:
    """UI window to display and configure application settings."""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Inventory Screenshot App")
        self.root.geometry("700x700")
        self.app_running = False
        self.config_widgets: Dict[str, Any] = {}
        self.selected_monitor_index = config.MONITOR_INDEX
        self.pending_crop_region = None
        self.crop_selector = None
        self.crop_accept_button = None
        self.crop_discard_button = None
        self.crop_status_label = None
        
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
        
        # Crop Region (interactive selection)
        row = self._add_crop_selection(main_frame, row)
        
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
    
    def _add_crop_selection(self, parent: ttk.Frame, row: int) -> int:
        """Add crop region selection with interactive button."""
        ttk.Label(parent, text="Crop Region:", font=("Arial", 9, "bold")).grid(
            row=row, column=0, sticky=tk.W, pady=5, padx=(0, 10)
        )
        
        crop_frame = ttk.Frame(parent)
        crop_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        
        # Current crop display
        if config.CROP_REGION:
            crop_str = f"left={config.CROP_REGION['left']}, top={config.CROP_REGION['top']}, "
            crop_str += f"width={config.CROP_REGION['width']}, height={config.CROP_REGION['height']}"
        else:
            crop_str = "None (full monitor)"
        
        self.crop_status_label = ttk.Label(crop_frame, text=crop_str, font=("Arial", 9))
        self.crop_status_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # Select button
        select_button = ttk.Button(crop_frame, text="Select Crop Area", 
                                   command=self._start_crop_selection)
        select_button.pack(side=tk.LEFT, padx=2)
        
        # Accept/Discard buttons (initially hidden)
        self.crop_accept_button = ttk.Button(crop_frame, text="Accept", 
                                            command=self._accept_crop, state=tk.DISABLED)
        self.crop_accept_button.pack(side=tk.LEFT, padx=2)
        
        self.crop_discard_button = ttk.Button(crop_frame, text="Discard", 
                                             command=self._discard_crop, state=tk.DISABLED)
        self.crop_discard_button.pack(side=tk.LEFT, padx=2)
        
        return row + 1
    
    def _start_crop_selection(self) -> None:
        """Start the interactive crop selection."""
        if self.selected_monitor_index is None:
            messagebox.showwarning("No Monitor Selected", 
                                 "Please select a monitor first before selecting crop region.")
            return
        
        # Create crop selector
        self.crop_selector = CropSelector(
            self.root,
            self.selected_monitor_index,
            self._on_crop_selected
        )
        self.crop_selector.start_selection()
    
    def _on_crop_selected(self, crop_region: Dict[str, int] | None) -> None:
        """Callback when crop region is selected."""
        if crop_region is None:
            # Selection was cancelled (ESC pressed or other cancellation)
            if self.crop_selector:
                self.crop_selector.close()
                self.crop_selector = None
            
            # Clear pending crop region and reset UI state
            self.pending_crop_region = None
            
            # Reset status label to current config
            if config.CROP_REGION:
                crop_str = f"left={config.CROP_REGION['left']}, top={config.CROP_REGION['top']}, "
                crop_str += f"width={config.CROP_REGION['width']}, height={config.CROP_REGION['height']}"
            else:
                crop_str = "None (full monitor)"
            self.crop_status_label.config(text=crop_str)
            
            # Disable Accept/Discard buttons
            self.crop_accept_button.config(state=tk.DISABLED)
            self.crop_discard_button.config(state=tk.DISABLED)
            return
        
        # Store pending crop region
        self.pending_crop_region = crop_region
        
        # Update status label
        crop_str = f"left={crop_region['left']}, top={crop_region['top']}, "
        crop_str += f"width={crop_region['width']}, height={crop_region['height']}"
        self.crop_status_label.config(text=crop_str + " (pending)")
        
        # Enable Accept/Discard buttons
        self.crop_accept_button.config(state=tk.NORMAL)
        self.crop_discard_button.config(state=tk.NORMAL)
    
    def _accept_crop(self) -> None:
        """Accept the selected crop region."""
        if self.pending_crop_region:
            # Update the config widget (we'll save it when Save Config is clicked)
            # For now, just update the display
            crop_str = f"left={self.pending_crop_region['left']}, top={self.pending_crop_region['top']}, "
            crop_str += f"width={self.pending_crop_region['width']}, height={self.pending_crop_region['height']}"
            self.crop_status_label.config(text=crop_str)
            
            # Disable buttons
            self.crop_accept_button.config(state=tk.DISABLED)
            self.crop_discard_button.config(state=tk.DISABLED)
            
            # Close overlay if still open
            if self.crop_selector:
                self.crop_selector.close()
                self.crop_selector = None
            
            messagebox.showinfo("Crop Accepted", 
                              f"Crop region accepted.\n\n"
                              f"Click 'Save Config' to save this change permanently.")
    
    def _discard_crop(self) -> None:
        """Discard the selected crop region."""
        # Reset to current config
        if config.CROP_REGION:
            crop_str = f"left={config.CROP_REGION['left']}, top={config.CROP_REGION['top']}, "
            crop_str += f"width={config.CROP_REGION['width']}, height={config.CROP_REGION['height']}"
        else:
            crop_str = "None (full monitor)"
        self.crop_status_label.config(text=crop_str)
        
        # Clear pending crop
        self.pending_crop_region = None
        
        # Disable buttons
        self.crop_accept_button.config(state=tk.DISABLED)
        self.crop_discard_button.config(state=tk.DISABLED)
        
        # Close overlay if still open
        if self.crop_selector:
            self.crop_selector.close()
            self.crop_selector = None
    
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
            
            # Handle crop region if accepted
            crop_region_pattern = "CROP_REGION ="
            if self.pending_crop_region:
                crop_dict = self.pending_crop_region
                updates["CROP_REGION"] = f'{{"left": {crop_dict["left"]}, "top": {crop_dict["top"]}, "width": {crop_dict["width"]}, "height": {crop_dict["height"]}}}'
            
            # Update tesseract path (special handling - it's an attribute assignment)
            tesseract_path = self.config_widgets["Tesseract Executable"].get()
            tesseract_line_pattern = "pytesseract.pytesseract.tesseract_cmd"
            
            # Write updated config
            new_lines = []
            skip_next_line = False  # Skip comment lines after CROP_REGION
            
            for i, line in enumerate(lines):
                if skip_next_line:
                    skip_next_line = False
                    continue
                
                updated = False
                
                # Special handling for tesseract path
                if tesseract_line_pattern in line and ("=" in line):
                    comment = ""
                    if "#" in line:
                        comment = " " + line[line.index("#"):].rstrip()
                    new_lines.append(f"{tesseract_line_pattern} = r\"{tesseract_path}\"{comment}\n")
                    updated = True
                
                # Special handling for crop region (multi-line)
                if crop_region_pattern in line and not updated:
                    if self.pending_crop_region:
                        # Replace the CROP_REGION line
                        comment = ""
                        if "#" in line:
                            comment = " " + line[line.index("#"):].rstrip()
                        new_lines.append(f"CROP_REGION = {updates['CROP_REGION']}{comment}\n")
                        updated = True
                        # Skip the next line if it's a comment
                        if i + 1 < len(lines) and lines[i + 1].strip().startswith("#"):
                            skip_next_line = True
                
                # Handle other config values
                if not updated:
                    for key, value in updates.items():
                        if key == "CROP_REGION":
                            continue  # Already handled above
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
            
            # Clear pending crop region after save
            if self.pending_crop_region:
                self.pending_crop_region = None
                # Update display to remove "(pending)" text
                if config.CROP_REGION:
                    crop_str = f"left={config.CROP_REGION['left']}, top={config.CROP_REGION['top']}, "
                    crop_str += f"width={config.CROP_REGION['width']}, height={config.CROP_REGION['height']}"
                    self.crop_status_label.config(text=crop_str)
            
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
