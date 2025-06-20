"""
CSV file-based storage adapter implementation.

This adapter stores data in a CSV file, providing persistence across application restarts.
It uses an in-memory cache (`_data_cache`) for reads and writes to the CSV file
upon modification (`_save_data`).
"""
import csv
import os
import uuid
import shutil
from typing import List, Optional, Dict, Any

from src.core.storage_interface import StorageInterface

class CsvStorage(StorageInterface):
    """
    Implements the StorageInterface using a CSV file for persistence.

    Attributes:
        filepath (str): Path to the CSV file.
        fieldnames (List[str]): List of column headers for the CSV file.
        _data_cache (List[Dict[str, Any]]): In-memory cache of the CSV data.
    """
    def __init__(self, filepath: str, fieldnames: List[str]):
        """
        Initializes the CsvStorage adapter.

        Args:
            filepath: The path to the CSV file where data will be stored.
            fieldnames: A list of strings representing the header row of the CSV.
                        Must include 'id'.
        """
        self.filepath = filepath
        if not fieldnames or 'id' not in fieldnames:
            # Ensure 'id' is a field, or prepend it if necessary.
            # For simplicity, we assume 'id' will be correctly provided by config.
            pass
        self.fieldnames = fieldnames
        self._data_cache: List[Dict[str, Any]] = []

        # Ensure the directory for the CSV file exists
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)

        self._load_data()
        print(f"CsvStorage initialized. Data file: {self.filepath}")

    def _load_data(self) -> None:
        """
        Loads data from the CSV file into the in-memory cache (`_data_cache`).
        If the file doesn't exist or is empty, it initializes an empty cache
        and ensures the file is created with headers on the first save.
        """
        if not os.path.exists(self.filepath) or os.path.getsize(self.filepath) == 0:
            self._data_cache = []
            # Ensure file with headers is created if it was empty/non-existent
            if self.fieldnames:
                 with open(self.filepath, 'w', newline='') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=self.fieldnames)
                    writer.writeheader()
            return

        try:
            with open(self.filepath, mode='r', newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                # Basic check for fieldnames consistency (optional, DictReader adapts)
                if reader.fieldnames and not all(f in reader.fieldnames for f in self.fieldnames):
                    print(f"Warning: Fieldnames in {self.filepath} differ from configured fieldnames.")
                self._data_cache = [row for row in reader]
        except FileNotFoundError: # Should be caught by os.path.exists, but as a safeguard
            self._data_cache = []
        except Exception as e:
            print(f"Error loading data from {self.filepath}: {e}. Starting with an empty cache.")
            self._data_cache = []


    def _save_data(self) -> None:
        """
        Saves the current state of `_data_cache` to the CSV file.
        Uses a temporary file for writing to prevent data corruption in case of errors,
        then replaces the original file.
        """
        temp_filepath = self.filepath + ".tmp"
        try:
            with open(temp_filepath, mode='w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=self.fieldnames, extrasaction='ignore')
                writer.writeheader()
                writer.writerows(self._data_cache)
            shutil.move(temp_filepath, self.filepath)
        except Exception as e:
            print(f"Error saving data to {self.filepath}: {e}")
            if os.path.exists(temp_filepath):
                try:
                    os.remove(temp_filepath)
                except OSError as rm_e:
                    print(f"Error removing temporary file {temp_filepath}: {rm_e}")


    async def create(self, item_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Creates a new item, adds it to the cache, and saves to the CSV file.
        Generates a UUID for 'id' if not provided. Ensures all fieldnames are present.
        """
        item_id = item_data.get('id', uuid.uuid4().hex)

        new_item_entry: Dict[str, Any] = {'id': item_id}
        for field in self.fieldnames:
            if field == 'id':
                continue
            new_item_entry[field] = str(item_data.get(field, "")) # Ensure all values are strings for CSV

        self._data_cache.append(new_item_entry)
        self._save_data()
        return new_item_entry

    async def read_all(self) -> List[Dict[str, Any]]:
        """Retrieves all items from the data cache."""
        return list(self._data_cache)

    async def read_one(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single item by ID from the data cache."""
        for item in self._data_cache:
            if item.get('id') == item_id:
                return item
        return None

    async def update(self, item_id: str, item_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Updates an item in the cache and saves to CSV.
        Ensures 'id' is preserved and all values are stringified for CSV.
        """
        item_index = -1
        for i, item in enumerate(self._data_cache):
            if item.get('id') == item_id:
                item_index = i
                break

        if item_index != -1:
            original_item = self._data_cache[item_index]

            # Create a new dict for the updated item, ensuring all fieldnames are present
            # and values are stringified for CSV.
            updated_item_entry: Dict[str, Any] = {'id': item_id} # Preserve original ID
            for field in self.fieldnames:
                if field == 'id':
                    continue
                # Take new value from item_data if present, else keep original, default to empty string
                updated_item_entry[field] = str(item_data.get(field, original_item.get(field, "")))

            self._data_cache[item_index] = updated_item_entry
            self._save_data()
            return updated_item_entry
        return None

    async def delete(self, item_id: str) -> bool:
        """Deletes an item from the cache and saves the change to CSV."""
        original_length = len(self._data_cache)
        self._data_cache = [item for item in self._data_cache if item.get('id') != item_id]

        if len(self._data_cache) < original_length:
            self._save_data()
            return True
        return False
