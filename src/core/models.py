from typing import Optional, Dict
from pydantic import BaseModel

class Item(BaseModel):
    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    data: Dict # for arbitrary data
