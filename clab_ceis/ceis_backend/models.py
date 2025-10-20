from typing import Optional
from pydantic import BaseModel

class Preparation(BaseModel):
    type: str
    amount: int
    
class FabricBlock(BaseModel):
    type: str
    co2eq: Optional[int] = None
    preparations: Optional[list[Preparation]] = None

