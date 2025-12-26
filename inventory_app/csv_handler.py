"""
CSV file handling module: manages inventory data storage and retrieval.
"""
import csv
import os
import sys
from datetime import datetime
from typing import Any, Dict, List

from inventory_app.config import CSV_HEADER, CSV_PATH


def log(message: str, verbose: bool = False) -> None:
    """Print a log message only when verbose mode is enabled."""
    if verbose:
        print(message)


def ensure_csv_header(path: str, verbose: bool = False) -> None:
    """
    Create CSV with header if it doesn't exist.
    If it exists with a different header, keep it but warn in stdout so the
    user can decide whether to recreate the file.
    """
    if not os.path.exists(path):
        with open(path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADER)
        return

    try:
        with open(path, mode="r", encoding="utf-8") as f:
            first_line = f.readline().strip()
        existing = [h.strip() for h in first_line.split(",")] if first_line else []
        if existing and existing != CSV_HEADER:
            log(
                f"Warning: CSV header is {existing}, expected {CSV_HEADER}. "
                "Continuing without modifying the file.",
                verbose
            )
    except OSError as exc:
        print(f"Could not verify CSV header: {exc}", file=sys.stderr)


def read_csv_data(path: str) -> Dict[str, List[str]]:
    """
    Read existing CSV data and return a dictionary mapping item_name to row data.
    Returns dict with keys: item_name -> [timestamp, item_name, available_count, required_count]
    """
    data: Dict[str, List[str]] = {}
    
    if not os.path.exists(path):
        return data
    
    try:
        with open(path, mode="r", newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader, None)  # Skip header
            if header != CSV_HEADER:
                # If header doesn't match, return empty dict (will be handled by ensure_csv_header)
                return data
            
            for row in reader:
                if len(row) >= 2:  # At least timestamp and item_name
                    item_name = row[1].strip()
                    if item_name and item_name not in ("NONE", "ERROR"):
                        # Store the row, overwriting if item_name already exists (keep most recent)
                        data[item_name] = row
    except (OSError, csv.Error) as exc:
        print(f"Error reading CSV file: {exc}", file=sys.stderr)
        return {}
    
    return data


def update_inventory_csv(
    items: List[Dict[str, Any]], 
    path: str = CSV_PATH, 
    verbose: bool = False
) -> None:
    """
    Update the CSV file with new inventory items.
    - Reads existing CSV data
    - Updates rows where item_name matches
    - Adds new rows for items not found
    - Filters out items with item_name "NONE" or "ERROR"
    - Writes the updated data back to the file
    """
    if not items:
        return

    ensure_csv_header(path, verbose)
    
    # Read existing data
    existing_data = read_csv_data(path)
    log(f"Read {len(existing_data)} existing items from CSV", verbose)
    
    # Prepare new timestamp
    timestamp = datetime.now().isoformat(timespec="seconds")
    
    # Update or add items
    updated_count = 0
    added_count = 0
    
    for item in items:
        # Skip NONE and ERROR items
        item_name = item.get("item_name", "").strip()
        if not item_name or item_name in ("NONE", "ERROR"):
            continue
        
        # Prepare new row data
        new_row = [
            timestamp,
            item_name,
            str(item.get("available_count", "")),
            str(item.get("required_count", "")),
        ]
        
        if item_name in existing_data:
            # Update existing row
            existing_data[item_name] = new_row
            updated_count += 1
            log(f"Updated: {item_name}", verbose)
        else:
            # Add new row
            existing_data[item_name] = new_row
            added_count += 1
            log(f"Added: {item_name}", verbose)
    
    # Write all data back to CSV
    try:
        with open(path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADER)
            # Write rows sorted by item_name for consistency
            for item_name in sorted(existing_data.keys()):
                writer.writerow(existing_data[item_name])
        
        log(f"CSV updated: {updated_count} updated, {added_count} added, {len(existing_data)} total items", verbose)
    except OSError as exc:
        print(f"Error writing CSV file: {exc}", file=sys.stderr)
        raise


# Keep the old function name as an alias for backwards compatibility (if needed)
append_inventory_to_csv = update_inventory_csv

