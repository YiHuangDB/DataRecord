import unittest
from typing import List, Optional, Dict, Any
import asyncio
import uuid

from fastapi import HTTPException
from fastapi.testclient import TestClient

from src.core.models import Item, PaginatedResponseModel # Ensure PaginatedResponseModel is imported
from src.core.storage_interface import StorageInterface, PaginatedDbResponse
from src.core.query_models import FilterCondition, SortInstruction # Import query models
from src.api import routes
# Import the in-memory helper functions
from src.adapters.in_memory_query_utils import _filter_items_in_memory, _sort_items_in_memory


# MockStorage implementation
class MockStorage(StorageInterface):
    def __init__(self):
        self.data: Dict[str, Dict[str, Any]] = {}
        self.counter: int = 0 # Counter for generating simple IDs if needed
        self._keys_in_order: List[str] = [] # To maintain insertion order for consistent tests

    async def create(self, item_data: Dict[str, Any]) -> Dict[str, Any]:
        item_id = item_data.get("id")
        if not item_id:
            self.counter += 1
            item_id = str(self.counter) # Generate ID if not provided

        final_item_data = item_data.copy()
        final_item_data["id"] = item_id

        if new_id not in self.data: # Add to order list only if it's a new key
            self._keys_in_order.append(item_id)
        self.data[item_id] = final_item_data
        return final_item_data

    async def read_all(
        self,
        filters: Optional[List[FilterCondition]] = None,
        sort_by: Optional[List[SortInstruction]] = None,
        offset: int = 0,
        limit: int = 100
    ) -> PaginatedDbResponse:
        # Ensure items are retrieved in a consistent order if _keys_in_order is used
        if hasattr(self, '_keys_in_order') and self._keys_in_order:
            all_items = [self.data[key] for key in self._keys_in_order if key in self.data]
        else:
            all_items = list(self.data.values())

        # Apply filtering
        processed_items = _filter_items_in_memory(all_items, filters)

        # Apply sorting
        processed_items = _sort_items_in_memory(processed_items, sort_by)

        total_count = len(processed_items) # Count after filtering

        # Apply pagination
        offset = max(0, offset)
        limit = max(0, limit) # Ensure limit is not negative
        paginated_items_list = processed_items[offset : offset + limit]

        return {
            "items": paginated_items_list,
            "total_count": total_count,
            "offset": offset,
            "limit": limit
        }

    async def read_one(self, item_id: str) -> Optional[Dict[str, Any]]:
        return self.data.get(item_id)

    async def update(self, item_id: str, item_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if item_id in self.data:
            updated_record = self.data[item_id].copy()
            updated_record.update(item_data)
            updated_record["id"] = item_id
            self.data[item_id] = updated_record
            return updated_record
        return None

    async def delete(self, item_id: str) -> bool:
        if item_id in self.data:
            del self.data[item_id]
            if item_id in self._keys_in_order:
                self._keys_in_order.remove(item_id)
            return True
        return False

    async def create_many(self, items_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        created_items_list = []
        for item_data_single in items_data:
            item_id = item_data_single.get('id', uuid.uuid4().hex)

            new_item = item_data_single.copy()
            new_item['id'] = item_id

            self.data[item_id] = new_item
            if new_item['id'] not in self._keys_in_order:
                self._keys_in_order.append(new_item['id'])
            created_items_list.append(new_item)
        return created_items_list

    async def export_all(self) -> List[Dict[str, Any]]:
        return [self.data[key] for key in self._keys_in_order if key in self.data]


class TestApiRoutes(unittest.TestCase):

    def setUp(self): # Changed to standard setUp, async operations will use asyncio.run
        self.mock_storage = MockStorage()
        routes.storage_adapter = self.mock_storage
        self.client = TestClient(routes.app)

        # Common test data setup
        self.test_api_items_data = [
            {"id": "api-1", "name": "Alpha Test", "description": "First item for API", "data": {"value": 100, "group": "A"}},
            {"id": "api-2", "name": "Beta Test", "description": "Second item", "data": {"value": 200, "group": "B"}},
            {"id": "api-3", "name": "Gamma Query", "description": "Third item with Gamma", "data": {"value": 150, "group": "A"}},
            {"id": "api-4", "name": "Delta Test", "description": "Fourth item", "data": {"value": 250, "group": "B"}},
            {"id": "api-5", "name": "Alpha Another", "description": "Fifth item", "data": {"value": 120, "group": "A"}},
        ]
        # Clear and populate for each test method to ensure isolation
        self.mock_storage.data.clear()
        if hasattr(self.mock_storage, '_keys_in_order'): self.mock_storage._keys_in_order.clear()
        asyncio.run(self.mock_storage.create_many(self.test_api_items_data))


    def test_create_item_api(self):
        item_payload = {"name": "API New Item", "description": "Testing creation", "data": {"key": "val"}}
        response = self.client.post("/items", json=item_payload)
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertIsNotNone(response_data.get("id"))
        self.assertEqual(response_data["name"], item_payload["name"])
        created_id = response_data["id"]
        stored_item = asyncio.run(self.mock_storage.read_one(created_id))
        self.assertIsNotNone(stored_item)
        self.assertEqual(stored_item["name"], item_payload["name"])

    # --- Pagination Tests (existing) ---
    def test_read_items_paginated_default_with_items(self):
        # Data is pre-populated by setUp
        response = self.client.get("/items")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["items"]), 5) # Should match self.test_api_items_data
        self.assertEqual(data["total_count"], 5)
        self.assertEqual(data["offset"], 0)
        self.assertEqual(data["limit"], 10)
        self.assertEqual(data["items"][0]["name"], "Alpha Test") # Based on _keys_in_order

    # --- New Filter and Sort API Tests ---
    def test_read_items_api_filter_name_contains(self):
        response = self.client.get("/items?name__contains=Test")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # Expected: Alpha Test, Beta Test, Delta Test (3 items)
        self.assertEqual(data["total_count"], 3)
        self.assertEqual(len(data["items"]), 3)
        names = {item["name"] for item in data["items"]}
        self.assertIn("Alpha Test", names)
        self.assertIn("Beta Test", names)
        self.assertIn("Delta Test", names)

    def test_read_items_api_filter_description_startswith(self):
        # Test data has "First item for API", "Second item", "Third item with Gamma", "Fourth item", "Fifth item"
        # "description__startswith=F" should match "First" and "Fourth" and "Fifth"
        response = self.client.get("/items?description__startswith=F")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total_count"], 3)
        names = {item["name"] for item in data["items"]}
        self.assertIn("Alpha Test", names) # "First item for API"
        self.assertIn("Delta Test", names) # "Fourth item"
        self.assertIn("Alpha Another", names) # "Fifth item"

    def test_read_items_api_sort_name_desc(self):
        response = self.client.get("/items?sort_by=-name")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["items"]), 5) # All 5 items from setup
        self.assertEqual(data["items"][0]["name"], "Gamma Query") # Gamma Query is last alphabetically
        self.assertEqual(data["items"][1]["name"], "Delta Test")
        self.assertEqual(data["items"][2]["name"], "Beta Test")
        self.assertEqual(data["items"][3]["name"], "Alpha Test")
        self.assertEqual(data["items"][4]["name"], "Alpha Another")


    def test_read_items_api_filter_sort_paginate(self):
        # Filter: description contains "item" -> Alpha Test, Beta Test, Gamma Query, Delta Test, Alpha Another (all 5)
        # Sort: name ascending
        # Offset 1, Limit 2
        # Expected order of names: Alpha Another, Alpha Test, Beta Test, Delta Test, Gamma Query
        # After offset 1, limit 2: "Alpha Test", "Beta Test"
        response = self.client.get("/items?description__contains=item&sort_by=name&offset=1&limit=2")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["total_count"], 5) # All 5 items contain "item" in description
        self.assertEqual(len(data["items"]), 2)
        self.assertEqual(data["items"][0]["name"], "Alpha Test")
        self.assertEqual(data["items"][1]["name"], "Beta Test")
        self.assertEqual(data["offset"], 1)
        self.assertEqual(data["limit"], 2)

    def test_read_items_api_invalid_filter_operator_is_skipped(self):
        # Current _parse_query_params and adapter _filter_items_in_memory will skip/ignore unknown operators
        response = self.client.get("/items?name__unknownop=Test")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total_count"], 5) # Filter is ignored, all items returned (within default limit)
        self.assertEqual(len(data["items"]), 5) # Default limit is 10, 5 items in total

    # --- Batch and Export API Tests (from previous step, ensure they still pass) ---
    def test_create_items_batch_api_success(self):
        # Clear initial data for this specific test if it interferes
        self.mock_storage.data.clear()
        if hasattr(self.mock_storage, '_keys_in_order'): self.mock_storage._keys_in_order.clear()

        items_to_create_payload = [
            {"name": "Batch API Item 1", "description": "First batch via API", "data": {"api_b": 1}},
            {"name": "Batch API Item 2", "data": {"api_b": 2}},
        ]
        response = self.client.post("/items/batch", json=items_to_create_payload)
        self.assertEqual(response.status_code, 200)
        created_items_response = response.json()

        self.assertEqual(len(created_items_response), 2)
        for i, item_resp in enumerate(created_items_response):
            self.assertTrue(item_resp.get("id"))
            self.assertEqual(item_resp["name"], items_to_create_payload[i]["name"])
            mock_item = asyncio.run(self.mock_storage.read_one(item_resp["id"]))
            self.assertIsNotNone(mock_item)
            self.assertEqual(mock_item["name"], items_to_create_payload[i]["name"])

    def test_create_items_batch_api_empty_list(self):
        response = self.client.post("/items/batch", json=[])
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "No items provided for batch creation.")

    def test_export_all_items_api_no_items(self):
        self.mock_storage.data.clear() # Ensure storage is empty
        if hasattr(self.mock_storage, '_keys_in_order'): self.mock_storage._keys_in_order.clear()

        response = self.client.get("/items/export")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_export_all_items_api_with_items(self):
        # setUp already populates with 5 items
        response = self.client.get("/items/export")
        self.assertEqual(response.status_code, 200)
        exported_items = response.json()

        self.assertEqual(len(exported_items), len(self.test_api_items_data))

        created_ids = {item["id"] for item in self.test_api_items_data}
        exported_ids = {item["id"] for item in exported_items}
        self.assertEqual(created_ids, exported_ids)


if __name__ == '__main__':
    unittest.main()
