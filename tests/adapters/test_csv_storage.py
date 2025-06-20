import unittest
import os
import shutil
import asyncio
from src.adapters.csv_storage import CsvStorage

class TestCsvStorage(unittest.IsolatedAsyncioTestCase): # Use IsolatedAsyncioTestCase

    def setUp(self):
        self.test_dir = "temp_test_data_csv"
        self.test_file = os.path.join(self.test_dir, "test_items.csv")
        self.fieldnames = ['id', 'name', 'description', 'data']

        # Ensure the test directory is clean before each test
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        os.makedirs(self.test_dir, exist_ok=True)

        self.storage = CsvStorage(filepath=self.test_file, fieldnames=self.fieldnames)
        self.loop = asyncio.get_event_loop()

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    async def test_file_creation_and_header(self):
        self.assertTrue(os.path.exists(self.test_file))
        with open(self.test_file, 'r') as f:
            header = f.readline().strip()
            self.assertEqual(header, ",".join(self.fieldnames))

    async def test_create_item(self):
        item_data = {"name": "CSV Test Item", "description": "A test item for CSV", "data": "{'key': 'value'}"} # CSV stores data as string
        created_item = await self.storage.create(item_data)
        self.assertIsNotNone(created_item.get("id"))
        self.assertEqual(created_item["name"], item_data["name"])

        retrieved_item = await self.storage.read_one(created_item["id"])
        self.assertEqual(retrieved_item["id"], created_item["id"])
        self.assertEqual(retrieved_item["name"], created_item["name"])
        # Data from CSV is read as string, ensure it matches what was stored
        self.assertEqual(retrieved_item["data"], item_data["data"])


    async def test_read_all_items(self):
        item1_data = {"name": "CSV Item 1", "data": "{'val': 1}"}
        item2_data = {"name": "CSV Item 2", "data": "{'val': 2}"}
        await self.storage.create(item1_data)
        await self.storage.create(item2_data)

        all_items = await self.storage.read_all()
        self.assertEqual(len(all_items), 2)
        self.assertTrue(any(item['name'] == 'CSV Item 1' for item in all_items))
        self.assertTrue(any(item['name'] == 'CSV Item 2' for item in all_items))

    async def test_read_one_item(self):
        item_data = {"name": "Specific CSV Item", "data": "{}"}
        created_item = await self.storage.create(item_data)
        retrieved_item = await self.storage.read_one(created_item["id"])
        self.assertIsNotNone(retrieved_item)
        self.assertEqual(retrieved_item["name"], item_data["name"])

    async def test_read_nonexistent_item(self):
        retrieved_item = await self.storage.read_one("nonexistent-csv-id")
        self.assertIsNone(retrieved_item)

    async def test_update_item(self):
        item_data = {"name": "Original CSV Name", "description": "Original Desc", "data": "{'k':'v'}"}
        created_item = await self.storage.create(item_data)

        update_data = {"name": "Updated CSV Name", "description": "Updated Desc", "data": "{'new_k':'new_v'}"}
        updated_item = await self.storage.update(created_item["id"], update_data)

        self.assertIsNotNone(updated_item)
        self.assertEqual(updated_item["id"], created_item["id"]) # ID should not change
        self.assertEqual(updated_item["name"], update_data["name"])
        self.assertEqual(updated_item["description"], update_data["description"])
        self.assertEqual(updated_item["data"], update_data["data"])

        # Verify by reading again from storage
        retrieved_item = await self.storage.read_one(created_item["id"])
        self.assertEqual(retrieved_item["name"], update_data["name"])
        self.assertEqual(retrieved_item["data"], update_data["data"])


    async def test_update_nonexistent_item(self):
        update_data = {"name": "Non Existent Update"}
        updated_item = await self.storage.update("nonexistent-csv-id", update_data)
        self.assertIsNone(updated_item)

    async def test_delete_item(self):
        item_data = {"name": "To Be Deleted CSV", "data": "{}"}
        created_item = await self.storage.create(item_data)
        self.assertIsNotNone(await self.storage.read_one(created_item["id"]))

        deleted = await self.storage.delete(created_item["id"])
        self.assertTrue(deleted)
        self.assertIsNone(await self.storage.read_one(created_item["id"]))

        # Verify it's gone from cache and file (by reloading)
        new_storage_instance = CsvStorage(filepath=self.test_file, fieldnames=self.fieldnames)
        self.assertIsNone(await new_storage_instance.read_one(created_item["id"]))


    async def test_delete_nonexistent_item(self):
        deleted = await self.storage.delete("nonexistent-csv-id")
        self.assertFalse(deleted)

    async def test_data_persistence(self):
        item_data = {"name": "Persistent Item", "description": "Check persistence", "data": "{'persist': True}"}
        created_item = await self.storage.create(item_data)

        # Create a new storage instance with the same file
        new_storage_instance = CsvStorage(filepath=self.test_file, fieldnames=self.fieldnames)
        retrieved_item = await new_storage_instance.read_one(created_item["id"])

        self.assertIsNotNone(retrieved_item)
        self.assertEqual(retrieved_item["name"], item_data["name"])
        self.assertEqual(retrieved_item["description"], item_data["description"])
        self.assertEqual(retrieved_item["data"], item_data["data"])

    async def test_create_many_items(self):
        items_to_create_data = [
            {"name": "Batch CSV 1", "description": "First batch CSV", "data": {"b_csv": 1, "nested": {"n": "one"}}},
            {"name": "Batch CSV 2", "description": "Second batch CSV", "data": {"b_csv": 2, "other": True}},
        ]
        # This storage instance will write to self.test_file
        created_items = await self.storage.create_many(items_to_create_data)
        self.assertEqual(len(created_items), 2)

        for i, created_item in enumerate(created_items):
            self.assertIn("id", created_item)
            self.assertIsNotNone(created_item["id"])
            self.assertEqual(created_item["name"], items_to_create_data[i]["name"])
            # Verify data type for 'data' field if it was dict
            self.assertEqual(created_item["data"], items_to_create_data[i]["data"])

        # Verify persistence by loading with a new CsvStorage instance
        new_storage_instance = CsvStorage(filepath=self.test_file, fieldnames=self.fieldnames)
        # export_all on new instance should load and parse all data correctly
        all_persisted_items = await new_storage_instance.export_all()
        self.assertEqual(len(all_persisted_items), 2)

        retrieved_ids = {item["id"] for item in all_persisted_items}
        for created_item in created_items:
            self.assertIn(created_item["id"], retrieved_ids)
            # Further check content from new instance
            fetched_item = await new_storage_instance.read_one(created_item["id"])
            self.assertIsNotNone(fetched_item)
            self.assertEqual(fetched_item["name"], created_item["name"])
            # CsvStorage's read_one/export_all should deserialize 'data' from JSON string to dict
            self.assertEqual(fetched_item["data"], created_item["data"])


    async def test_export_all_items(self):
        # Test with no items
        exported_empty = await self.storage.export_all()
        self.assertEqual(len(exported_empty), 0)

        # Create some items - CsvStorage stores 'data' as JSON string but export_all should return dict
        item1_data = {"name": "Export CSV 1", "data": {"e_csv": 1, "is_dict": True}}
        item2_data = {"name": "Export CSV 2", "description": "With Desc", "data": {"e_csv": 2}}

        created1 = await self.storage.create(item1_data) # create method itself returns 'data' as dict
        created2 = await self.storage.create(item2_data)

        exported_items = await self.storage.export_all()
        self.assertEqual(len(exported_items), 2)

        exported_ids = {item["id"] for item in exported_items}
        self.assertIn(created1["id"], exported_ids)
        self.assertIn(created2["id"], exported_ids)

        # Verify content and that 'data' field is a dict
        found_item1 = next((item for item in exported_items if item["id"] == created1["id"]), None)
        self.assertIsNotNone(found_item1)
        self.assertEqual(found_item1["name"], created1["name"])
        self.assertIsInstance(found_item1["data"], dict) # Crucial for CSV test
        self.assertEqual(found_item1["data"], item1_data["data"])

        found_item2 = next((item for item in exported_items if item["id"] == created2["id"]), None)
        self.assertIsNotNone(found_item2)
        self.assertEqual(found_item2["name"], created2["name"])
        self.assertIsInstance(found_item2["data"], dict)
        self.assertEqual(found_item2["data"], item2_data["data"])
        self.assertEqual(found_item2["description"], item2_data["description"])


if __name__ == '__main__':
    unittest.main()
