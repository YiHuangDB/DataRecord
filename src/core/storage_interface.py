"""
Defines the abstract base class (interface) for all storage adapters.

This interface ensures that any storage backend implementation will provide a consistent
set of asynchronous CRUD (Create, Read, Update, Delete) operations for items.
Items are represented as dictionaries.
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any # Using Any for dict values for flexibility

class StorageInterface(ABC):
    """
    Abstract base class defining the contract for storage adapter implementations.
    All methods are asynchronous.
    """

    @abstractmethod
    async def create(self, item_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Creates a new item in the storage.

        Args:
            item_data: A dictionary containing the data for the new item.
                       The 'id' may or may not be present; the implementation
                       is responsible for generating an ID if not provided or
                       if the provided ID needs to be overridden.

        Returns:
            A dictionary representing the created item, including its final ID.
        """
        pass

    @abstractmethod
    async def read_all(self) -> List[Dict[str, Any]]:
        """
        Retrieves all items from the storage.

        Returns:
            A list of dictionaries, where each dictionary represents an item.
            Returns an empty list if no items are found.
        """
        pass

    @abstractmethod
    async def read_one(self, item_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a single item by its ID.

        Args:
            item_id: The unique identifier of the item to retrieve.

        Returns:
            A dictionary representing the found item, or None if no item
            with the given ID exists.
        """
        pass

    @abstractmethod
    async def update(self, item_id: str, item_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Updates an existing item identified by its ID.

        Args:
            item_id: The ID of the item to update.
            item_data: A dictionary containing the new data for the item.
                       This dictionary may contain all or a subset of item fields.
                       The 'id' field in item_data, if present, should be ignored
                       or validated against item_id.

        Returns:
            A dictionary representing the updated item, or None if no item
            with the given ID was found.
        """
        pass

    @abstractmethod
    async def delete(self, item_id: str) -> bool:
        """
        Deletes an item from the storage by its ID.

        Args:
            item_id: The ID of the item to delete.

        Returns:
            True if the item was successfully deleted, False otherwise (e.g., if
            the item was not found).
        """
        pass
