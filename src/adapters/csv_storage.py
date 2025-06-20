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
import json # Ensure json is imported for handling the 'data' field
from typing import List, Optional, Dict, Any

from src.core.storage_interface import StorageInterface, PaginatedDbResponse

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
            # This was a pass before, but it's good practice to ensure 'id' is critical.
            # For now, assume config provides valid fieldnames including 'id'.
            if 'id' not in fieldnames:
                 # Or raise an error if 'id' is strictly required by design
                print("Warning: 'id' not in fieldnames for CsvStorage. This might lead to issues.")
        self.fieldnames = fieldnames
        self._data_cache: List[Dict[str, Any]] = []

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
            if self.fieldnames:
                 with open(self.filepath, 'w', newline='') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=self.fieldnames)
                    writer.writeheader()
            return

        try:
            with open(self.filepath, mode='r', newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                if reader.fieldnames and not all(f in reader.fieldnames for f in self.fieldnames):
                    print(f"Warning: Fieldnames in {self.filepath} differ from configured fieldnames.")

                # Deserialize 'data' field if it was stored as JSON string
                temp_cache = []
                for row in reader:
                    if 'data' in row and isinstance(row['data'], str):
                        try:
                            row['data'] = json.loads(row['data'])
                        except json.JSONDecodeError:
                            # If 'data' is not a valid JSON string, keep it as is or log error
                            print(f"Warning: Could not parse JSON string for 'data' field in row: {row['id']}")
                    temp_cache.append(row)
                self._data_cache = temp_cache
        except FileNotFoundError:
            self._data_cache = []
        except Exception as e:
            print(f"Error loading data from {self.filepath}: {e}. Starting with an empty cache.")
            self._data_cache = []


    def _save_data(self) -> None:
        """
        Saves the current state of `_data_cache` to the CSV file.
        Uses a temporary file for writing to prevent data corruption in case of errors,
        then replaces the original file. Serializes 'data' field to JSON string if it's a dict.
        """
        temp_filepath = self.filepath + ".tmp"
        try:
            # Prepare data for CSV: stringify 'data' field if it's a dict
            rows_to_write = []
            for item in self._data_cache:
                row_copy = item.copy()
                if 'data' in row_copy and isinstance(row_copy['data'], dict):
                    row_copy['data'] = json.dumps(row_copy['data'])
                rows_to_write.append(row_copy)

            with open(temp_filepath, mode='w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=self.fieldnames, extrasaction='ignore')
                writer.writeheader()
                writer.writerows(rows_to_write)
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
        The 'data' field is stored as a JSON string in CSV if it's a dictionary.
        """
        item_id = item_data.get('id', uuid.uuid4().hex)

        new_item_for_cache: Dict[str, Any] = {'id': item_id}
        for field in self.fieldnames:
            if field == 'id':
                continue
            # For CSV, all values are typically stored as strings.
            # 'data' field might be a dict, which should be JSON stringified before _save_data.
            if field == 'data' and field in item_data:
                new_item_for_cache[field] = item_data[field] # Keep as dict in cache, _save_data handles stringification
            else:
                new_item_for_cache[field] = str(item_data.get(field, ""))

        self._data_cache.append(new_item_for_cache)
        self._save_data() # _save_data will handle JSON stringification of 'data' field

        # Return item_data with ID, ensuring 'data' field is dict if it was input as dict
        return_item = item_data.copy()
        return_item['id'] = item_id
        return return_item


    async def read_all(self, offset: int = 0, limit: int = 100) -> PaginatedDbResponse:
        """
        Retrieves items from the CSV data cache with pagination.
        The cache reflects the content of the CSV file loaded at initialization.
        The 'data' field is parsed from JSON string to dict if necessary during load.
        """
        all_items_list = list(self._data_cache)
        total_count = len(all_items_list)

        paginated_items = all_items_list[offset : offset + limit]

        return {
            "items": paginated_items, # Items in cache should have 'data' as dict
            "total_count": total_count,
            "offset": offset,
            "limit": limit,
        }

    async def read_one(self, item_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a single item by ID from the data cache.
        'data' field is returned as a dict.
        """
        for item in self._data_cache: # self._data_cache items have 'data' as dict
            if item.get('id') == item_id:
                return item
        return None

    async def update(self, item_id: str, item_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Updates an item in the cache and saves to CSV.
        Ensures 'id' is preserved. 'data' field is handled as dict in cache,
        stringified to JSON on save.
        """
        item_index = -1
        for i, item_in_cache in enumerate(self._data_cache):
            if item_in_cache.get('id') == item_id:
                item_index = i
                break

        if item_index != -1:
            # Update the item in the cache.
            # The cache stores 'data' as dict. _save_data handles serialization.
            current_item = self._data_cache[item_index]
            for field_key, field_value in item_data.items():
                if field_key == 'id': continue # Don't update ID via payload
                current_item[field_key] = field_value # Update fields directly

            # Ensure all defined fieldnames are present, default if not from item_data
            for fn_field in self.fieldnames:
                if fn_field not in current_item:
                    current_item[fn_field] = "" # Default for missing fields

            self._data_cache[item_index] = current_item
            self._save_data() # Persist changes
            return current_item # Return the item as it is in cache (data as dict)
        return None

    async def delete(self, item_id: str) -> bool:
        """Deletes an item from the cache and saves the change to CSV."""
        original_length = len(self._data_cache)
        self._data_cache = [item for item in self._data_cache if item.get('id') != item_id]

        if len(self._data_cache) < original_length:
            self._save_data()
            return True
        return False

    async def create_many(self, items_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Creates multiple items in batch, adds them to cache, and saves to CSV once.
        'data' field is handled as dict in cache, serialized to JSON string on save.
        """
        created_items_for_return = []

        for item_data_single in items_data:
            item_id = item_data_single.get('id', uuid.uuid4().hex)

            new_item_for_cache: Dict[str, Any] = {'id': item_id}
            for field in self.fieldnames:
                if field == 'id':
                    continue
                if field == 'data' and field in item_data_single:
                     # Store 'data' as dict in cache, _save_data handles stringification
                    new_item_for_cache[field] = item_data_single[field]
                else:
                    new_item_for_cache[field] = str(item_data_single.get(field, ""))

            self._data_cache.append(new_item_for_cache)

            # Prepare item for the return list (should match how items are read)
            item_to_return = item_data_single.copy()
            item_to_return['id'] = item_id
            created_items_for_return.append(item_to_return)

        self._save_data() # Save all new items to CSV file once
        return created_items_for_return

    async def export_all(self) -> List[Dict[str, Any]]:
        """
        Exports all items from the CSV data cache.
        'data' field is returned as dict.
        """
        # self._load_data() might be needed if external changes are frequent and not reflected in cache.
        # For this app, cache is source of truth after init.
        return list(self._data_cache) # _data_cache items should have 'data' as dict due to _load_data logic
