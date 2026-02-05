from typing import Any, Optional
from pydantic import BaseModel

class Process(BaseModel):
    activity: str
    time: float
    
class PreparationInfo(BaseModel):
    type_id: int
    time: float
    
class Resource(BaseModel):
    name: str
    activity_id: int
    amount: float

class FabricBlock(BaseModel):
    id: Optional[int]
    type_id: int
    co2eq: Optional[int]
    processes: list[Process]
    
class FabricBlockInfo(BaseModel):
    type_id: int
    processes: list[PreparationInfo]

class EmissionDetails(BaseModel):
    details: list[dict[str, Any]]
    total_emission: float

class Co2Response(BaseModel):
    processes: EmissionDetails
    fabric_blocks: EmissionDetails
    
class GarmentRecipe(BaseModel):
    fabric_blocks: list[str]
    processes: list[Process]