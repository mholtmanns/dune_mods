"""
Main entry point for the Inventory Screenshot App.
Handles hotkey registration and coordinates the workflow with background queue processing.
"""
import argparse
import sys
import time
from datetime import datetime

import keyboard  # type: ignore

from inventory_app.config import (
    CSV_PATH,
    HOTKEY,
    OLLAMA_URL,
)
from inventory_app.csv_handler import ensure_csv_header
from inventory_app.image_handler import take_screenshot
from inventory_app.queue_processor import QueueProcessor

# Global verbose flag (set by command line argument)
VERBOSE = False

# Global queue processor instance
queue_processor: QueueProcessor | None = None


def log(message: str) -> None:
    """Print a log message only when verbose mode is enabled."""
    if VERBOSE:
        print(message)


def handle_hotkey() -> None:
    """Callback for when the hotkey is pressed. Quickly captures and enqueues the screenshot."""
    global queue_processor
    
    # Always print this to confirm hotkey is working
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Hotkey pressed, capturing screenshot...")
    
    try:
        # Capture screenshot (this should be fast)
        img = take_screenshot(verbose=VERBOSE)
        log(f"Captured image size: {img.size[0]}x{img.size[1]} pixels")
        
        # Enqueue for background processing
        if queue_processor:
            task_id = queue_processor.enqueue_screenshot(img)
            queue_size = queue_processor.get_queue_size()
            print(f"Screenshot queued as task #{task_id} ({queue_size} task(s) in queue)")
        else:
            print("Error: Queue processor not initialized!", file=sys.stderr)
        
    except Exception as e:
        print(f"Error during screenshot capture: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()


def start_app(verbose: bool = False) -> None:
    """Start the main application (hotkey listener and queue processor)."""
    global VERBOSE, queue_processor
    
    VERBOSE = verbose
    
    print("Inventory Screenshot App")
    print("========================")
    print(f"Hotkey: {HOTKEY}  (German STRG+ALT+.)")
    print(f"CSV file: {CSV_PATH}")
    print(f"LLM API URL: {OLLAMA_URL}")
    if VERBOSE:
        print("Verbose logging is ENABLED.")
    print("Press the hotkey to capture and process a screenshot.")
    print("Press Ctrl+C in this terminal to exit.\n")

    ensure_csv_header(CSV_PATH, verbose=VERBOSE)

    # Initialize and start the queue processor
    queue_processor = QueueProcessor(verbose=VERBOSE)
    queue_processor.start()
    print("✓ Background queue processor started")

    # Register hotkey with error handling
    try:
        keyboard.add_hotkey(HOTKEY, handle_hotkey)
        print(f"✓ Hotkey '{HOTKEY}' registered successfully.")
        if VERBOSE:
            print("Note: On Windows, the keyboard library may require administrator privileges.")
            print("If the hotkey doesn't work, try running this script as administrator.")
    except Exception as e:
        print(f"✗ Failed to register hotkey '{HOTKEY}': {e}", file=sys.stderr)
        print("\nTroubleshooting tips:", file=sys.stderr)
        print("1. Try running this script as administrator (right-click → Run as administrator)", file=sys.stderr)
        print("2. Check if another application is using the same hotkey", file=sys.stderr)
        print("3. Try a different hotkey combination (e.g., 'ctrl+alt+l')", file=sys.stderr)
        print("4. If using 'ctrl+alt+.' (period), try 'ctrl+alt+period' instead", file=sys.stderr)
        queue_processor.stop()
        raise
    
    # Verify hotkey is actually working (optional verbose check)
    if VERBOSE:
        print("\nWaiting for hotkey press... If nothing happens when you press it, the hotkey may not be working.")
        print("Common causes: insufficient permissions, hotkey conflict, or keyboard library issue.")
        print("You can take multiple screenshots without waiting - they will be processed in the background.")

    # Keep the script running
    try:
        while True:
            time.sleep(1)
            # Optionally show queue status in verbose mode
            if VERBOSE and queue_processor:
                queue_size = queue_processor.get_queue_size()
                if queue_size > 0:
                    log(f"Queue status: {queue_size} task(s) waiting")
    except KeyboardInterrupt:
        print("\nExiting...")
        if queue_processor:
            queue_processor.stop()
        keyboard.unhook_all()  # Clean up hotkey registration
        print("Shutdown complete.")


def main() -> None:
    global VERBOSE

    parser = argparse.ArgumentParser(
        description="Capture a cropped screen region, split into 8 images, "
        "send each to a vision LLM, and log inventory data to CSV."
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose/debug output.",
    )
    parser.add_argument(
        "--no-ui",
        action="store_true",
        help="Start the app directly without showing the UI (legacy mode).",
    )

    args = parser.parse_args()
    VERBOSE = args.verbose
    
    # Default behavior: show UI. Use --no-ui to start app directly
    if not args.no_ui:
        from inventory_app.ui import show_config_ui
        show_config_ui()
    else:
        start_app(verbose=VERBOSE)


if __name__ == "__main__":
    main()

