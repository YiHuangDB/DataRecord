from typing import List, Optional, Any, Dict # Added Any, Dict
from fastapi import FastAPI, HTTPException, Response, Query, Request # Added Request
from src.core.models import Item, PaginatedResponseModel
from src.core.storage_interface import StorageInterface, PaginatedDbResponse
from src.core.query_models import FilterCondition, SortInstruction, SortDirection # Added query_models

# Define tags for OpenAPI documentation
tags_metadata = [
    {
        "name": "Items",
        "description": "CRUD operations for individual items, including paginated listing with filtering and sorting.",
    },
    {
        "name": "Items Batch Operations",
        "description": "Batch create and export operations for items.",
    },
]

app = FastAPI(
    title="Flexible CRUD API",
    description="A demonstration API for CRUD operations with configurable storage backends.",
    version="1.0.0",
    openapi_tags=tags_metadata,
)

storage_adapter: Optional[StorageInterface] = None


# Helper function for parsing filter and sort query parameters
def _parse_query_params(
    query_params: Dict[str, Any]
) -> (Optional[List[FilterCondition]], Optional[List[SortInstruction]]):
    filters: List[FilterCondition] = []
    sort_instructions: List[SortInstruction] = []

    # Define valid operators for filters. Used to distinguish operator suffix from field name parts.
    valid_operators = ["eq", "ne", "gt", "gte", "lt", "lte", "contains", "startswith", "in"]

    for key, value in query_params.items():
        if key == "sort_by":
            # Parse sort_by: e.g., "name", "-price", "category,-name"
            # Multiple sort_by params are not standard; usually it's one comma-separated string.
            # If query_params can have multiple 'sort_by' keys, Starlette's MultiDict via request.query_params
            # would need specific handling (e.g., request.query_params.getlist('sort_by')).
            # Assuming value is a single string if 'sort_by' appears once.
            sort_fields_str = value if isinstance(value, str) else "" # Handle if not string
            sort_fields = [field.strip() for field in sort_fields_str.split(',') if field.strip()]
            for field_entry in sort_fields:
                direction: SortDirection = "asc"
                field_name = field_entry
                if field_entry.startswith("-"):
                    direction = "desc"
                    field_name = field_entry[1:]
                elif field_entry.startswith("+"):
                    field_name = field_entry[1:]

                if field_name:
                     sort_instructions.append(SortInstruction(field=field_name, direction=direction))

        elif key in ["offset", "limit"]:
            continue # Handled by FastAPI Query directly in the route signature

        else: # Assume it's a filter condition: field__operator=value or field=value (implies field__eq=value)
            parts = key.split("__")
            field_name_from_key = parts[0]
            operator_from_key = "eq" # Default operator

            if len(parts) > 1 and parts[-1] in valid_operators:
                operator_from_key = parts[-1]
                field_name_from_key = "__".join(parts[:-1])

            # Type conversion for numeric and 'in' operators
            original_value = value
            parsed_value = value # Start with original value

            if operator_from_key in ["gt", "gte", "lt", "lte"]:
                try:
                    parsed_value = float(original_value)
                except ValueError:
                    try:
                        parsed_value = int(original_value)
                    except ValueError:
                        # Let adapter handle type error or raise specific HTTP 400 here if strict
                        # For now, pass as string and let adapter deal with it.
                        # print(f"Warning: Could not convert value '{original_value}' for numeric filter on field '{field_name_from_key}'")
                        pass
            elif operator_from_key == "in":
                if isinstance(original_value, str):
                    # If 'in' value is a comma-separated string from query param
                    parsed_value = [part.strip() for part in original_value.split(',') if part.strip()]
                elif isinstance(original_value, list):
                    # If FastAPI somehow passes a list (e.g. for key[]=v1&key[]=v2, though not standard for 'in')
                    parsed_value = [str(v).strip() for v in original_value if str(v).strip()]
                # If it's already a list from another source, use as is (assuming correct type)
                # else: it's neither string nor list, could be an issue.

            filters.append(FilterCondition(field=field_name_from_key, operator=operator_from_key, value=parsed_value))

    return filters if filters else None, sort_instructions if sort_instructions else None


@app.post("/items", response_model=Item, tags=["Items"],
          summary="Create a new item",
          description="Creates a new item in the configured storage backend. The item ID is generated by the storage backend.")
async def create_item(item: Item) -> Item:
    if storage_adapter is None:
        raise HTTPException(status_code=503, detail="Storage adapter not initialized. Please check configuration.")
    item_data = item.model_dump(exclude_unset=True, exclude={'id'})
    try:
        created_item_dict = await storage_adapter.create(item_data)
        return Item(**created_item_dict)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during item creation: {e}")


@app.get(
    "/items",
    response_model=PaginatedResponseModel[Item],
    summary="Read all items with advanced filtering, sorting, and pagination",
    tags=["Items"],
    description="Retrieves items with support for pagination (offset, limit). "                             "Additional query parameters can be used for filtering (e.g., `name__contains=value`, `id=value`) "                             "and sorting (e.g., `sort_by=name,-id`). "                             "See the project README for detailed query syntax and supported operators/fields.",
)
async def read_items(
    request: Request, # Inject Request object to access all query params
    offset: int = Query(0, ge=0, description="Offset for pagination. Number of items to skip from the beginning. Must be non-negative."),
    limit: int = Query(10, gt=0, le=100, description="Limit for pagination. Maximum number of items to return. Must be positive and at most 100.")
):
    if storage_adapter is None:
        raise HTTPException(status_code=503, detail="Storage adapter not initialized. Please check configuration.")

    # Convert Starlette's MultiDict to a standard dict.
    # For keys with multiple values (e.g. ?field=a&field=b), this dict() conversion
    # will only keep one of them (typically the last one).
    # If multiple values for the same filter key are needed (e.g. for an OR condition on same field,
    # or multiple 'in' values not comma-separated), request.query_params.multi_items() needs to be parsed.
    # The current _parse_query_params handles comma-separated values for 'in'.
    query_params_dict = dict(request.query_params)

    parsed_filters, parsed_sort_by = _parse_query_params(query_params_dict)

    try:
        paginated_db_data: PaginatedDbResponse = await storage_adapter.read_all(
            filters=parsed_filters,
            sort_by=parsed_sort_by,
            offset=offset,
            limit=limit
        )

        validated_items = [Item(**item_dict) for item_dict in paginated_db_data["items"]]

        return PaginatedResponseModel[Item](
            items=validated_items,
            total_count=paginated_db_data["total_count"],
            offset=paginated_db_data["offset"],
            limit=paginated_db_data["limit"]
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except ValueError as e: # Catch potential ValueError from type conversions in parser or model validation
        raise HTTPException(status_code=400, detail=f"Invalid query parameter or item data: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


@app.get("/items/{item_id}", response_model=Item, tags=["Items"],
          summary="Read a specific item by ID",
          description="Retrieves a single item by its unique ID.")
async def read_item(item_id: str) -> Item:
    if storage_adapter is None:
        raise HTTPException(status_code=503, detail="Storage adapter not initialized. Please check configuration.")
    try:
        item_dict = await storage_adapter.read_one(item_id)
        if item_dict is None:
            raise HTTPException(status_code=404, detail="Item not found")
        return Item(**item_dict)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while retrieving item {item_id}: {e}")


@app.put("/items/{item_id}", response_model=Item, tags=["Items"],
         summary="Update an existing item",
         description="Updates the details of an existing item, identified by its ID. All fields provided in the request body will be updated.")
async def update_item(item_id: str, item: Item) -> Item:
    if storage_adapter is None:
        raise HTTPException(status_code=503, detail="Storage adapter not initialized. Please check configuration.")
    item_data = item.model_dump(exclude_unset=True, exclude={'id'})
    try:
        updated_item_dict = await storage_adapter.update(item_id, item_data)
        if updated_item_dict is None:
            raise HTTPException(status_code=404, detail="Item not found")
        return Item(**updated_item_dict)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while updating item {item_id}: {e}")


@app.delete("/items/{item_id}", status_code=204, tags=["Items"],
            summary="Delete an item",
            description="Deletes an item from the storage backend using its ID. Returns a 204 No Content response on successful deletion.")
async def delete_item(item_id: str):
    if storage_adapter is None:
        raise HTTPException(status_code=503, detail="Storage adapter not initialized. Please check configuration.")
    try:
        deleted = await storage_adapter.delete(item_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Item not found")
        return Response(status_code=204)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while deleting item {item_id}: {e}")

# --- New Batch Operations ---

@app.post(
    "/items/batch",
    response_model=List[Item],
    summary="Create multiple items in batch",
    tags=["Items Batch Operations"],
    description="Allows creating multiple items in a single request. Each item in the request list is processed. Returns a list of created items."
)
async def create_items_batch(items_to_create: List[Item]):
    if storage_adapter is None:
        raise HTTPException(status_code=503, detail="Storage adapter not initialized. Please check configuration.")

    if not items_to_create:
        raise HTTPException(status_code=400, detail="No items provided for batch creation.")

    try:
        item_data_list = [item.model_dump(exclude_none=True) for item in items_to_create]

        created_item_dicts = await storage_adapter.create_many(item_data_list)

        response_items = [Item(**item_dict) for item_dict in created_item_dicts]

        return response_items
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during batch creation: {str(e)}")

@app.get(
    "/items/export",
    response_model=List[Item],
    summary="Export all items from storage",
    tags=["Items Batch Operations"],
    description="Retrieves all items currently stored in the backend without pagination. Use with caution on very large datasets."
)
async def export_all_items():
    if storage_adapter is None:
        raise HTTPException(status_code=503, detail="Storage adapter not initialized. Please check configuration.")

    try:
        exported_item_dicts = await storage_adapter.export_all()

        response_items = [Item(**item_dict) for item_dict in exported_item_dicts]

        return response_items
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during export: {str(e)}")
