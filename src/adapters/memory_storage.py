"""
In-memory storage adapter implementation.

This adapter stores data in a Python dictionary in memory.
Data will be lost when the application instance terminates.
Suitable for testing, development, or scenarios where persistence is not required.
"""
import uuid
from typing import Optional, List, Dict, Any
from src.core.storage_interface import StorageInterface, PaginatedDbResponse

class MemoryStorage(StorageInterface):
    """
    Implements the StorageInterface using an in-memory dictionary.
    Items are stored in `self._data`.
    """
    def __init__(self):
        """Initializes the in-memory storage with an empty dictionary."""
        self._data: Dict[str, Dict[str, Any]] = {}
        print("MemoryStorage initialized.")

    async def create(self, item_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Creates a new item and stores it in the in-memory dictionary.
        An 'id' is generated using UUID if not provided in item_data.
        """
        item_id = item_data.get('id', uuid.uuid4().hex)
        new_item_entry = {**item_data, "id": item_id}
        self._data[item_id] = new_item_entry
        return new_item_entry

    async def read_all(self, offset: int = 0, limit: int = 100) -> PaginatedDbResponse:
        """
        Retrieves items from the in-memory storage with pagination.

        Args:
            offset: The number of items to skip before starting to collect the result set.
            limit: The maximum number of items to return.

        Returns:
            A dictionary conforming to PaginatedDbResponse, containing the
            paginated list of items, total count of all items in storage,
            the offset used, and the limit used.
        """
        all_items_list = list(self._data.values())
        total_count = len(all_items_list)

        paginated_items = all_items_list[offset : offset + limit]

        return {
            "items": paginated_items,
            "total_count": total_count,
            "offset": offset,
            "limit": limit,
        }

    async def read_one(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single item by its ID from the in-memory storage."""
        return self._data.get(item_id)

    async def update(self, item_id: str, item_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Updates an existing item in the in-memory storage.
        The 'id' field in item_data is ignored; item_id path parameter is canonical.
        """
        if item_id in self._data:
            updated_item = {**self._data[item_id], **item_data, "id": item_id}
            self._data[item_id] = updated_item
            return updated_item
        return None

    async def delete(self, item_id: str) -> bool:
        """Deletes an item by its ID from the in-memory storage."""
        if item_id in self._data:
            del self._data[item_id]
            return True
        return False
