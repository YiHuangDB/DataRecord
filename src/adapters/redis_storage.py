"""
Redis-based storage adapter implementation.

This adapter stores data in a Redis server, using JSON strings for item serialization.
Each item is stored under a key prefixed with "item:".
Requires a running Redis instance.
"""
import uuid
import json
from typing import List, Optional, Dict, Any

import redis # type: ignore - For Redis client, ignore type if stubs not present

from src.core.storage_interface import StorageInterface

class RedisStorage(StorageInterface):
    """
    Implements StorageInterface using Redis for persistence.

    Items are serialized to JSON strings before being stored in Redis.
    Each item is stored under a unique key, typically "item:<uuid>".

    Attributes:
        redis_client: The Redis client instance.
        key_prefix (str): Prefix for all keys managed by this storage adapter.
    """
    def __init__(self, redis_url: str):
        """
        Initializes the RedisStorage adapter.

        Args:
            redis_url: The connection URL for the Redis server (e.g., "redis://localhost:6379/0").

        Raises:
            ConnectionError: If the Redis client cannot connect to the server specified by redis_url.
        """
        try:
            self.redis_client = redis.from_url(redis_url)
            self.redis_client.ping() # Verify connection during initialization
        except redis.exceptions.ConnectionError as e:
            # Re-raise as a standard ConnectionError or a custom one if preferred
            raise ConnectionError(f"Failed to connect to Redis at {redis_url}: {e}")

        self.key_prefix = "item:"
        print(f"RedisStorage initialized. Connected to Redis at {redis_url}")


    def _serialize(self, data: Dict[str, Any]) -> str:
        """Serializes a dictionary to a JSON string."""
        return json.dumps(data)

    def _deserialize(self, data_str: Optional[bytes]) -> Optional[Dict[str, Any]]:
        """
        Deserializes a JSON string (from bytes) from Redis back to a dictionary.
        Returns None if input is None or if deserialization fails.
        """
        if data_str is None:
            return None
        try:
            return json.loads(data_str.decode('utf-8'))
        except json.JSONDecodeError:
            # Log error or handle appropriately if data is not valid JSON
            print(f"Error: Could not deserialize data from Redis: {data_str[:100]}") # Log snippet
            return None

    async def create(self, item_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Creates a new item in Redis.
        Generates a UUID for 'id' if not provided. Item is stored as a JSON string.
        """
        item_id = item_data.get('id', uuid.uuid4().hex)
        item_data_with_id = {**item_data, "id": item_id} # Ensure ID is part of the stored data

        redis_key = self.key_prefix + item_id
        serialized_data = self._serialize(item_data_with_id)

        self.redis_client.set(redis_key, serialized_data)
        return item_data_with_id # Return the dict with the confirmed ID

    async def read_all(self) -> List[Dict[str, Any]]:
        """
        Retrieves all items from Redis that match the key prefix.
        Note: `KEYS` can be slow on large databases; `SCAN` is preferred in production.
        """
        items: List[Dict[str, Any]] = []
        # Using KEYS for simplicity. For production, consider SCAN.
        item_keys_bytes = self.redis_client.keys(self.key_prefix + "*")

        if not item_keys_bytes:
            return items

        # MGET can be more efficient if there are many keys
        serialized_items = self.redis_client.mget(item_keys_bytes)

        for serialized_data in serialized_items:
            deserialized_item = self._deserialize(serialized_data) # serialized_data can be None if a key disappeared
            if deserialized_item:
                items.append(deserialized_item)
        return items

    async def read_one(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single item by ID from Redis after deserializing its JSON string."""
        redis_key = self.key_prefix + item_id
        serialized_data = self.redis_client.get(redis_key)
        return self._deserialize(serialized_data)

    async def update(self, item_id: str, item_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Updates an existing item in Redis.
        The item is re-serialized to JSON. 'id' in item_data is ignored.
        """
        redis_key = self.key_prefix + item_id

        if not self.redis_client.exists(redis_key):
            return None

        # Ensure the ID from path is used, and it's part of the stored object
        item_data_with_id = {**item_data, "id": item_id}

        serialized_data = self._serialize(item_data_with_id)
        self.redis_client.set(redis_key, serialized_data)
        return item_data_with_id

    async def delete(self, item_id: str) -> bool:
        """Deletes an item by ID from Redis. Returns True if deletion occurred."""
        redis_key = self.key_prefix + item_id
        deleted_count = self.redis_client.delete(redis_key)
        return deleted_count > 0
