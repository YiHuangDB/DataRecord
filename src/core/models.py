from typing import Optional, Dict, List, TypeVar, Generic, Any # Added List, TypeVar, Generic, Any
from pydantic import BaseModel, Field # Added Field

T = TypeVar('T') # Define TypeVar T at the module level

class Item(BaseModel):
    """
    Pydantic model representing an item.
    Used for request and response validation and serialization.
    """
    id: Optional[str] = Field(None, description="Unique identifier for the item (auto-generated if not provided on creation)")
    name: str = Field(..., description="Name of the item") # ... means required
    description: Optional[str] = Field(None, description="Optional description of the item")
    data: Dict[str, Any] = Field({}, description="Flexible dictionary for arbitrary data associated with the item")


class PaginatedResponseModel(BaseModel, Generic[T]):
    """
    Generic Pydantic model for paginated API responses.
    Allows consistent structure for returning lists of resources with pagination details.
    """
    items: List[T] = Field(..., description="The list of items for the current page.")
    total_count: int = Field(..., description="Total number of items available across all pages.")
    offset: int = Field(..., description="Offset from where the items are returned (i.e., number of items skipped).")
    limit: int = Field(..., description="Maximum number of items returned in this response.")
    # Optional: HATEOAS links (not implemented in this step)
    # next_url: Optional[str] = None
    # previous_url: Optional[str] = None
