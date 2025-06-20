import unittest
from typing import List, Optional, Dict, Any # Ensure Dict and Any are imported
import asyncio

from fastapi import HTTPException # Keep if used directly, though not in this MockStorage
from fastapi.testclient import TestClient

from src.core.models import Item # Item model is used by API responses
from src.core.storage_interface import StorageInterface, PaginatedDbResponse # Import PaginatedDbResponse
from src.api import routes # This is where 'app' and 'storage_adapter' are defined

# MockStorage implementation
class MockStorage(StorageInterface):
    def __init__(self):
        self.data: Dict[str, Dict[str, Any]] = {}
        self.counter: int = 0
        # For stable ordering in tests, store keys in a list as they are created
        self._keys_in_order: List[str] = []


    async def create(self, item_data: Dict[str, Any]) -> Dict[str, Any]:
        self.counter += 1
        new_id = item_data.get("id")
        if not new_id:
            new_id = str(self.counter)

        final_item_data = item_data.copy()
        final_item_data["id"] = new_id

        if new_id not in self.data: # Add to order list only if it's a new key
            self._keys_in_order.append(new_id)
        self.data[new_id] = final_item_data
        return final_item_data

    async def read_all(self, offset: int = 0, limit: int = 100) -> PaginatedDbResponse:
        # Use self._keys_in_order to get items in a stable order for pagination tests
        all_items_ordered = [self.data[key] for key in self._keys_in_order if key in self.data]
        total_count = len(all_items_ordered)

        # These checks mimic input validation or internal logic; FastAPI Query handles input validation for routes.
        offset = max(0, offset)
        limit = max(0, limit) # Or max(1, limit) if limit=0 is not sensible for the function's purpose

        paginated_items_list = all_items_ordered[offset : offset + limit]
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
            if item_id in self._keys_in_order: # Also remove from ordered list
                self._keys_in_order.remove(item_id)
            return True
        return False

class TestApiRoutes(unittest.TestCase):

    def setUp(self):
        self.mock_storage = MockStorage()
        routes.storage_adapter = self.mock_storage
        self.client = TestClient(routes.app)

    def test_create_item_api(self):
        item_payload = {"name": "API Test Item", "description": "Testing via API", "data": {"api_key": "api_val"}}
        response = self.client.post("/items", json=item_payload)
        self.assertEqual(response.status_code, 200)

        response_data = response.json()
        self.assertIsNotNone(response_data.get("id"))
        self.assertEqual(response_data["name"], item_payload["name"])
        # ... (rest of assertions from original test)
        created_id = response_data["id"]
        stored_item = asyncio.run(self.mock_storage.read_one(created_id))
        self.assertIsNotNone(stored_item)
        self.assertEqual(stored_item["name"], item_payload["name"])

    # --- Pagination Tests for GET /items ---
    def test_read_items_paginated_default_no_items(self):
        response = self.client.get("/items")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["items"]), 0)
        self.assertEqual(data["total_count"], 0)
        self.assertEqual(data["offset"], 0)
        self.assertEqual(data["limit"], 10) # Default API limit from Query

    def test_read_items_paginated_default_with_items(self):
        for i in range(5):
            # MockStorage.create now ensures items are added to _keys_in_order
            asyncio.run(self.mock_storage.create({"name": f"Item {i}", "description": f"Desc {i}", "data": {"key": f"val{i}"}}))

        response = self.client.get("/items")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(len(data["items"]), 5)
        self.assertEqual(data["items"][0]["name"], "Item 0") # Relies on MockStorage order
        self.assertEqual(data["total_count"], 5)
        self.assertEqual(data["offset"], 0)
        self.assertEqual(data["limit"], 10)

    def test_read_items_paginated_custom_offset_limit(self):
        for i in range(15):
            asyncio.run(self.mock_storage.create({"name": f"Item {i}", "data": {}}))

        response = self.client.get("/items?offset=5&limit=5")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(len(data["items"]), 5)
        self.assertEqual(data["items"][0]["name"], "Item 5")
        self.assertEqual(data["total_count"], 15)
        self.assertEqual(data["offset"], 5)
        self.assertEqual(data["limit"], 5)

    def test_read_items_paginated_offset_beyond_total(self):
        for i in range(3):
            asyncio.run(self.mock_storage.create({"name": f"Item {i}", "data": {}}))

        response = self.client.get("/items?offset=10&limit=5")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(len(data["items"]), 0)
        self.assertEqual(data["total_count"], 3)
        self.assertEqual(data["offset"], 10)
        self.assertEqual(data["limit"], 5)

    def test_read_items_paginated_partial_last_page(self):
        for i in range(7):
            asyncio.run(self.mock_storage.create({"name": f"Item {i}", "data": {}}))

        response = self.client.get("/items?offset=5&limit=5")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(len(data["items"]), 2)
        self.assertEqual(data["total_count"], 7)
        self.assertEqual(data["offset"], 5)
        self.assertEqual(data["limit"], 5)
        self.assertEqual(data["items"][0]["name"], "Item 5")
        self.assertEqual(data["items"][1]["name"], "Item 6")

    def test_read_items_paginated_invalid_query_params(self):
        response = self.client.get("/items?offset=-1&limit=5")
        self.assertEqual(response.status_code, 422)

        response = self.client.get("/items?offset=0&limit=0")
        self.assertEqual(response.status_code, 422)

        response = self.client.get("/items?offset=0&limit=-5")
        self.assertEqual(response.status_code, 422)

        response = self.client.get("/items?offset=0&limit=101")
        self.assertEqual(response.status_code, 422)

        response = self.client.get("/items?offset=0&limit=100") # Valid max limit
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["limit"], 100)

    # --- Other existing API tests (read_one, update, delete) ---
    def test_read_one_item_api(self):
        item_data = {"name": "Specific API Item", "data": {}}
        created_item = asyncio.run(self.mock_storage.create(item_data)) # Use returned item with ID

        response = self.client.get(f"/items/{created_item['id']}")
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data["name"], created_item["name"])
        self.assertEqual(response_data["id"], created_item["id"])

    def test_read_one_item_not_found_api(self):
        response = self.client.get("/items/nonexistent-api-item")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Item not found")

    def test_update_item_api(self):
        original_item_data = {"name": "Original API Name", "description": "Original", "data": {"k": "v"}}
        created_item = asyncio.run(self.mock_storage.create(original_item_data))

        update_payload = {"name": "Updated API Name", "description": "Updated Desc", "data": {"new_k": "new_v"}}
        response = self.client.put(f"/items/{created_item['id']}", json=update_payload)
        self.assertEqual(response.status_code, 200)

        response_data = response.json()
        self.assertEqual(response_data["id"], created_item['id'])
        self.assertEqual(response_data["name"], update_payload["name"])

        updated_stored_item = asyncio.run(self.mock_storage.read_one(created_item['id']))
        self.assertEqual(updated_stored_item["name"], update_payload["name"])

    def test_update_item_not_found_api(self):
        update_payload = {"name": "Update Nonexistent", "data": {}}
        response = self.client.put("/items/nonexistent-api-update", json=update_payload)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Item not found")

    def test_delete_item_api(self):
        item_to_delete = {"name": "API Item to Delete", "data": {}}
        created_item = asyncio.run(self.mock_storage.create(item_to_delete))

        response = self.client.delete(f"/items/{created_item['id']}")
        self.assertEqual(response.status_code, 204)

        self.assertIsNone(asyncio.run(self.mock_storage.read_one(created_item['id'])))

    def test_delete_item_not_found_api(self):
        response = self.client.delete("/items/nonexistent-api-delete")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Item not found")

if __name__ == '__main__':
    unittest.main()
