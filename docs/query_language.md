# Advanced Querying Guide

The `GET /items` endpoint supports advanced filtering, sorting, and pagination to allow precise data retrieval. This guide details the syntax for these operations.

## Filtering

Filters are applied as query parameters. Multiple filter parameters are **ANDed** together.

**Syntax**:

*   Exact match: `fieldName=value` (equivalent to `fieldName__eq=value`)
*   Operator-based: `fieldName__operator=value`

**Supported Fields for Filtering**:
Currently, filtering is best supported on top-level fields of the item model: `id`, `name`, `description`. Filtering on nested fields within the `data` JSON object (e.g., `data.price__gt=10`) is not directly supported by the basic query parser and may not work consistently or performantly across all storage backends.

**Supported Operators**:

*   `eq` (Equals): Matches items where the field is exactly equal to the specified value.
    *   Example: `?name__eq=My Specific Item` or `?name=My Specific Item`
*   `ne` (Not Equals): Matches items where the field is not equal to the specified value.
    *   Example: `?name__ne=Archived Item`
*   `gt` (Greater Than): Matches items where the field's numeric value is greater than the specified value.
    *   Example (if `id` were treated numerically, or for a future numeric field): `?id__gt=100`
*   `gte` (Greater Than or Equal To): Matches items where the field's numeric value is greater than or equal to the specified value.
    *   Example: `?data.stock__gte=50` (Note: subject to nested field limitations mentioned above)
*   `lt` (Less Than): Matches items where the field's numeric value is less than the specified value.
    *   Example: `?data.price__lt=20.50` (Note: subject to nested field limitations)
*   `lte` (Less Than or Equal To): Matches items where the field's numeric value is less than or equal to the specified value.
    *   Example: `?data.priority__lte=3` (Note: subject to nested field limitations)
*   `contains` (Contains Substring): Matches items where the string field contains the specified substring (case-insensitive).
    *   Example: `?description__contains=important keyword`
*   `startswith` (Starts With Prefix): Matches items where the string field starts with the specified prefix (case-insensitive).
    *   Example: `?name__startswith=PROJ-`
*   `in` (In a List): Matches items where the field's value is one of a list of specified values. Values should be comma-separated in the query parameter.
    *   Example: `?name__in=Apple,Banana,Cherry` or `?data.status__in=active,pending` (Note: subject to nested field limitations for `data.status`)

**Example Filter Combinations (AND logic)**:
*   `GET /items?name__contains=report&description__startswith=Confidential`
    *   Finds items where the name contains "report" AND the description starts with "Confidential".

## Sorting

Sorting is controlled by the `sort_by` query parameter.

**Syntax**:

*   Single field, ascending: `sort_by=fieldName`
    *   Example: `?sort_by=name` (sorts by name, A-Z)
*   Single field, descending: `sort_by=-fieldName` (prefix with a hyphen)
    *   Example: `?sort_by=-name` (sorts by name, Z-A)
*   Multiple fields: Comma-separate field names. Sorting is applied in the order specified.
    *   Example: `?sort_by=description,-name` (sorts by description ascending, then by name descending for items with the same description).

**Supported Fields for Sorting**:
Similar to filtering, sorting is best supported on top-level fields (`id`, `name`, `description`). Sorting on nested `data` fields is subject to backend capabilities and current implementation limitations.

## Pagination

Pagination is controlled by `offset` and `limit` query parameters and is applied *after* filtering and sorting.

*   `offset` (integer, optional, default: 0): Number of items to skip from the beginning of the filtered and sorted result set.
*   `limit` (integer, optional, default: 10, max: 100): Maximum number of items to return in the response.

## Current Limitations

*   **Nested Field Operations**: Filtering or sorting directly on nested fields within the `data` JSON object (e.g., `data.price__gt=10` or `sort_by=data.category`) is not robustly supported across all backends with the current basic query parser. While some simple cases might work with certain backends if the `data` field is structured simply, it's generally recommended to use top-level fields for complex queries or ensure the `data` field is denormalized to top-level fields if frequent querying on its sub-attributes is needed.
*   **Complex OR Conditions**: The API does not currently support `OR` conditions between different fields (e.g., `name__startswith=A OR description__contains=Urgent`). All top-level filter conditions are implicitly ANDed. The `in` operator provides OR logic for multiple values within a single field.
*   **Data Type Handling in Filters**: The query parser attempts basic conversion for numeric operators (`gt`, `gte`, `lt`, `lte`). If a value cannot be converted to a number for these operators, the filter might behave unexpectedly or be ignored by the storage adapter. String comparisons are generally case-insensitive for `contains` and `startswith`.

This query language provides a flexible way to retrieve specific subsets of your data. For details on the API response structure, see the [`api_reference.md`](api_reference.md).
