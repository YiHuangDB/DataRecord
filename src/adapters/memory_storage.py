"""
In-memory storage adapter implementation.

This adapter stores data in a Python dictionary in memory.
Data will be lost when the application instance terminates.
Suitable for testing, development, or scenarios where persistence is not required.
"""
import uuid
from typing import Optional, List, Dict, Any
from src.core.storage_interface import StorageInterface

class MemoryStorage(StorageInterface):
    """
    Implements the StorageInterface using an in-memory dictionary.
    Items are stored in `self._data`.
    """
    def __init__(self):
        """Initializes the in-memory storage with an empty dictionary."""
        self._data: Dict[str, Dict[str, Any]] = {}
        print("MemoryStorage initialized.") # Confirmation message

    async def create(self, item_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Creates a new item and stores it in the in-memory dictionary.
        An 'id' is generated using UUID if not provided in item_data.
        """
        item_id = item_data.get('id', uuid.uuid4().hex) # Use provided ID or generate one
        # Ensure the ID is part of the item_data being stored
        new_item_entry = {**item_data, "id": item_id}
        self._data[item_id] = new_item_entry
        return new_item_entry

    async def read_all(self) -> List[Dict[str, Any]]:
        """Retrieves all items from the in-memory storage."""
        return list(self._data.values())

    async def read_one(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single item by its ID from the in-memory storage."""
        return self._data.get(item_id)

    async def update(self, item_id: str, item_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Updates an existing item in the in-memory storage.
        The 'id' field in item_data is ignored; item_id path parameter is canonical.
        """
        if item_id in self._data:
            # Preserve original ID, update other fields from item_data
            updated_item = {**self._data[item_id], **item_data, "id": item_id}
            self._data[item_id] = updated_item
            return updated_item
        return None

    async def delete(self, item_id: str) -> bool:
        """Deletes an item by its ID from the in-memory storage."""
        if item_id in self.data:
            del self.data[item_id]
            return True
        return False
