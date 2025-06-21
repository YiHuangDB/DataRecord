"""
In-memory storage adapter implementation.

This adapter stores data in a Python dictionary in memory.
Data will be lost when the application instance terminates.
Suitable for testing, development, or scenarios where persistence is not required.
"""
import uuid
from typing import Optional, List, Dict, Any
from src.core.storage_interface import StorageInterface, PaginatedDbResponse
from src.core.query_models import FilterCondition, SortInstruction # Import query models
from .in_memory_query_utils import _filter_items_in_memory, _sort_items_in_memory # Import helpers

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

    async def read_all(
        self,
        filters: Optional[List[FilterCondition]] = None,
        sort_by: Optional[List[SortInstruction]] = None,
        offset: int = 0,
        limit: int = 100
    ) -> PaginatedDbResponse:
        """
        Retrieves items from the in-memory storage with optional filtering, sorting, and pagination.

        Args:
            filters: A list of FilterCondition dictionaries to apply.
            sort_by: A list of SortInstruction dictionaries for ordering results.
            offset: The number of items to skip.
            limit: The maximum number of items to return.

        Returns:
            A dictionary conforming to PaginatedDbResponse.
        """
        # In Python 3.7+, dict values are ordered by insertion.
        # If specific pre-sorting is needed before other operations, convert to list earlier.
        all_items_list = list(self._data.values())

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

    async def create_many(self, items_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Creates multiple items in batch in the in-memory storage.
        IDs are generated if not provided.
        """
        created_items = []
        for item_data in items_data:
            item_id = item_data.get('id', uuid.uuid4().hex)
            new_item = item_data.copy()
            new_item['id'] = item_id

            self._data[item_id] = new_item
            created_items.append(new_item)
        return created_items

    async def export_all(self) -> List[Dict[str, Any]]:
        """
        Exports all items from the in-memory storage.
        Returns a list of all stored items.
        """
        return list(self._data.values())
