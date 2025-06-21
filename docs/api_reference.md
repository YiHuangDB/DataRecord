# API Reference

This section provides a detailed reference for all API endpoints available in the Flexible CRUD API.

**Base URL**: `http://localhost:8000` (when running locally)

**Interactive Documentation**:
*   Swagger UI: [`/docs`](/docs)
*   ReDoc: [`/redoc`](/redoc)

These interactive interfaces provide the most up-to-date details based on the application's OpenAPI schema, including model definitions and live try-out capabilities. This document serves as a static reference.

## Common Concepts

*   **Item Model**: Most operations revolve around an "item" resource. An item typically has the following structure (Pydantic model: `Item`):
    *   `id` (string, UUID format, optional on create, server-generated): Unique identifier.
    *   `name` (string, required): Name of the item.
    *   `description` (string, optional): Optional description.
    *   `data` (object/dictionary, required but can be empty `{}`): Arbitrary key-value pairs for additional data.
*   **Error Responses**: Common HTTP status codes include:
    *   `200 OK`: Request successful.
    *   `201 Created`: Resource successfully created (often used for `POST`). Note: Current API uses 200 for POST.
    *   `204 No Content`: Request successful, no content to return (e.g., after `DELETE`).
    *   `400 Bad Request`: Invalid request payload or parameters (e.g., empty batch list).
    *   `404 Not Found`: Resource not found.
    *   `422 Unprocessable Entity`: Validation error for request data (e.g., invalid field types or missing required fields as per Pydantic models).
    *   `500 Internal Server Error`: Unexpected error on the server.
    *   `503 Service Unavailable`: Storage adapter not initialized or backend service down.

## Items Resource (`/items`)

### 1. Create Item

*   **Endpoint**: `POST /items`
*   **Description**: Creates a new item.
*   **Request Body**: JSON object representing the item to create. `id` is optional; if provided, some backends might honor it, otherwise it's server-generated.
    ```json
    {
      "name": "New Item Name",
      "description": "Optional description of the new item.",
      "data": {
        "custom_field": "custom_value",
        "quantity": 10
      }
    }
    ```
*   **Response**: `200 OK` with the JSON object of the created item, including its server-assigned `id`.
    ```json
    {
      "id": "generated-uuid-string",
      "name": "New Item Name",
      "description": "Optional description of the new item.",
      "data": {
        "custom_field": "custom_value",
        "quantity": 10
      }
    }
    ```

### 2. List Items (with Querying)

*   **Endpoint**: `GET /items`
*   **Description**: Retrieves a list of items. Supports advanced filtering, sorting, and pagination. For detailed syntax on filtering and sorting, please refer to [`query_language.md`](query_language.md) and the main project README.
*   **Query Parameters**:
    *   **Filtering**: (e.g., `name__contains=Book`, `id=specific-id`). See [`query_language.md`](query_language.md).
    *   **Sorting**: `sort_by=fieldName` or `sort_by=-fieldName`. See [`query_language.md`](query_language.md).
    *   **Pagination**:
        *   `offset` (int, optional, default: 0): Number of items to skip.
        *   `limit` (int, optional, default: 10, max: 100): Max items per page.
*   **Response**: `200 OK` with a JSON object (Pydantic model: `PaginatedResponseModel[Item]`) containing:
    *   `items`: An array of item objects.
    *   `total_count`: Total number of items matching the filters.
    *   `offset`: The applied offset.
    *   `limit`: The applied limit.
    ```json
    {
      "items": [
        { "id": "uuid1", "name": "Item A", "description": "Description A", "data": {} },
        { "id": "uuid2", "name": "Item B", "description": "Description B", "data": {} }
      ],
      "total_count": 25,
      "offset": 0,
      "limit": 10
    }
    ```

### 3. Get Item by ID

*   **Endpoint**: `GET /items/{item_id}`
*   **Description**: Retrieves a specific item by its unique ID.
*   **Path Parameters**:
    *   `item_id` (string, required): The ID of the item to retrieve.
*   **Response**:
    *   `200 OK`: JSON object of the retrieved item.
    *   `404 Not Found`: If no item with the given ID exists.

### 4. Update Item

*   **Endpoint**: `PUT /items/{item_id}`
*   **Description**: Updates an existing item by its ID. The request body should contain all fields for the item that are intended to be updated. Fields not provided may be set to null or ignored depending on the Pydantic model's behavior (`exclude_unset=True` is used, so only provided fields are processed for update).
*   **Path Parameters**:
    *   `item_id` (string, required): The ID of the item to update.
*   **Request Body**: JSON object with the item data to update.
    ```json
    {
      "name": "Updated Item Name",
      "description": "Updated description.",
      "data": { "status": "active" }
    }
    ```
*   **Response**:
    *   `200 OK`: JSON object of the updated item.
    *   `404 Not Found`: If no item with the given ID exists.

### 5. Delete Item

*   **Endpoint**: `DELETE /items/{item_id}`
*   **Description**: Deletes an item by its ID.
*   **Path Parameters**:
    *   `item_id` (string, required): The ID of the item to delete.
*   **Response**:
    *   `204 No Content`: Item successfully deleted.
    *   `404 Not Found`: If no item with the given ID exists.

## Items Batch Operations

### 1. Batch Create Items

*   **Endpoint**: `POST /items/batch`
*   **Description**: Creates multiple items in a single request.
*   **Request Body**: JSON array of item objects to create. `id` is optional for each item.
    ```json
    [
      { "name": "Batch Item 1", "data": {"key": "val1"} },
      { "name": "Batch Item 2", "description": "Desc B2", "data": {"key": "val2"} }
    ]
    ```
*   **Response**: `200 OK` with a JSON array of the created item objects, including their server-assigned IDs.
    ```json
    [
      { "id": "gen-id-1", "name": "Batch Item 1", "data": {"key": "val1"} },
      { "id": "gen-id-2", "name": "Batch Item 2", "description": "Desc B2", "data": {"key": "val2"} }
    ]
    ```

### 2. Export All Items

*   **Endpoint**: `GET /items/export`
*   **Description**: Exports all items currently in storage. This endpoint does not support pagination or filtering; it returns the entire dataset. Use with caution on very large datasets.
*   **Response**: `200 OK` with a JSON array of all item objects.
    ```json
    [
      { "id": "uuid1", "name": "Item A", "description": "Description A", "data": {} },
      { "id": "uuid2", "name": "Item B", "description": "Description B", "data": {} }
      // ... potentially many more items
    ]
    ```
