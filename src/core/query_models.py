from typing import TypedDict, List, Any, Literal

class FilterCondition(TypedDict):
    """
    Represents a single filter condition to be applied when querying data.

    Attributes:
        field: The name of the field to filter on.
        operator: The comparison operator (e.g., "eq", "ne", "gt", "gte", "lt", "lte",
                  "contains", "startswith", "in"). Support for operators may vary by adapter.
        value: The value to compare against. For "in" operator, this might be a list.
    """
    field: str
    operator: str
    value: Any

SortDirection = Literal["asc", "desc"]
"""Defines the allowed directions for sorting: 'asc' for ascending, 'desc' for descending."""

class SortInstruction(TypedDict):
    """
    Represents a single sort instruction for ordering query results.

    Attributes:
        field: The name of the field to sort by.
        direction: The direction of the sort ('asc' or 'desc').
    """
    field: str
    direction: SortDirection
