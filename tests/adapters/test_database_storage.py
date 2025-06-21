import unittest
import os
import shutil
import asyncio
from src.adapters.database_storage import DatabaseStorage, ItemDB # Import ItemDB as well for potential direct use
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session as SQLAlchemySession # To avoid confusion with local 'session' variables
from src.core.query_models import FilterCondition, SortInstruction # Import query models
from typing import List, Dict, Any, Optional # Ensure all are imported


class TestDatabaseStorage(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self): # Changed to asyncSetUp
        self.test_db_dir = "temp_test_data_db"
        self.db_url = f"sqlite:///{os.path.join(self.test_db_dir, 'test_items.db')}"

        if os.path.exists(self.test_db_dir):
            shutil.rmtree(self.test_db_dir)
        os.makedirs(self.test_db_dir, exist_ok=True)

        # Initialize storage, which creates tables
        self.storage = DatabaseStorage(db_url=self.db_url)

        # Clear any data from tables before each test
        # This is crucial for test isolation, especially if tearDownClass doesn't drop tables.
        session: SQLAlchemySession = self.storage.SessionLocal()
        try:
            # Assuming ItemDB is accessible for reflection or directly
            from src.adapters.database_storage import ItemDB as SQLiteItemDB
            session.query(SQLiteItemDB).delete()
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error clearing database table during setUp: {e}")
        finally:
            session.close()

        # Common test data
        self.test_items_data = [
            {"id": "sql-1", "name": "Apple", "description": "Crisp and red fruit", "data": {"color": "red", "category": "Fruit", "stock": 100}},
            {"id": "sql-2", "name": "Banana", "description": "Yellow and curved fruit", "data": {"color": "yellow", "category": "Fruit", "stock": 150}},
            {"id": "sql-3", "name": "Carrot", "description": "Orange and crunchy vegetable", "data": {"color": "orange", "category": "Vegetable", "stock": 80}},
            {"id": "sql-4", "name": "Dates", "description": "Brown and sweet fruit", "data": {"color": "brown", "category": "Fruit", "stock": 50}},
            {"id": "sql-5", "name": "Eggplant", "description": "Purple and smooth vegetable", "data": {"color": "purple", "category": "Vegetable", "stock": 70}},
        ]
        await self.storage.create_many(self.test_items_data)

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

    async def test_create_many_items(self):
        items_to_create_data = [
            {"name": "Batch DB 1", "description": "First batch SQLite item", "data": {"b_db": 1}},
            {"name": "Batch DB 2", "description": "Second batch SQLite item", "data": {"b_db": 2, "extra": True}},
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
            self.assertEqual(fetched_item["data"], items_to_create_data[i]["data"]) # JSON should be handled by SQLAlchemy

    async def test_export_all_items(self):
        # Test with no items
        exported_empty = await self.storage.export_all()
        self.assertEqual(len(exported_empty), 0)

        # Create some items
        item1_data = {"name": "Export DB 1", "data": {"e_db": 1}}
        item2_data = {"name": "Export DB 2", "description": "SQLite export test", "data": {"e_db": 2}}
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
        self.assertEqual(found_item1["data"], created1["data"]) # SQLAlchemy handles JSON type

        found_item2 = next((item for item in exported_items if item["id"] == created2["id"]), None)
        self.assertIsNotNone(found_item2)
        self.assertEqual(found_item2["name"], created2["name"])
        self.assertEqual(found_item2["description"], created2["description"])

    # --- Filtering Tests ---
    async def test_read_all_filter_eq_name(self):
        filters = [FilterCondition(field="name", operator="eq", value="Apple")]
        result = await self.storage.read_all(filters=filters)
        self.assertEqual(result["total_count"], 1)
        self.assertEqual(len(result["items"]), 1)
        self.assertEqual(result["items"][0]["name"], "Apple")

    async def test_read_all_filter_name_startswith(self):
        filters = [FilterCondition(field="name", operator="startswith", value="Ba")] # Banana
        result = await self.storage.read_all(filters=filters)
        self.assertEqual(result["total_count"], 1)
        self.assertEqual(result["items"][0]["name"], "Banana")

    async def test_read_all_filter_description_contains(self):
        filters = [FilterCondition(field="description", operator="contains", value="fruit")] # Apple, Banana, Dates
        result = await self.storage.read_all(filters=filters, limit=5)
        self.assertEqual(result["total_count"], 3)
        names = {item["name"] for item in result["items"]}
        self.assertIn("Apple", names)
        self.assertIn("Banana", names)
        self.assertIn("Dates", names)

    async def test_read_all_filter_in_name(self):
        filters = [FilterCondition(field="name", operator="in", value=["Apple", "Dates", "NoOne"])]
        result = await self.storage.read_all(filters=filters)
        self.assertEqual(result["total_count"], 2)
        names = {item["name"] for item in result["items"]}
        self.assertIn("Apple", names)
        self.assertIn("Dates", names)

    async def test_read_all_multiple_filters_and(self):
        filters = [
            FilterCondition(field="description", operator="contains", value="fruit"),
            FilterCondition(field="name", operator="startswith", value="Ba")
        ]
        result = await self.storage.read_all(filters=filters)
        self.assertEqual(result["total_count"], 1)
        self.assertEqual(result["items"][0]["name"], "Banana")

    async def test_read_all_filter_no_match(self):
        filters = [FilterCondition(field="name", operator="eq", value="NonExistentName")]
        result = await self.storage.read_all(filters=filters)
        self.assertEqual(result["total_count"], 0)

    # --- Sorting Tests ---
    async def test_read_all_sort_name_asc(self):
        sort_by = [SortInstruction(field="name", direction="asc")]
        result = await self.storage.read_all(sort_by=sort_by, limit=len(self.test_items_data))
        self.assertEqual(len(result["items"]), len(self.test_items_data))
        self.assertEqual(result["items"][0]["name"], "Apple")
        self.assertEqual(result["items"][-1]["name"], "Eggplant")

    async def test_read_all_sort_name_desc(self):
        sort_by = [SortInstruction(field="name", direction="desc")]
        result = await self.storage.read_all(sort_by=sort_by, limit=len(self.test_items_data))
        self.assertEqual(len(result["items"]), len(self.test_items_data))
        self.assertEqual(result["items"][0]["name"], "Eggplant")
        self.assertEqual(result["items"][-1]["name"], "Apple")

    async def test_read_all_sort_description_asc(self):
        sort_by = [SortInstruction(field="description", direction="asc")]
        result = await self.storage.read_all(sort_by=sort_by, limit=len(self.test_items_data))
        # Expected order by description (asc):
        # "Brown and sweet fruit" (Dates)
        # "Crisp and red fruit" (Apple)
        # "Orange and crunchy vegetable" (Carrot)
        # "Purple and smooth vegetable" (Eggplant)
        # "Yellow and curved fruit" (Banana)
        self.assertEqual(result["items"][0]["name"], "Dates")
        self.assertEqual(result["items"][1]["name"], "Apple")
        self.assertEqual(result["items"][2]["name"], "Carrot")
        self.assertEqual(result["items"][3]["name"], "Eggplant")
        self.assertEqual(result["items"][4]["name"], "Banana")

    # --- Combined Test ---
    async def test_read_all_combined_filter_sort_pagination(self):
        # Data: Apple, Banana, Carrot, Dates, Eggplant
        # Filter: description contains "vegetable" -> Carrot, Eggplant (2 items)
        filters = [FilterCondition(field="description", operator="contains", value="vegetable")]
        # Sort: name asc -> Carrot, Eggplant
        sort_by = [SortInstruction(field="name", direction="asc")]

        # Offset 0, Limit 1 from (Carrot, Eggplant) -> Should be Carrot
        result = await self.storage.read_all(filters=filters, sort_by=sort_by, offset=0, limit=1)

        self.assertEqual(result["total_count"], 2) # Total matching filter
        self.assertEqual(len(result["items"]), 1)
        self.assertEqual(result["items"][0]["name"], "Carrot")


if __name__ == '__main__':
    unittest.main()
