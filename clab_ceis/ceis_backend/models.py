from typing import Optional
from pydantic import BaseModel

class Preparation(BaseModel):
    type_id: int
    amount: int
    
class FabricBlock(BaseModel):
    type_id: int
    co2eq: Optional[int] = None
    preparations: Optional[list[Preparation]] = None

