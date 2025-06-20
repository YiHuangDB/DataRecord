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

if __name__ == '__main__':
    unittest.main()
