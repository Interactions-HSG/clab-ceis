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
    weight_kg: float
    activity_id: int
    processes: list[Process]


class FabricBlockType(BaseModel):
    id: int
    name: str
    sqm: float


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


class FabricBlockTypeProcessCreate(BaseModel):
    process_id: int
    amount: float


class FabricBlockTypeCreate(BaseModel):
    name: str
    sqm: float
    processes: Optional[list[FabricBlockTypeProcessCreate]] = None


class ProcessTypeCreate(BaseModel):
    name: str
    unit: Optional[str] = None
    activity_id: int


class MaterialCreate(BaseModel):
    name: str
    kg_per_sqm: float
    activity_id: int


class GarmentRecipeFabricBlockCreate(BaseModel):
    type_id: int
    amount: int


class GarmentRecipeMaterialCreate(BaseModel):
    material_id: int


class GarmentRecipeProcessCreate(BaseModel):
    process_id: int
    amount: float


class GarmentRecipeCreate(BaseModel):
    garment_type_name: str
    fabric_blocks: list[GarmentRecipeFabricBlockCreate]
    materials: Optional[list[GarmentRecipeMaterialCreate]] = None
    processes: Optional[list[GarmentRecipeProcessCreate]] = None


class ActivitySearchRequest(BaseModel):
    query: str
