import unittest
import os
import asyncio
import json # For comparing dict data which might be stored as JSON string
from src.adapters.redis_storage import RedisStorage
import redis # For redis.exceptions.ConnectionError

class TestRedisStorage(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.redis_url = os.getenv("TEST_REDIS_URL", "redis://localhost:6379/9")
        # Ensure that this URL points to a test/QA Redis instance and database number

        self.storage = RedisStorage(redis_url=self.redis_url)

        try:
            # Ping to check connection and then flush the specific test database.
            # This is critical to ensure tests are isolated and don't pollute other data.
            self.storage.redis_client.ping()
            self.storage.redis_client.flushdb()
        except redis.exceptions.ConnectionError:
            # If Redis is not available, skip all tests in this class.
            self.skipTest(f"Redis server not available at {self.redis_url}. Skipping Redis tests.")
        except Exception as e: # Catch other potential Redis errors during setup
             self.skipTest(f"Failed to connect or flush Redis DB {self.redis_url}: {e}. Skipping Redis tests.")


    def tearDown(self):
        # Clean up the test database after tests run, if client exists.
        if hasattr(self.storage, 'redis_client') and self.storage.redis_client:
            try:
                self.storage.redis_client.flushdb()
            except redis.exceptions.ConnectionError:
                # If connection is lost by teardown, there's not much to do
                pass

    async def test_create_item(self):
        item_data = {"name": "Redis Test Item", "description": "A test item for Redis", "data": {"key": "value"}}
        created_item = await self.storage.create(item_data)
        self.assertIsNotNone(created_item.get("id"))
        self.assertEqual(created_item["name"], item_data["name"])

        retrieved_item = await self.storage.read_one(created_item["id"])
        self.assertIsNotNone(retrieved_item)
        self.assertEqual(retrieved_item["id"], created_item["id"])
        self.assertEqual(retrieved_item["name"], item_data["name"])
        # Data in Redis is stored as JSON string, then deserialized.
        # So, comparing dicts directly should work.
        self.assertEqual(retrieved_item["data"], item_data["data"])


    async def test_read_all_items(self):
        item1_data = {"name": "Redis Item 1", "data": {"val": 1}}
        item2_data = {"name": "Redis Item 2", "data": {"val": 2}}
        await self.storage.create(item1_data)
        await self.storage.create(item2_data)

        all_items = await self.storage.read_all()
        self.assertEqual(len(all_items), 2)
        # Order is not guaranteed from Redis KEYS, so check for presence
        names_retrieved = {item['name'] for item in all_items}
        self.assertIn("Redis Item 1", names_retrieved)
        self.assertIn("Redis Item 2", names_retrieved)


    async def test_read_one_item(self):
        item_data = {"name": "Specific Redis Item", "data": {}}
        created_item = await self.storage.create(item_data)
        retrieved_item = await self.storage.read_one(created_item["id"])
        self.assertIsNotNone(retrieved_item)
        self.assertEqual(retrieved_item["name"], item_data["name"])

    async def test_read_nonexistent_item(self):
        retrieved_item = await self.storage.read_one("nonexistent-redis-id")
        self.assertIsNone(retrieved_item)

    async def test_update_item(self):
        item_data = {"name": "Original Redis Name", "description": "Original Desc", "data": {"orig_key": "orig_val"}}
        created_item = await self.storage.create(item_data)

        update_data = {"name": "Updated Redis Name", "description": "Updated Desc", "data": {"new_key": "new_val"}}
        updated_item = await self.storage.update(created_item["id"], update_data)

        self.assertIsNotNone(updated_item)
        self.assertEqual(updated_item["id"], created_item["id"])
        self.assertEqual(updated_item["name"], update_data["name"])
        self.assertEqual(updated_item["description"], update_data["description"])
        self.assertEqual(updated_item["data"], update_data["data"])

        retrieved_item = await self.storage.read_one(created_item["id"])
        self.assertEqual(retrieved_item["name"], update_data["name"])


    async def test_update_nonexistent_item(self):
        update_data = {"name": "Non Existent Update"}
        updated_item = await self.storage.update("nonexistent-redis-id", update_data)
        self.assertIsNone(updated_item)

    async def test_delete_item(self):
        item_data = {"name": "To Be Deleted Redis", "data": {}}
        created_item = await self.storage.create(item_data)
        self.assertIsNotNone(await self.storage.read_one(created_item["id"]))

        deleted = await self.storage.delete(created_item["id"])
        self.assertTrue(deleted)
        self.assertIsNone(await self.storage.read_one(created_item["id"]))

    async def test_delete_nonexistent_item(self):
        deleted = await self.storage.delete("nonexistent-redis-id")
        self.assertFalse(deleted)

    async def test_create_many_items(self):
        items_to_create_data = [
            {"name": "Batch Redis 1", "description": "First batch Redis", "data": {"b_redis": 1, "is_complex": True}},
            {"name": "Batch Redis 2", "description": "Second batch Redis", "data": {"b_redis": 2, "value": None}},
        ]
        created_items = await self.storage.create_many(items_to_create_data)
        self.assertEqual(len(created_items), 2)
        for i, created_item in enumerate(created_items):
            self.assertIn("id", created_item)
            self.assertIsNotNone(created_item["id"])
            self.assertEqual(created_item["name"], items_to_create_data[i]["name"])
            # Verify item is actually stored
            fetched_item = await self.storage.read_one(created_item["id"])
            self.assertIsNotNone(fetched_item)
            self.assertEqual(fetched_item["name"], items_to_create_data[i]["name"])
            self.assertEqual(fetched_item["description"], items_to_create_data[i]["description"])
            self.assertEqual(fetched_item["data"], items_to_create_data[i]["data"]) # Redis adapter handles JSON serialization

    async def test_export_all_items(self):
        # Test with no items
        exported_empty = await self.storage.export_all()
        self.assertEqual(len(exported_empty), 0)

        # Create some items
        item1_data = {"name": "Export Redis 1", "data": {"e_redis": 1}}
        item2_data = {"name": "Export Redis 2", "description": "Redis export", "data": {"e_redis": 2}}
        created1 = await self.storage.create(item1_data)
        created2 = await self.storage.create(item2_data)

        exported_items = await self.storage.export_all()
        self.assertEqual(len(exported_items), 2)

        exported_ids = {item["id"] for item in exported_items}
        self.assertIn(created1["id"], exported_ids)
        self.assertIn(created2["id"], exported_ids)

        found_item1 = next((item for item in exported_items if item["id"] == created1["id"]), None)
        self.assertIsNotNone(found_item1)
        self.assertEqual(found_item1["name"], created1["name"])
        self.assertEqual(found_item1["data"], created1["data"])

        found_item2 = next((item for item in exported_items if item["id"] == created2["id"]), None)
        self.assertIsNotNone(found_item2)
        self.assertEqual(found_item2["name"], created2["name"])
        self.assertEqual(found_item2["description"], created2["description"])


if __name__ == '__main__':
    unittest.main()
