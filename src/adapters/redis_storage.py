"""
Redis-based storage adapter implementation.

This adapter stores data in a Redis server, using JSON strings for item serialization.
Each item is stored under a key prefixed with "item:".
Requires a running Redis instance.
"""
import uuid
import json
from typing import List, Optional, Dict, Any

import redis
from redis.exceptions import RedisError # Import RedisError
from src.core.storage_interface import StorageInterface, PaginatedDbResponse

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
            self.redis_client.ping()
        except redis.exceptions.ConnectionError as e: # More specific than just RedisError for connection
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
            print(f"Error: Could not deserialize data from Redis: {data_str[:100]}")
            return None

    async def create(self, item_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Creates a new item in Redis.
        Generates a UUID for 'id' if not provided. Item is stored as a JSON string.
        """
        item_id = item_data.get('id', uuid.uuid4().hex)
        item_data_with_id = {**item_data, "id": item_id}

        redis_key = self.key_prefix + item_id
        serialized_data = self._serialize(item_data_with_id)

        self.redis_client.set(redis_key, serialized_data)
        return item_data_with_id

    async def read_all(self, offset: int = 0, limit: int = 100) -> PaginatedDbResponse:
        """
        Retrieves items from Redis with pagination.
        Note: This implementation uses `KEYS` which can be inefficient for large datasets.
        Client-side sorting is applied for pagination consistency.

        Args:
            offset: The number of items to skip.
            limit: The maximum number of items to return.

        Returns:
            A dictionary conforming to PaginatedDbResponse, containing the
            paginated list of items, total count of matching items,
            the offset used, and the limit used.

        Raises:
            RuntimeError: If a Redis error occurs or an unexpected error happens.
        """
        try:
            item_keys_bytes = self.redis_client.keys(self.key_prefix + "*")
            item_keys = sorted([key.decode('utf-8') for key in item_keys_bytes])

            total_count = len(item_keys)

            if total_count == 0:
                return {"items": [], "total_count": 0, "offset": offset, "limit": limit}

            paginated_keys_to_fetch = item_keys[offset : offset + limit]

            items_list: List[Dict[str, Any]] = []
            if paginated_keys_to_fetch:
                items_data_str = self.redis_client.mget(paginated_keys_to_fetch)

                deserialized_items = [self._deserialize(item_str) for item_str in items_data_str if item_str is not None]
                items_list = [item for item in deserialized_items if item is not None]

            return {
                "items": items_list,
                "total_count": total_count,
                "offset": offset,
                "limit": limit,
            }
        except RedisError as e:
            print(f"Error reading items from Redis: {e}")
            raise RuntimeError(f"Error reading items from Redis: {e}")
        except Exception as e:
            print(f"An unexpected error occurred in RedisStorage.read_all: {e}")
            raise RuntimeError(f"An unexpected error occurred in RedisStorage.read_all: {e}")

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

        item_data_with_id = {**item_data, "id": item_id}

        serialized_data = self._serialize(item_data_with_id)
        self.redis_client.set(redis_key, serialized_data)
        return item_data_with_id

    async def delete(self, item_id: str) -> bool:
        """Deletes an item by ID from Redis. Returns True if deletion occurred."""
        redis_key = self.key_prefix + item_id
        deleted_count = self.redis_client.delete(redis_key)
        return deleted_count > 0

    async def create_many(self, items_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Creates multiple items in batch in Redis using a pipeline."""
        created_items = []
        if not items_data:
            return []

        try:
            pipe = self.redis_client.pipeline()
            for item_data in items_data:
                item_id = item_data.get('id', uuid.uuid4().hex)

                full_item_data = item_data.copy()
                full_item_data['id'] = item_id

                redis_key = self.key_prefix + item_id
                serialized_data = self._serialize(full_item_data)

                pipe.set(redis_key, serialized_data)
                created_items.append(full_item_data)

            pipe.execute()
            return created_items
        except RedisError as e:
            # Log the error, e.g., print(f"RedisError during create_many: {e}")
            raise RuntimeError(f"Error bulk creating items in Redis: {e}")
        except Exception as e:
            # Log the error, e.g., print(f"Unexpected error during create_many: {e}")
            raise RuntimeError(f"An unexpected error occurred during Redis create_many: {e}")

    async def export_all(self) -> List[Dict[str, Any]]:
        """
        Exports all items from Redis.
        Uses KEYS and MGET. Warning: KEYS can be slow on large databases.
        """
        try:
            item_keys_bytes = self.redis_client.keys(self.key_prefix + "*")

            if not item_keys_bytes:
                return []

            # item_keys = [key.decode('utf-8') for key in item_keys_bytes] # Not needed if mget takes bytes

            items_data_str = self.redis_client.mget(item_keys_bytes) # mget can take list of bytes

            exported_items: List[Dict[str, Any]] = []
            for item_str in items_data_str:
                if item_str is not None:
                    deserialized_item = self._deserialize(item_str)
                    if deserialized_item is not None:
                        exported_items.append(deserialized_item)

            return exported_items
        except RedisError as e:
            # Log the error, e.g., print(f"RedisError during export_all: {e}")
            raise RuntimeError(f"Error exporting all items from Redis: {e}")
        except Exception as e:
            # Log the error, e.g., print(f"Unexpected error during export_all: {e}")
            raise RuntimeError(f"An unexpected error occurred during Redis export_all: {e}")
