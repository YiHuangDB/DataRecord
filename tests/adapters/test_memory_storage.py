import unittest
import asyncio
from src.adapters.memory_storage import MemoryStorage

class TestMemoryStorage(unittest.IsolatedAsyncioTestCase): # Use IsolatedAsyncioTestCase for async methods

    def setUp(self):
        self.storage = MemoryStorage()
        self.loop = asyncio.get_event_loop()

    async def test_create_item(self):
        item_data = {"name": "Test Item", "description": "A test item", "data": {"key": "value"}}
        created_item = await self.storage.create(item_data)
        self.assertIsNotNone(created_item.get("id"))
        self.assertEqual(created_item["name"], item_data["name"])
        retrieved_item = await self.storage.read_one(created_item["id"])
        self.assertEqual(retrieved_item, created_item)

    async def test_read_all_items(self):
        item1_data = {"name": "Item 1", "data": {}}
        item2_data = {"name": "Item 2", "data": {}}
        await self.storage.create(item1_data)
        await self.storage.create(item2_data)
        all_items = await self.storage.read_all()
        self.assertEqual(len(all_items), 2)
        self.assertTrue(any(item['name'] == 'Item 1' for item in all_items))
        self.assertTrue(any(item['name'] == 'Item 2' for item in all_items))

    async def test_read_one_item(self):
        item_data = {"name": "Specific Item", "data": {}}
        created_item = await self.storage.create(item_data)
        retrieved_item = await self.storage.read_one(created_item["id"])
        self.assertIsNotNone(retrieved_item)
        self.assertEqual(retrieved_item["name"], item_data["name"])

    async def test_read_nonexistent_item(self):
        retrieved_item = await self.storage.read_one("nonexistent-id")
        self.assertIsNone(retrieved_item)

    async def test_update_item(self):
        item_data = {"name": "Original Name", "description": "Original Desc", "data": {"orig_key": "orig_val"}}
        created_item = await self.storage.create(item_data)
        update_data = {"name": "Updated Name", "description": "Updated Desc", "data": {"new_key": "new_val"}}
        updated_item = await self.storage.update(created_item["id"], update_data)

        self.assertIsNotNone(updated_item)
        self.assertEqual(updated_item["id"], created_item["id"])
        self.assertEqual(updated_item["name"], update_data["name"])
        self.assertEqual(updated_item["description"], update_data["description"])
        self.assertEqual(updated_item["data"], update_data["data"])

        # Verify by reading again
        retrieved_item = await self.storage.read_one(created_item["id"])
        self.assertEqual(retrieved_item["name"], update_data["name"])

    async def test_update_nonexistent_item(self):
        update_data = {"name": "Non Existent Update"}
        updated_item = await self.storage.update("nonexistent-id", update_data)
        self.assertIsNone(updated_item)

    async def test_delete_item(self):
        item_data = {"name": "To Be Deleted", "data": {}}
        created_item = await self.storage.create(item_data)
        self.assertIsNotNone(await self.storage.read_one(created_item["id"]))

        deleted = await self.storage.delete(created_item["id"])
        self.assertTrue(deleted)
        self.assertIsNone(await self.storage.read_one(created_item["id"]))

    async def test_delete_nonexistent_item(self):
        deleted = await self.storage.delete("nonexistent-id")
        self.assertFalse(deleted)

    async def test_create_many_items(self):
        items_to_create_data = [
            {"name": "Batch Mem 1", "description": "First batch memory item", "data": {"b_mem": 1}},
            {"name": "Batch Mem 2", "description": "Second batch memory item", "data": {"b_mem": 2}},
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
            self.assertEqual(fetched_item["data"], items_to_create_data[i]["data"])

    async def test_export_all_items(self):
        # Test with no items
        exported_empty = await self.storage.export_all()
        self.assertEqual(len(exported_empty), 0)

        # Create some items
        item1_data = {"name": "Export Mem 1", "data": {"e_mem": 1}}
        item2_data = {"name": "Export Mem 2", "data": {"e_mem": 2}}
        created1 = await self.storage.create(item1_data)
        created2 = await self.storage.create(item2_data)

        exported_items = await self.storage.export_all()
        self.assertEqual(len(exported_items), 2)

        # Check if created items are in exported_items (order might not be guaranteed for all backends)
        # For MemoryStorage, list(self._data.values()) order depends on dict's internal order,
        # which is insertion order for Python 3.7+.
        exported_ids = {item["id"] for item in exported_items}
        self.assertIn(created1["id"], exported_ids)
        self.assertIn(created2["id"], exported_ids)

        # Verify content (optional, but good)
        found_item1 = next((item for item in exported_items if item["id"] == created1["id"]), None)
        self.assertIsNotNone(found_item1)
        self.assertEqual(found_item1["name"], created1["name"])


if __name__ == '__main__':
    unittest.main()
