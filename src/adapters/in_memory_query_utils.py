from typing import List, Dict, Any, Optional
from functools import cmp_to_key
from src.core.query_models import FilterCondition, SortInstruction

# Helper function for in-memory filtering
def _filter_items_in_memory(items: List[Dict[str, Any]],
                            filter_conditions: Optional[List[FilterCondition]]) -> List[Dict[str, Any]]:
    if not filter_conditions:
        return items

    filtered_items = []
    for item in items:
        match_all_conditions = True
        for condition in filter_conditions:
            field_name = condition["field"]
            operator = condition["operator"]
            value = condition["value"]

            item_value = item.get(field_name)

            # Basic handling for None values during comparison
            if item_value is None and operator not in ["eq", "ne", "in"]: # 'in' check can handle None if value list contains None
                match_all_conditions = False
                break # Current item cannot satisfy this condition

            match_current_condition = False
            if operator == "eq":
                match_current_condition = (item_value == value)
            elif operator == "ne":
                match_current_condition = (item_value != value)
            elif operator == "gt":
                if isinstance(item_value, (int, float, str)) and isinstance(value, type(item_value)):
                    match_current_condition = (item_value > value)
            elif operator == "gte":
                if isinstance(item_value, (int, float, str)) and isinstance(value, type(item_value)):
                    match_current_condition = (item_value >= value)
            elif operator == "lt":
                if isinstance(item_value, (int, float, str)) and isinstance(value, type(item_value)):
                    match_current_condition = (item_value < value)
            elif operator == "lte":
                if isinstance(item_value, (int, float, str)) and isinstance(value, type(item_value)):
                    match_current_condition = (item_value <= value)
            elif operator == "contains":
                # Case-insensitive for strings. For dicts/lists, value should be element to check.
                if isinstance(item_value, str) and isinstance(value, str):
                    match_current_condition = (value.lower() in item_value.lower())
                elif isinstance(item_value, list) or isinstance(item_value, dict):
                     match_current_condition = (value in item_value)
            elif operator == "startswith":
                if isinstance(item_value, str) and isinstance(value, str):
                    match_current_condition = (item_value.lower().startswith(value.lower()))
            elif operator == "in":
                val_list = value if isinstance(value, list) else [p.strip() for p in str(value).split(',') if p.strip()]
                match_current_condition = (item_value in val_list)
            else:
                # Unknown operator, conservatively treat as no match for this condition
                # Or, could raise an error or log a warning.
                print(f"Warning: Unknown operator '{operator}' for field '{field_name}'.")
                match_current_condition = False

            if not match_current_condition:
                match_all_conditions = False
                break

        if match_all_conditions:
            filtered_items.append(item)
    return filtered_items

# Helper function for in-memory sorting (multi-level)
def _sort_items_in_memory(items: List[Dict[str, Any]],
                          sort_instructions: Optional[List[SortInstruction]]) -> List[Dict[str, Any]]:
    if not sort_instructions:
        return items

    def compare_items(item1: Dict[str, Any], item2: Dict[str, Any]) -> int:
        for instruction in sort_instructions:
            field = instruction["field"]
            direction = instruction["direction"]

            val1 = item1.get(field)
            val2 = item2.get(field)

            # Define sorting order for None values (e.g., Nones first or last)
            # Here, Nones are considered "smaller" than other values.
            if val1 is None and val2 is None:
                cmp = 0
            elif val1 is None:
                cmp = -1
            elif val2 is None:
                cmp = 1
            else:
                # Attempt comparison only if types are compatible or at least not None
                try:
                    if val1 < val2: cmp = -1
                    elif val1 > val2: cmp = 1
                    else: cmp = 0
                except TypeError:
                    # Fallback for incompatible types: sort by string representation
                    # This is a basic fallback and might not be ideal for all cases.
                    s_val1, s_val2 = str(val1), str(val2)
                    if s_val1 < s_val2: cmp = -1
                    elif s_val1 > s_val2: cmp = 1
                    else: cmp = 0

            if cmp != 0:
                return cmp if direction == "asc" else -cmp
        return 0 # All sort keys are equal

    return sorted(items, key=cmp_to_key(compare_items))
