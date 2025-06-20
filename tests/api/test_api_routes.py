import unittest
from typing import List, Optional, Dict, Any
import asyncio
import uuid # Ensure uuid is imported

from fastapi import HTTPException
from fastapi.testclient import TestClient

from src.core.models import Item
from src.core.storage_interface import StorageInterface, PaginatedDbResponse
from src.api import routes

# MockStorage implementation
class MockStorage(StorageInterface):
    def __init__(self):
        self.data: Dict[str, Dict[str, Any]] = {}
        self.counter: int = 0
        self._keys_in_order: List[str] = []


    async def create(self, item_data: Dict[str, Any]) -> Dict[str, Any]:
        self.counter += 1
        new_id = item_data.get("id")
        if not new_id:
            new_id = str(self.counter)

        final_item_data = item_data.copy()
        final_item_data["id"] = new_id

        if new_id not in self.data:
            self._keys_in_order.append(new_id)
        self.data[new_id] = final_item_data
        return final_item_data

    async def read_all(self, offset: int = 0, limit: int = 100) -> PaginatedDbResponse:
        all_items_ordered = [self.data[key] for key in self._keys_in_order if key in self.data]
        total_count = len(all_items_ordered)

        offset = max(0, offset)
        limit = max(0, limit)

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
            if item_id in self._keys_in_order:
                self._keys_in_order.remove(item_id)
            return True
        return False

    async def create_many(self, items_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        created_items_list = []
        for item_data in items_data:
            item_id = item_data.get('id', uuid.uuid4().hex)

            new_item = item_data.copy()
            new_item['id'] = item_id

            self.data[item_id] = new_item
            if new_item['id'] not in self._keys_in_order:
                self._keys_in_order.append(new_item['id'])

            created_items_list.append(new_item)
        return created_items_list

    async def export_all(self) -> List[Dict[str, Any]]:
        # Return items in a consistent order if _keys_in_order is maintained
        return [self.data[key] for key in self._keys_in_order if key in self.data]


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
        created_id = response_data["id"]
        stored_item = asyncio.run(self.mock_storage.read_one(created_id))
        self.assertIsNotNone(stored_item)
        self.assertEqual(stored_item["name"], item_payload["name"])

    def test_read_items_paginated_default_no_items(self):
        response = self.client.get("/items")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["items"]), 0)
        self.assertEqual(data["total_count"], 0)
        self.assertEqual(data["offset"], 0)
        self.assertEqual(data["limit"], 10)

    def test_read_items_paginated_default_with_items(self):
        for i in range(5):
            asyncio.run(self.mock_storage.create({"name": f"Item {i}", "description": f"Desc {i}", "data": {"key": f"val{i}"}}))

        response = self.client.get("/items")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(len(data["items"]), 5)
        self.assertEqual(data["items"][0]["name"], "Item 0")
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

        response = self.client.get("/items?offset=0&limit=100")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["limit"], 100)

    def test_read_one_item_api(self):
        item_data = {"name": "Specific API Item", "data": {}}
        created_item = asyncio.run(self.mock_storage.create(item_data))

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

    # --- Tests for Batch and Export API Endpoints ---

    def test_create_items_batch_api_success(self):
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
        response = self.client.get("/items/export")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_export_all_items_api_with_items(self):
        items_payload = [
            {"name": "Export API 1", "data": {"exp": "val1"}},
            {"name": "Export API 2", "description": "Desc for exp2", "data": {"exp": "val2"}},
        ]
        batch_create_response = self.client.post("/items/batch", json=items_payload)
        self.assertEqual(batch_create_response.status_code, 200)
        created_items = batch_create_response.json()

        response = self.client.get("/items/export")
        self.assertEqual(response.status_code, 200)
        exported_items = response.json()

        self.assertEqual(len(exported_items), len(created_items))

        created_ids = {item["id"] for item in created_items}
        exported_ids = {item["id"] for item in exported_items}
        self.assertEqual(created_ids, exported_ids)

        if exported_items:
            sample_created_item = created_items[0]
            found_in_export = next((exp_item for exp_item in exported_items if exp_item["id"] == sample_created_item["id"]), None)
            self.assertIsNotNone(found_in_export)
            self.assertEqual(found_in_export["name"], sample_created_item["name"])
            self.assertEqual(found_in_export["data"], sample_created_item["data"])

if __name__ == '__main__':
    unittest.main()
