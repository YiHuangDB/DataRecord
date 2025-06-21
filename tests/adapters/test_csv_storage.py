import unittest
import os
import shutil
import asyncio
import json # For checking data field if necessary
from typing import List, Dict, Any, Optional # Ensure all are imported
from src.adapters.csv_storage import CsvStorage
from src.core.query_models import FilterCondition, SortInstruction # Import query models


class TestCsvStorage(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self): # Changed to asyncSetUp
        self.test_dir = "temp_test_data_csv"
        self.test_file = os.path.join(self.test_dir, "test_items.csv")
        # Define fieldnames carefully, ensure 'data' is included if complex dicts are stored as JSON strings
        self.fieldnames = ['id', 'name', 'description', 'data']

        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        os.makedirs(self.test_dir, exist_ok=True)

        # Initialize storage, this will create an empty file with headers if it doesn't exist
        self.storage = CsvStorage(filepath=self.test_file, fieldnames=self.fieldnames)

        # Common test data - ensure data field is stringified if CsvStorage expects that for writing directly
        # However, our CsvStorage.create_many takes dicts and handles JSON conversion in _save_data
        self.test_items_data = [
            {"id": "csv-1", "name": "Apple", "description": "Crisp and red fruit", "data": {"color": "red", "category": "Fruit", "stock": 100}},
            {"id": "csv-2", "name": "Banana", "description": "Yellow and curved fruit", "data": {"color": "yellow", "category": "Fruit", "stock": 150}},
            {"id": "csv-3", "name": "Carrot", "description": "Orange and crunchy vegetable", "data": {"color": "orange", "category": "Vegetable", "stock": 80}},
            {"id": "csv-4", "name": "Dates", "description": "Brown and sweet fruit", "data": {"color": "brown", "category": "Fruit", "stock": 50}},
            {"id": "csv-5", "name": "Eggplant", "description": "Purple and smooth vegetable", "data": {"color": "purple", "category": "Vegetable", "stock": 70}},
        ]
        # Clear data cache and ensure file is empty or reflects only headers before creating many
        self.storage._data_cache.clear()
        self.storage._save_data() # Save empty cache to write just headers or truncate file

        await self.storage.create_many(self.test_items_data)
        # Reload data to ensure tests run against what's actually persisted and re-loaded,
        # including type conversions (e.g. 'data' field from JSON string to dict).
        self.storage._load_data()


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
        filters = [FilterCondition(field="name", operator="in", value="Apple,Dates,NoOne")] # Test string CSV for IN
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

    async def test_read_all_sort_description_asc_for_csv_specific_handling(self):
        # Test sorting on a field that might have varied string content
        # This relies on the _sort_items_in_memory helper's string comparison
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
