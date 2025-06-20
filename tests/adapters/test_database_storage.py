import unittest
import os
import shutil
import asyncio
from src.adapters.database_storage import DatabaseStorage, ItemDB # Import ItemDB as well for potential direct use
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

class TestDatabaseStorage(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.test_db_dir = "temp_test_data_db"
        # Ensure the directory name is unique enough or cleaned properly
        self.db_url = f"sqlite:///{os.path.join(self.test_db_dir, 'test_items.db')}"

        # Clean up before test
        if os.path.exists(self.test_db_dir):
            shutil.rmtree(self.test_db_dir)
        os.makedirs(self.test_db_dir, exist_ok=True)

        self.storage = DatabaseStorage(db_url=self.db_url)
        # For direct DB inspection if needed, though tests should use storage interface
        self.engine = create_engine(self.db_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def tearDown(self):
        # Close connections and release resources held by SQLAlchemy engine
        if hasattr(self.storage, 'engine') and self.storage.engine is not None:
            self.storage.engine.dispose()
        if hasattr(self, 'engine') and self.engine is not None: # Also dispose engine used for direct inspection
            self.engine.dispose()

        if os.path.exists(self.test_db_dir):
            shutil.rmtree(self.test_db_dir)

    async def test_create_item(self):
        item_data = {"name": "DB Test Item", "description": "A test item for DB", "data": {"key": "value"}}
        created_item = await self.storage.create(item_data)
        self.assertIsNotNone(created_item.get("id"))
        self.assertEqual(created_item["name"], item_data["name"])

        retrieved_item = await self.storage.read_one(created_item["id"])
        self.assertEqual(retrieved_item, created_item)

    async def test_read_all_items(self):
        item1_data = {"name": "DB Item 1", "data": {"val": 1}}
        item2_data = {"name": "DB Item 2", "data": {"val": 2}}
        await self.storage.create(item1_data)
        await self.storage.create(item2_data)

        all_items = await self.storage.read_all()
        self.assertEqual(len(all_items), 2)
        self.assertTrue(any(item['name'] == 'DB Item 1' for item in all_items))
        self.assertTrue(any(item['name'] == 'DB Item 2' for item in all_items))

    async def test_read_one_item(self):
        item_data = {"name": "Specific DB Item", "data": {}}
        created_item = await self.storage.create(item_data)
        retrieved_item = await self.storage.read_one(created_item["id"])
        self.assertIsNotNone(retrieved_item)
        self.assertEqual(retrieved_item["name"], item_data["name"])

    async def test_read_nonexistent_item(self):
        retrieved_item = await self.storage.read_one("nonexistent-db-id")
        self.assertIsNone(retrieved_item)

    async def test_update_item(self):
        item_data = {"name": "Original DB Name", "description": "Original Desc", "data": {"orig_key": "orig_val"}}
        created_item = await self.storage.create(item_data)

        update_data = {"name": "Updated DB Name", "description": "Updated Desc", "data": {"new_key": "new_val"}}
        updated_item = await self.storage.update(created_item["id"], update_data)

        self.assertIsNotNone(updated_item)
        self.assertEqual(updated_item["id"], created_item["id"]) # ID should not change
        self.assertEqual(updated_item["name"], update_data["name"])
        self.assertEqual(updated_item["description"], update_data["description"])
        self.assertEqual(updated_item["data"], update_data["data"])

        retrieved_item = await self.storage.read_one(created_item["id"])
        self.assertEqual(retrieved_item["name"], update_data["name"])

    async def test_update_nonexistent_item(self):
        update_data = {"name": "Non Existent DB Update"}
        updated_item = await self.storage.update("nonexistent-db-id", update_data)
        self.assertIsNone(updated_item)

    async def test_delete_item(self):
        item_data = {"name": "To Be Deleted DB", "data": {}}
        created_item = await self.storage.create(item_data)
        self.assertIsNotNone(await self.storage.read_one(created_item["id"]))

        deleted = await self.storage.delete(created_item["id"])
        self.assertTrue(deleted)
        self.assertIsNone(await self.storage.read_one(created_item["id"]))

    async def test_delete_nonexistent_item(self):
        deleted = await self.storage.delete("nonexistent-db-id")
        self.assertFalse(deleted)

    async def test_data_persistence(self):
        item_data = {"name": "Persistent DB Item", "description": "Check DB persistence", "data": {"persist_db": True}}
        created_item = await self.storage.create(item_data)

        # Dispose of the current engine to ensure data is flushed and connections closed
        self.storage.engine.dispose()

        # Create a new storage instance with the same DB URL
        new_storage_instance = DatabaseStorage(db_url=self.db_url)
        retrieved_item = await new_storage_instance.read_one(created_item["id"])

        self.assertIsNotNone(retrieved_item)
        self.assertEqual(retrieved_item["name"], item_data["name"])
        self.assertEqual(retrieved_item["description"], item_data["description"])
        self.assertEqual(retrieved_item["data"], item_data["data"])
        new_storage_instance.engine.dispose()


if __name__ == '__main__':
    unittest.main()
