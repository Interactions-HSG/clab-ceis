"""Customer-facing repair and return CO2 scenario calculations.

The garment, material, fabric-block, process, and emission-factor data comes
from the existing CEIS model.  Only the temporary damage-to-process mapping is
declared here; image analysis can later emit the same damage codes and exact
affected block IDs.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException

from ceis_backend.data.location_details import ACTIVITY_ID_TRANSPORT
from ceis_backend.models import Process
from ceis_backend.queries import (
    db_get_garment_processes,
    db_get_inventory_fabric_blocks_for_garment,
    db_get_process_types,
    db_get_sold_garment,
    db_get_sold_garments,
    get_fabric_block_recipe,
)
from ceis_backend.utils import (
    calculate_process_emissions,
    calculate_transport_emission,
)
from ceis_backend.wiser_bridge import WiserClient


@dataclass(frozen=True)
class ProcessRequirement:
    name: str
    amount: float
    label: str | None = None


@dataclass(frozen=True)
class DamageProfile:
    code: str
    label: str
    repair_processes: tuple[ProcessRequirement, ...]
    replacement_block_count: int = 0
    unrecoverable_block_count: int = 0
    repair_available: bool = True
    whole_garment_available: bool = True
    fabric_blocks_available: bool = True


# The seeded garment recipe uses 0.042 kWh of sewing and 0.22 kWh of
# steaming. These lightweight placeholders keep repair work proportional to
# that baseline without adding a more detailed time or equipment model.
_SMALL_REPAIR_SEWING_KWH = 0.0042
_MEDIUM_REPAIR_SEWING_KWH = 0.0105
_LARGE_REPAIR_SEWING_KWH = 0.021
_PANEL_REPLACEMENT_SEWING_KWH = 0.042
_ALLOCATED_WASHING_KWH = 0.10
_LIGHT_STEAMING_KWH = 0.11

_STEAMING = (ProcessRequirement("steaming", _LIGHT_STEAMING_KWH),)
_BLOCK_PREPARATION = (
    ProcessRequirement("washing", _ALLOCATED_WASHING_KWH),
    ProcessRequirement("sewing", _LARGE_REPAIR_SEWING_KWH, "disassembly"),
)


DAMAGE_PROFILES: tuple[DamageProfile, ...] = (
    DamageProfile(
        "dirt",
        "Dirt or odor",
        (ProcessRequirement("washing", _ALLOCATED_WASHING_KWH),),
    ),
    DamageProfile(
        "stain",
        "Stain or discoloration",
        (
            ProcessRequirement("washing", _ALLOCATED_WASHING_KWH),
            ProcessRequirement("dyeing", 0.02, "surface treatment"),
        ),
    ),
    DamageProfile(
        "small_hole",
        "Small hole or puncture",
        (ProcessRequirement("sewing", _SMALL_REPAIR_SEWING_KWH),),
    ),
    DamageProfile(
        "tear",
        "Large hole, tear or cut",
        (ProcessRequirement("sewing", _LARGE_REPAIR_SEWING_KWH),),
    ),
    DamageProfile(
        "seam",
        "Open or damaged seam",
        (ProcessRequirement("sewing", _MEDIUM_REPAIR_SEWING_KWH),),
    ),
    DamageProfile(
        "worn",
        "Worn or thinning fabric",
        (ProcessRequirement("sewing", _LARGE_REPAIR_SEWING_KWH),),
    ),
    DamageProfile(
        "fastener",
        "Missing button or snap",
        (ProcessRequirement("sewing", _SMALL_REPAIR_SEWING_KWH),),
    ),
    DamageProfile(
        "zipper",
        "Broken zipper",
        (ProcessRequirement("sewing", _LARGE_REPAIR_SEWING_KWH),),
    ),
    DamageProfile(
        "trim",
        "Damaged elastic, cuff or hem",
        (ProcessRequirement("sewing", _MEDIUM_REPAIR_SEWING_KWH),),
    ),
    DamageProfile(
        "coating",
        "Coating or delamination failure",
        (ProcessRequirement("dyeing", 0.04, "surface treatment"),),
    ),
    DamageProfile(
        "burn",
        "Burn or chemical damage",
        (
            ProcessRequirement(
                "sewing",
                _PANEL_REPLACEMENT_SEWING_KWH,
                "panel replacement",
            ),
        ),
        replacement_block_count=1,
        unrecoverable_block_count=1,
    ),
    DamageProfile(
        "contamination",
        "Mold or unsafe contamination",
        (),
        repair_available=False,
        whole_garment_available=False,
        fabric_blocks_available=False,
    ),
    DamageProfile(
        "unknown",
        "Multiple or unknown damage",
        (),
        repair_available=False,
        whole_garment_available=False,
        fabric_blocks_available=False,
    ),
)

DAMAGE_PROFILE_BY_CODE = {profile.code: profile for profile in DAMAGE_PROFILES}

# A light kit is still transported when no replacement panel is required.
MINIMUM_REPAIR_KIT_WEIGHT_KG = 0.05
HIGHER_ELECTRICITY_FACTOR_ACTIVITY_ID = 6566


def _electricity_process_names() -> set[str]:
    """Return process names whose configured unit is electricity (kWh)."""
    return {
        str(process_type["name"])
        for process_type in db_get_process_types()
        if str(process_type.get("unit") or "").strip().lower() == "kwh"
    }


def _processes_for_electricity_mode(
    processes: list[Process], use_higher_electricity_factor: bool
) -> list[Process]:
    if not use_higher_electricity_factor:
        return processes

    electricity_processes = _electricity_process_names()
    return [
        Process(
            name=process.name,
            amount=process.amount,
            activity_id=(
                HIGHER_ELECTRICITY_FACTOR_ACTIVITY_ID
                if process.name in electricity_processes
                else process.activity_id
            ),
        )
        for process in processes
    ]


def get_circular_scenario_options() -> dict:
    """Return actual sold garments and the temporary damage catalog."""
    garments = db_get_sold_garments()
    return {
        "garments": [
            {
                **garment,
                "label": f"{garment['name']} · garment #{garment['id']}",
            }
            for garment in garments
        ],
        "damages": [
            {"code": profile.code, "label": profile.label}
            for profile in DAMAGE_PROFILES
        ],
    }


def _resolve_processes(
    requirements: tuple[ProcessRequirement, ...],
    use_higher_electricity_factor: bool,
) -> list[Process]:
    process_types = {item["name"]: item for item in db_get_process_types()}
    missing = sorted(
        requirement.name
        for requirement in requirements
        if requirement.name not in process_types
    )
    if missing:
        raise HTTPException(
            status_code=500,
            detail=f"Missing process types: {', '.join(missing)}",
        )
    processes = [
        Process(
            name=requirement.name,
            amount=requirement.amount,
            activity_id=int(process_types[requirement.name]["activity_id"]),
        )
        for requirement in requirements
    ]
    return _processes_for_electricity_mode(
        processes, use_higher_electricity_factor
    )


def _process_result(
    wiser_client: WiserClient,
    requirements: tuple[ProcessRequirement, ...],
    use_higher_electricity_factor: bool,
) -> dict:
    processes = _resolve_processes(requirements, use_higher_electricity_factor)
    total, details = calculate_process_emissions(wiser_client, processes)
    for requirement, detail in zip(requirements, details):
        detail["label"] = requirement.label or requirement.name
    return {
        "total_co2eq": round(float(total), 6),
        "details": details,
    }


def _new_equivalent_block_data(
    wiser_client: WiserClient,
    blocks: list[dict],
    use_higher_electricity_factor: bool,
) -> dict:
    details: list[dict] = []
    total_co2eq = 0.0
    total_weight_kg = 0.0
    total_material_co2eq = 0.0
    total_process_co2eq = 0.0

    for block in blocks:
        material_id = block.get("material_id")
        activity_id = block.get("activity_id")
        if material_id is None or activity_id is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Fabric block {block['inventory_id']} is missing material data"
                ),
            )

        block_recipe = get_fabric_block_recipe(
            block["type_name"], int(material_id)
        )
        if block_recipe is None:
            raise HTTPException(
                status_code=400,
                detail=f"No recipe for fabric block '{block['type_name']}'",
            )

        weight_kg = float(block["kg_per_sqm"]) * float(block["sqm"])
        material_factor = wiser_client.get_emission_per_unit(int(activity_id))
        material_co2eq = (
            float(material_factor) * weight_kg
            if material_factor is not None
            else 0.0
        )
        process_co2eq, process_details = calculate_process_emissions(
            wiser_client,
            _processes_for_electricity_mode(
                block_recipe.processes, use_higher_electricity_factor
            ),
        )
        block_total = material_co2eq + process_co2eq
        total_co2eq += block_total
        total_weight_kg += weight_kg
        total_material_co2eq += material_co2eq
        total_process_co2eq += process_co2eq
        details.append(
            {
                "inventory_id": block["inventory_id"],
                "fabric_block": block["type_name"],
                "material": block["material_name"],
                "weight_kg": round(weight_kg, 6),
                "new_equivalent_co2eq": round(block_total, 6),
                "material_co2eq": round(material_co2eq, 6),
                "process_co2eq": round(process_co2eq, 6),
                "processes": process_details,
            }
        )

    return {
        "total_co2eq": round(total_co2eq, 6),
        "total_weight_kg": round(total_weight_kg, 6),
        "material_co2eq": round(total_material_co2eq, 6),
        "process_co2eq": round(total_process_co2eq, 6),
        "details": details,
    }


def _aggregate_components(components: list[dict]) -> list[dict]:
    totals: dict[str, float] = {}
    for component in components:
        name = str(component["name"])
        totals[name] = totals.get(name, 0.0) + float(component["co2eq"])
    return [
        {"name": name, "co2eq": round(value, 6)}
        for name, value in totals.items()
    ]


def _process_components(prefix: str, process_result: dict) -> list[dict]:
    return _aggregate_components(
        [
            {
                "name": f"{prefix}: {detail.get('label', detail['process'])}",
                "co2eq": detail.get("emission", 0),
            }
            for detail in process_result.get("details", [])
        ]
    )


def _transport_result(
    distance_km: float,
    legs: int,
    weight_kg: float,
    emission_per_unit: float | None,
) -> dict:
    co2eq = calculate_transport_emission(
        distance_km * legs, weight_kg, emission_per_unit
    )
    return {
        "distance_km": round(distance_km, 3),
        "legs": legs,
        "weight_kg": round(weight_kg, 6),
        "co2eq": round(float(co2eq or 0), 6),
    }


def _available_scenario(
    total_co2eq: float,
    reference_co2eq: float,
    components: list[dict],
    **extra,
) -> dict:
    saving_co2eq = reference_co2eq - total_co2eq
    saving_percent = (
        saving_co2eq / reference_co2eq * 100 if reference_co2eq else None
    )
    return {
        "available": True,
        "total_co2eq": round(total_co2eq, 6),
        "saving_co2eq": round(saving_co2eq, 6),
        "saving_percent": (
            round(saving_percent, 1) if saving_percent is not None else None
        ),
        "components": _aggregate_components(components),
        **extra,
    }


def _unavailable_scenario(reason: str) -> dict:
    return {
        "available": False,
        "reason": reason,
        "total_co2eq": None,
        "saving_co2eq": None,
        "saving_percent": None,
        "components": [],
        "reference_components": [],
    }


def calculate_circular_scenarios(
    garment_id: int,
    distance_km: float,
    damage_code: str,
    wiser_client: WiserClient,
    use_higher_electricity_factor: bool = False,
) -> dict:
    """Calculate alternatives without choosing or ranking a preferred route."""
    if distance_km < 0:
        raise HTTPException(status_code=422, detail="distance_km must be non-negative")

    higher_electricity_factor = (
        wiser_client.get_emission_per_unit(
            HIGHER_ELECTRICITY_FACTOR_ACTIVITY_ID
        )
        if use_higher_electricity_factor
        else None
    )

    garment = db_get_sold_garment(garment_id)
    if garment is None:
        raise HTTPException(status_code=404, detail="Sold garment not found")

    damage = DAMAGE_PROFILE_BY_CODE.get(damage_code)
    if damage is None:
        raise HTTPException(status_code=404, detail="Damage type not found")

    blocks = db_get_inventory_fabric_blocks_for_garment(garment_id)
    if not blocks:
        raise HTTPException(
            status_code=400,
            detail="Selected garment has no linked fabric blocks",
        )

    block_reference = _new_equivalent_block_data(
        wiser_client, blocks, use_higher_electricity_factor
    )
    garment_processes = _processes_for_electricity_mode(
        db_get_garment_processes(int(garment["type_id"])),
        use_higher_electricity_factor,
    )
    assembly_co2eq, assembly_details = calculate_process_emissions(
        wiser_client, garment_processes
    )
    transport_factor = wiser_client.get_emission_per_unit(ACTIVITY_ID_TRANSPORT)
    garment_weight_kg = float(block_reference["total_weight_kg"])
    block_count = len(blocks)
    new_garment_transport = _transport_result(
        distance_km,
        1,
        garment_weight_kg,
        transport_factor,
    )
    new_garment_production_co2eq = (
        block_reference["total_co2eq"] + assembly_co2eq
    )
    new_garment_co2eq = (
        new_garment_production_co2eq + new_garment_transport["co2eq"]
    )
    new_garment_components = _aggregate_components(
        [
            {
                "name": "New material",
                "co2eq": block_reference["material_co2eq"],
            },
            {
                "name": "Fabric-block production",
                "co2eq": block_reference["process_co2eq"],
            },
            *[
                {
                    "name": f"Garment assembly: {detail['process']}",
                    "co2eq": detail.get("emission", 0),
                }
                for detail in assembly_details
            ],
            {
                "name": "Transport",
                "co2eq": new_garment_transport["co2eq"],
            },
        ]
    )

    repair_process = _process_result(
        wiser_client, damage.repair_processes, use_higher_electricity_factor
    )
    replacement_count = min(damage.replacement_block_count, block_count)
    replacement_share = replacement_count / block_count
    replacement_material_co2eq = (
        float(block_reference["total_co2eq"]) * replacement_share
    )
    replacement_weight_kg = garment_weight_kg * replacement_share
    shared_repair_co2eq = (
        float(repair_process["total_co2eq"]) + replacement_material_co2eq
    )
    shared_repair_components = _process_components("Repair", repair_process)
    if replacement_material_co2eq:
        shared_repair_components.append(
            {
                "name": "Replacement fabric blocks",
                "co2eq": round(replacement_material_co2eq, 6),
            }
        )

    if damage.repair_available:
        self_transport = _transport_result(
            distance_km,
            1,
            max(replacement_weight_kg, MINIMUM_REPAIR_KIT_WEIGHT_KG),
            transport_factor,
        )
        professional_transport = _transport_result(
            distance_km,
            2,
            garment_weight_kg,
            transport_factor,
        )
        self_repair = _available_scenario(
            shared_repair_co2eq + self_transport["co2eq"],
            new_garment_co2eq,
            components=[
                *shared_repair_components,
                {"name": "Transport", "co2eq": self_transport["co2eq"]},
            ],
            shared_repair_co2eq=round(shared_repair_co2eq, 6),
            transport=self_transport,
        )
        professional_repair = _available_scenario(
            shared_repair_co2eq + professional_transport["co2eq"],
            new_garment_co2eq,
            components=[
                *shared_repair_components,
                {
                    "name": "Transport",
                    "co2eq": professional_transport["co2eq"],
                },
            ],
            shared_repair_co2eq=round(shared_repair_co2eq, 6),
            transport=professional_transport,
        )
    else:
        reason = "This damage requires manual assessment."
        self_repair = _unavailable_scenario(reason)
        professional_repair = _unavailable_scenario(reason)

    return_transport = _transport_result(
        distance_km,
        1,
        garment_weight_kg,
        transport_factor,
    )
    whole_preparation = _process_result(
        wiser_client, _STEAMING, use_higher_electricity_factor
    )
    block_preparation = _process_result(
        wiser_client, _BLOCK_PREPARATION, use_higher_electricity_factor
    )

    if damage.whole_garment_available and damage.repair_available:
        whole_total = (
            return_transport["co2eq"]
            + shared_repair_co2eq
            + whole_preparation["total_co2eq"]
        )
        whole_garment = _available_scenario(
            whole_total,
            new_garment_co2eq,
            components=[
                *shared_repair_components,
                *_process_components("Preparation", whole_preparation),
                {"name": "Transport", "co2eq": return_transport["co2eq"]},
            ],
            avoided_new_garment_co2eq=round(new_garment_co2eq, 6),
            reference_components=new_garment_components,
            repair_co2eq=round(shared_repair_co2eq, 6),
            preparation=whole_preparation,
            transport=return_transport,
        )
    else:
        whole_garment = _unavailable_scenario(
            "Whole-garment reuse cannot be calculated for this damage."
        )

    if damage.fabric_blocks_available:
        unrecoverable_count = min(damage.unrecoverable_block_count, block_count)
        recoverable_share = (block_count - unrecoverable_count) / block_count
        recoverable_material_co2eq = (
            float(block_reference["total_co2eq"]) * recoverable_share
        )
        block_total = (
            return_transport["co2eq"] + block_preparation["total_co2eq"]
        )
        fabric_blocks = _available_scenario(
            block_total,
            recoverable_material_co2eq,
            components=[
                *_process_components("Preparation", block_preparation),
                {"name": "Transport", "co2eq": return_transport["co2eq"]},
            ],
            recoverable_material_co2eq=round(recoverable_material_co2eq, 6),
            reference_components=[
                {
                    "name": "Material production avoided",
                    "co2eq": round(
                        float(block_reference["material_co2eq"])
                        * recoverable_share,
                        6,
                    ),
                },
                {
                    "name": "Avoided fabric-block production",
                    "co2eq": round(
                        float(block_reference["process_co2eq"])
                        * recoverable_share,
                        6,
                    ),
                },
            ],
            recoverable_block_count=block_count - unrecoverable_count,
            total_block_count=block_count,
            preparation=block_preparation,
            transport=return_transport,
        )
    else:
        fabric_blocks = _unavailable_scenario(
            "Fabric-block recovery cannot be calculated for this damage."
        )

    return {
        "garment": {
            **garment,
            "weight_kg": round(garment_weight_kg, 6),
            "fabric_block_count": block_count,
            "new_equivalent_co2eq": round(new_garment_co2eq, 6),
            "new_equivalent_block_co2eq": block_reference["total_co2eq"],
        },
        "damage": {
            "code": damage.code,
            "label": damage.label,
            "processes": repair_process["details"],
            "replacement_block_count": replacement_count,
            "unrecoverable_block_count": min(
                damage.unrecoverable_block_count, block_count
            ),
        },
        "repair": {
            "self_repair": self_repair,
            "professional_repair": professional_repair,
            "new_garment": {
                "available": True,
                "total_co2eq": round(new_garment_co2eq, 6),
                "saving_co2eq": 0.0,
                "saving_percent": 0.0,
                "components": new_garment_components,
                "production_co2eq": round(new_garment_production_co2eq, 6),
                "transport": new_garment_transport,
                "assembly_processes": assembly_details,
            },
        },
        "return": {
            "whole_garment": whole_garment,
            "fabric_blocks": fabric_blocks,
        },
        "calculation": {
            "electricity_mode": (
                "higher_factor" if use_higher_electricity_factor else "current"
            ),
            "electricity_activity_id": (
                HIGHER_ELECTRICITY_FACTOR_ACTIVITY_ID
                if use_higher_electricity_factor
                else next(
                    (
                        int(process_type["activity_id"])
                        for process_type in db_get_process_types()
                        if str(process_type.get("unit") or "").strip().lower()
                        == "kwh"
                    ),
                    None,
                )
            ),
            "electricity_emission_factor": higher_electricity_factor,
        },
        "assumptions": [
            (
                "Electricity-based processes use the higher emission factor "
                "from activity 6566."
                if use_higher_electricity_factor
                else "Electricity-based processes use the currently configured activity."
            ),
            "Self and professional repair use the same repair processes.",
            "Repair sewing is scaled from 10% to 100% of the seeded garment "
            "sewing amount.",
            "Washing is allocated per garment and return steaming uses half "
            "the new-garment amount.",
            "Self repair transports one repair kit or replacement-material shipment.",
            "Professional repair transports the complete garment for two legs.",
            "Return scenarios transport the complete garment for one leg.",
            "The new-garment reference transports the complete garment for one leg.",
            "Without detected block IDs, unrecoverable blocks use the average block footprint.",
            "Packaging, age, probability, and end-of-life emissions are excluded.",
        ],
    }
