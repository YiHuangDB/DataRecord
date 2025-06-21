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
import json
from typing import List, Optional, Dict, Any

from src.core.storage_interface import StorageInterface, PaginatedDbResponse
from src.core.query_models import FilterCondition, SortInstruction # Import query models
from .in_memory_query_utils import _filter_items_in_memory, _sort_items_in_memory # Import helpers

class CsvStorage(StorageInterface):
    """
    Implements the StorageInterface using a CSV file for persistence.

    Attributes:
        filepath (str): Path to the CSV file.
        fieldnames (List[str]): List of column headers for the CSV file.
        _data_cache (List[Dict[str, Any]]): In-memory cache of the CSV data.
                                          'data' field is stored as dict here.
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
            if 'id' not in fieldnames:
                print("Warning: 'id' not in fieldnames for CsvStorage. This might lead to issues.")
        self.fieldnames = fieldnames
        self._data_cache: List[Dict[str, Any]] = []

        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)

        self._load_data() # Loads data and parses 'data' field to dict
        print(f"CsvStorage initialized. Data file: {self.filepath}")

    def _load_data(self) -> None:
        """
        Loads data from the CSV file into `_data_cache`.
        'data' field (if JSON string) is parsed into a dictionary.
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

                temp_cache = []
                for row in reader:
                    # Ensure 'data' field is parsed from JSON string to dict
                    if 'data' in row and isinstance(row['data'], str):
                        try:
                            row['data'] = json.loads(row['data'])
                        except json.JSONDecodeError:
                            print(f"Warning: Could not parse JSON string for 'data' field in row ID: {row.get('id', 'N/A')}. Keeping as string.")
                    temp_cache.append(row)
                self._data_cache = temp_cache
        except FileNotFoundError:
            self._data_cache = []
        except Exception as e:
            print(f"Error loading data from {self.filepath}: {e}. Starting with an empty cache.")
            self._data_cache = []


    def _save_data(self) -> None:
        """
        Saves `_data_cache` to CSV. 'data' field (if dict) is serialized to JSON string.
        """
        temp_filepath = self.filepath + ".tmp"
        try:
            rows_to_write = []
            for item in self._data_cache:
                row_copy = item.copy()
                if 'data' in row_copy and isinstance(row_copy['data'], dict):
                    row_copy['data'] = json.dumps(row_copy['data'])
                # Ensure all values are strings for CSV writer, except for what DictWriter handles
                for key, value in row_copy.items():
                    if not isinstance(value, (str, int, float, bool)) and value is not None : # Check if simple type
                         row_copy[key] = str(value) # Fallback to string for complex types not handled (e.g. list if not data)
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
        Creates item, adds to cache (with 'data' as dict), saves to CSV (serializes 'data').
        """
        item_id = item_data.get('id', uuid.uuid4().hex)

        new_item_for_cache: Dict[str, Any] = {'id': item_id}
        for field in self.fieldnames:
            if field == 'id': continue
            if field == 'data' and field in item_data:
                new_item_for_cache[field] = item_data[field] # Keep as dict in cache
            else:
                # For other fields, ensure they are string or simple types for CSV compatibility if not handled by _save_data stringification
                new_item_for_cache[field] = item_data.get(field, "")


        self._data_cache.append(new_item_for_cache)
        self._save_data()

        return_item = item_data.copy()
        return_item['id'] = item_id
        return return_item


    async def read_all(
        self,
        filters: Optional[List[FilterCondition]] = None,
        sort_by: Optional[List[SortInstruction]] = None,
        offset: int = 0,
        limit: int = 100
    ) -> PaginatedDbResponse:
        """
        Retrieves items from CSV cache with filtering, sorting, and pagination.
        'data' field in items is expected to be a dictionary.
        """
        # self._load_data() # Typically not needed here as __init__ loads data.
                         # If CSV can change externally during app lifecycle, this might be needed.

        all_items_list = list(self._data_cache) # Operates on the in-memory cache

        # Apply filtering
        if filters:
            processed_items = _filter_items_in_memory(all_items_list, filters)
        else:
            processed_items = all_items_list

        # Apply sorting
        if sort_by:
            processed_items = _sort_items_in_memory(processed_items, sort_by)

        total_count = len(processed_items) # Count after filtering

        # Apply pagination
        paginated_items = processed_items[offset : offset + limit]

        return {
            "items": paginated_items, # Items here have 'data' as dict
            "total_count": total_count,
            "offset": offset,
            "limit": limit,
        }

    async def read_one(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves item by ID from cache. 'data' field is dict."""
        for item in self._data_cache:
            if item.get('id') == item_id:
                return item
        return None

    async def update(self, item_id: str, item_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Updates item in cache (with 'data' as dict), saves to CSV (serializes 'data')."""
        item_index = -1
        for i, item_in_cache in enumerate(self._data_cache):
            if item_in_cache.get('id') == item_id:
                item_index = i
                break

        if item_index != -1:
            current_item = self._data_cache[item_index]
            for field_key, field_value in item_data.items():
                if field_key == 'id': continue
                current_item[field_key] = field_value

            for fn_field in self.fieldnames: # Ensure all expected fields are present
                if fn_field not in current_item:
                    current_item[fn_field] = ""

            self._data_cache[item_index] = current_item
            self._save_data()
            return current_item
        return None

    async def delete(self, item_id: str) -> bool:
        """Deletes item from cache and saves change to CSV."""
        original_length = len(self._data_cache)
        self._data_cache = [item for item in self._data_cache if item.get('id') != item_id]

        if len(self._data_cache) < original_length:
            self._save_data()
            return True
        return False

    async def create_many(self, items_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Creates multiple items in cache (with 'data' as dict), saves to CSV once (serializes 'data')."""
        created_items_for_return = []

        for item_data_single in items_data:
            item_id = item_data_single.get('id', uuid.uuid4().hex)

            new_item_for_cache: Dict[str, Any] = {'id': item_id}
            for field in self.fieldnames:
                if field == 'id': continue
                if field == 'data' and field in item_data_single:
                    new_item_for_cache[field] = item_data_single[field] # Keep as dict in cache
                else:
                    # For other fields, ensure they are string or simple types.
                    # Using item_data_single.get(field, "") ensures that if a field defined in fieldnames
                    # is not in item_data_single, it gets a default empty string.
                    new_item_for_cache[field] = item_data_single.get(field, "")


            self._data_cache.append(new_item_for_cache)

            item_to_return = item_data_single.copy()
            item_to_return['id'] = item_id
            created_items_for_return.append(item_to_return)

        self._save_data()
        return created_items_for_return

    async def export_all(self) -> List[Dict[str, Any]]:
        """Exports all items from cache. 'data' field is dict."""
        return list(self._data_cache)
