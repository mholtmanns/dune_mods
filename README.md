## Dune: Awakening Inventory Screenshot App (Windows, Python)

This Python app listens for a global hotkey (German **STRG+ALT+.**, i.e. `Ctrl+Alt+.`), captures a cropped area of the screen that contains an inventory/resource list associated with an item to be fabricated, and processes screenshots in the background using a queue system. Each screenshot is split into 8 tiles, pre-screened with Tesseract OCR, sent to a local vision LLM (Ollama), and the recognized items update a CSV file.

The app only works properly if thee screenshot is taken while viewing any of the fabricators production screens.

**Key Features:**
- **Background processing**: Take multiple screenshots without waiting - they're queued and processed asynchronously
- **Queue system**: Screenshots are processed one at a time in a background worker thread
- **CSV updates**: Existing inventory items are updated (not duplicated) based on item name

The CSV file is called `inventory_log.csv` and will be created in the same folder as the script by default.

### ToDo

Implement a simple UI to define things like
- Interactive CSV file selection
- Interactive Monitor and crop region selection
- Adding small status window for task progress

### Project Structure

The app is organized into a modular structure:

- `main.py` - Entry point with hotkey handling and queue processor initialization
- `inventory_app/` - Main package
  - `config.py` - Configuration constants (hotkey, monitor, crop region, LLM settings, etc.)
  - `image_handler.py` - Screenshot capture, image splitting, OCR pre-screening, debug saving
  - `llm_client.py` - Communication with Ollama vision LLM API
  - `csv_handler.py` - CSV file operations (header management, reading/updating inventory data)
  - `queue_processor.py` - Background queue system for asynchronous screenshot processing

### 1. Prerequisites

- **Python 3.9+** installed and on your PATH.
- **Windows 10 or later** (tested on Windows).
- A running **Ollama** instance with a **vision model** installed (e.g. `qwen3-vl:8b`).

#### Install Tesseract OCR (used for pre-screening tiles)

1. Download the Tesseract OCR Windows installer from the official project (for example: `tesseract-ocr-w64-setup-*.exe`).
2. Install it, keeping note of the installation path, e.g.:
   - `C:\Program Files\Tesseract-OCR\tesseract.exe`
3. After installation, if `tesseract.exe` is not on your PATH, open `inventory_app/config.py` and ensure this line is set correctly:

```python
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
```

### 2. Install Python dependencies

In a terminal opened in the project folder:

```bash
pip install -r requirements.txt
```

This will install:

- `keyboard` – global hotkey listener
- `mss` – fast screenshots
- `Pillow` – image handling
- `requests` – HTTP client for talking to Ollama
- `pytesseract` – OCR wrapper for Tesseract (used only to check if a tile contains text)

> On some systems, the `keyboard` package may require running the terminal as administrator to receive global key events.

### 3. Run the app

From the project directory:

```bash
python main.py
```

Useful options:

- **Help**:

  ```bash
  python main.py --help
  ```

- **Verbose/debug output**:

  ```bash
  python main.py --verbose
  ```

You should see a message similar to:

```text
Inventory Screenshot App
========================
Hotkey: ctrl+alt+.  (German STRG+ALT+.)
CSV file: inventory_log.csv
LLM API URL: http://localhost:11434/api/generate
✓ Background queue processor started
✓ Hotkey 'ctrl+alt+.' registered successfully.
Press the hotkey to capture and process a screenshot.
Press Ctrl+C in this terminal to exit.
```

Now:

1. Bring your inventory / resource UI onto the screen (on the monitor selected by `MONITOR_INDEX`).
2. Make sure the configured crop rectangle (`CROP_REGION` in `inventory_app/config.py`) covers the "Resources Required" panel area.
3. Press **STRG+ALT+.** (`Ctrl+Alt+.`).
4. You'll immediately see: `"Screenshot queued as task #1 (1 task(s) in queue)"` - the screenshot is captured and queued instantly.
5. **You can press the hotkey multiple times** without waiting - each screenshot gets queued with a unique task ID.
6. In the background, each task is processed:
   - The captured image is split into **8 tiles** arranged in a **4×2 grid** (4 columns, 2 rows).
   - For each tile, run **Tesseract**; if it detects no text, that tile is skipped.
   - For the remaining tiles, send each tile **individually** to the configured **Ollama vision model** with a JSON-only prompt.
   - Parse the JSON responses and **update** `inventory_log.csv` (existing items are updated, new items are added).
7. When each batch completes, you'll see: `"Task #N: Updated CSV with X items (took Y.Ys)"`

### 4. How the vision / OCR pipeline works

- The crop region is defined by `CROP_REGION` (left, top, width, height) in `inventory_app/config.py` and is relative to the chosen monitor.
- The captured image (default 1360×300 on a 2560x1440 display) is split by `split_image_into_subimages` into 8 tiles in a **4×2 grid**.
- Each tile is passed to `image_has_text`:
  - Converts to grayscale.
  - Uses `pytesseract.image_to_string(..., lang="eng")`.
  - If the result contains any alphanumeric characters, the tile is considered to contain text.
  - Tiles without text are **not** sent to the LLM.
- The remaining tiles are sent one-by-one to Ollama (`qwen3-vl:8b` by default), using a prompt that asks for:

  - `item_name` (string, or `"NONE"` for empty tiles)
  - `required_count` (integer or `null`)
  - `available_count` (integer or `null`)

The model is instructed to return **only valid JSON** so the app can parse it directly.

### 5. CSV output and queue system

`inventory_log.csv` has the header:

```text
timestamp,item_name,available_count,required_count
```

Where `required_count` is only a momentary snapshot of the current item to fabricate when taking the screenshot. It can be ignored for now.

**CSV Update Behavior:**
- The CSV file is **updated** (not appended) - existing items with the same `item_name` are updated with new counts and timestamp
- New items are added as new rows
- Items are sorted alphabetically by `item_name` for consistency
- Each completed task updates the CSV file once with all its recognized items

**Queue System:**
- Screenshots are captured instantly and queued for background processing
- Tasks are processed sequentially (one at a time) to avoid overwhelming the LLM API
- Each task has a unique ID for tracking progress
- The queue size is shown when screenshots are captured
- CSV updates are thread-safe (protected by locks) to prevent data corruption

You can open the CSV file in Excel, LibreOffice, or any CSV tool to analyze your inventory over time. The file is updated after each batch completes, so you can monitor changes in real-time.

### 6. Notes and customization

- **CSV file location**: set `CSV_PATH` in `inventory_app/config.py` to point to the desired location of the CSV file
- **Screenshot region**: adjust `CROP_REGION` in `inventory_app/config.py` if the yellow "Resources Required" rectangle moves or if your resolution changes.
- **Monitor selection**: set `MONITOR_INDEX` near the top of the script:
  - `1` = primary monitor (default)
  - `0` = all monitors combined (virtual desktop)
  - `2`, `3`, ... = specific monitor index reported by `mss`
  
  Windows display enumeration is not always consistent and can change between reboots, or even after wake-up from suspend mode. Especially in case of more complex multi-monitor setups.

  In case of unexpected behavior, enable verbose output and if necessary save debug images by setting `SAVE_DEBUG_IMAGES` in `inventory_app/config.py` to `True`.
- **Hotkey**: change the `HOTKEY` constant (for example, `HOTKEY = "ctrl+shift+i"`).
- **Ollama model**: change `MODEL_NAME` to any compatible vision model you have installed (e.g. `llama3.2-vision`, `qwen2.5vl:7b`, etc.).
- **Verbose logging**: use `--verbose` to see:
  - Queue status and task processing details
  - OCR snippets from each tile
  - Which tiles were skipped by OCR
  - Per-image LLM calls and results
  - CSV update operations (what was updated vs. added)

If you adjust your UI layout (different size, different number of tiles), we can update the crop region and the grid splitting logic to match.  
If you share an updated screenshot and the exact values you expect in CSV, we can further refine the prompt and parsing.
