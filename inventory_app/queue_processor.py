"""
Queue processor module: handles background processing of screenshot tasks.
"""
import queue
import sys
import threading
from datetime import datetime
from typing import Any, Dict, List

from PIL import Image

from inventory_app.config import SAVE_DEBUG_IMAGES
from inventory_app.csv_handler import update_inventory_csv
from inventory_app.image_handler import (
    pre_screen_subimages,
    save_debug_image,
    split_image_into_subimages,
)
from inventory_app.llm_client import call_llm_api


class ScreenshotTask:
    """Represents a screenshot processing task."""
    def __init__(self, image: Image.Image, task_id: int, timestamp: datetime):
        self.image = image
        self.task_id = task_id
        self.timestamp = timestamp


class QueueProcessor:
    """
    Manages a queue of screenshot tasks and processes them in a background thread.
    """
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.task_queue: queue.Queue[ScreenshotTask] = queue.Queue()
        self.worker_thread: threading.Thread | None = None
        self.running = False
        self.task_counter = 0
        self.csv_lock = threading.Lock()  # Thread-safe CSV updates
        self._log(f"Queue processor initialized")

    def _log(self, message: str) -> None:
        """Print a log message only when verbose mode is enabled."""
        if self.verbose:
            print(f"[QueueProcessor] {message}")

    def start(self) -> None:
        """Start the background worker thread."""
        if self.running:
            return
        
        self.running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        self._log("Background worker thread started")

    def stop(self) -> None:
        """Stop the background worker thread and wait for current task to finish."""
        self.running = False
        if self.worker_thread:
            self._log("Waiting for worker thread to finish current task...")
            self.worker_thread.join(timeout=30)  # Wait up to 30 seconds
            if self.worker_thread.is_alive():
                print("Warning: Worker thread did not stop gracefully", file=sys.stderr)
            else:
                self._log("Worker thread stopped")

    def enqueue_screenshot(self, image: Image.Image) -> int:
        """
        Add a screenshot to the processing queue.
        Returns the task ID for tracking.
        """
        self.task_counter += 1
        task_id = self.task_counter
        timestamp = datetime.now()
        task = ScreenshotTask(image, task_id, timestamp)
        
        self.task_queue.put(task)
        self._log(f"Enqueued task #{task_id} (queue size: {self.task_queue.qsize()})")
        return task_id

    def get_queue_size(self) -> int:
        """Get the current number of tasks waiting in the queue."""
        return self.task_queue.qsize()

    def _worker_loop(self) -> None:
        """Main worker loop that processes tasks from the queue."""
        self._log("Worker thread started")
        
        while self.running:
            try:
                # Get a task from the queue (with timeout to allow checking self.running)
                try:
                    task = self.task_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                self._process_task(task)
                self.task_queue.task_done()
                
            except Exception as e:
                print(f"Error in worker thread: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc()
        
        self._log("Worker thread exiting")

    def _process_task(self, task: ScreenshotTask) -> None:
        """Process a single screenshot task."""
        task_start = datetime.now()
        self._log(f"Processing task #{task.task_id}...")
        
        try:
            img = task.image
            self._log(f"Task #{task.task_id}: Image size {img.size[0]}x{img.size[1]} pixels")
            
            # Save full screenshot if debug enabled
            if SAVE_DEBUG_IMAGES:
                save_debug_image(img, f"capture_full_task{task.task_id}", self.verbose)
            
            # Split into 8 subimages (4x2 grid)
            subimages = split_image_into_subimages(img)
            self._log(
                f"Task #{task.task_id}: Split into {len(subimages)} subimages in 4x2 grid "
                f"(each {subimages[0].size[0]}x{subimages[0].size[1]} pixels)"
            )
            
            # Save each subimage if debug enabled
            if SAVE_DEBUG_IMAGES:
                ts = datetime.now().strftime("%Y%m%d-%H%M%S")
                for i, subimg in enumerate(subimages):
                    save_debug_image(subimg, f"subimage_{i+1}_task{task.task_id}_{ts}", self.verbose)

            # Pre-screen subimages with Tesseract; keep only those with detected text
            screened_subimages = pre_screen_subimages(subimages, self.verbose)

            if not screened_subimages:
                print(f"Task #{task.task_id}: No text detected in any subimage; skipping.")
                return

            # Call LLM API for remaining subimages
            items = call_llm_api(screened_subimages, self.verbose)
            
            if not items:
                print(f"Task #{task.task_id}: No items returned from LLM API.")
                return
            
            self._log(f"Task #{task.task_id}: Received {len(items)} items from LLM API")
            for i, item in enumerate(items, 1):
                self._log(
                    f"Task #{task.task_id}:   {i}. {item.get('item_name', 'Unknown')}: "
                    f"Available={item.get('available_count')}, "
                    f"Required={item.get('required_count')}"
                )
            
            # Update CSV with thread-safe lock
            with self.csv_lock:
                update_inventory_csv(items, verbose=self.verbose)
            
            task_duration = (datetime.now() - task_start).total_seconds()
            print(f"Task #{task.task_id}: Updated CSV with {len(items)} items (took {task_duration:.1f}s)")
            
        except Exception as e:
            print(f"Task #{task.task_id}: Error during processing: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()

