from typing import Any, Optional
from pydantic import BaseModel


class Process(BaseModel):
    name: str
    amount: float
    activity_id: int


class PreparationInfo(BaseModel):
    type_id: int
    amount: float


class FabricBlock(BaseModel):
    id: int
    name: str
    material: str
    amount_kg: float
    activity_id: int
    processes: list[Process]


class SecondLifeFabricBlock(BaseModel):
    id: int
    type_id: int
    co2eq: Optional[int]
    processes: list[Process]
    location_id: Optional[int] = None
    location_name: Optional[str] = None


class SecondLifeFabricBlockInfo(BaseModel):
    type_id: int
    processes: list[PreparationInfo]
    location_id: Optional[int] = None


class EmissionDetails(BaseModel):
    details: list[dict[str, Any]]
    total_emission: float


class GarmentCo2Response(BaseModel):
    processes: EmissionDetails
    fabric_blocks: EmissionDetails


class GarmentRecipe(BaseModel):
    fabric_blocks: list[FabricBlock]
    processes: list[Process]


class GarmentTypeCreate(BaseModel):
    name: str


class FabricBlockTypeCreate(BaseModel):
    name: str
    material: Optional[str] = None
    amount_kg: Optional[float] = None
    activity_id: int


class ProcessTypeCreate(BaseModel):
    name: str
    unit: Optional[str] = None
    activity_id: int


class GarmentRecipeFabricBlockCreate(BaseModel):
    type_id: int
    amount: int


class GarmentRecipeProcessCreate(BaseModel):
    process_id: int
    amount: float


class GarmentRecipeCreate(BaseModel):
    garment_type_id: int
    fabric_blocks: list[GarmentRecipeFabricBlockCreate]
    processes: Optional[list[GarmentRecipeProcessCreate]] = None


class ActivitySearchRequest(BaseModel):
    query: str
