from fastapi import HTTPException

from ceis_backend.models import (
    GarmentCo2Response,
    EmissionDetails,
    FabricBlock,
    SecondLifeFabricBlock,
    Process,
)
from ceis_backend.wiser_bridge import get_emission_per_unit
from ceis_backend.data.location_details import (
    distances_to_manufacturer,
    activity_id_transport,
)
from ceis_backend.queries import (
    get_fabric_block_recipe,
    get_full_garment_recipe,
    get_used_fabric_block,
    get_fabric_block_processes_for_emission,
)


def calculate_transport_emission(
    distance_km: float, amount_kg: float, emission_per_unit: float | None
) -> float | None:
    """
    Calculate transport emission based on distance and weight.

    Args:
        distance_km: Distance in kilometers.
        amount_kg: Weight in kilograms.
        emission_per_unit: Emission per unit from WISER (kg CO2eq per ton-km).

    Returns:
        Total transport emission in kg CO2eq, or None if emission_per_unit is unavailable.
    """
    if emission_per_unit is None:
        return None
    return emission_per_unit / 1000 * distance_km * amount_kg


def calculate_process_emissions(
    wiser_token: str, processes: list[Process]
) -> tuple[float, list[dict]]:
    """
    Calculate total emissions and details for a list of processes.

    Args:
        wiser_token: Token for WISER API.
        processes: List of Process objects to calculate emissions for.

    Returns:
        Tuple of (total_emission, process_details_list).
    """
    total_emission = 0
    process_details = []

    for process in processes:
        emission_per_unit = get_emission_per_unit(wiser_token, process.activity_id)
        emissions = (
            emission_per_unit * process.amount if emission_per_unit is not None else 0
        )
        total_emission += emissions
        process_details.append(
            {
                "process": process.name,
                "amount": process.amount,
                "emission": emissions,
                "activity_id": process.activity_id,
            }
        )

    return total_emission, process_details


def calculate_used_fabric_block_alternative(
    wiser_token: str,
    used_fabric_block: SecondLifeFabricBlock,
    fabric_block_amount_kg: float,
) -> dict:
    """
    Calculate emissions and details for a used/secondhand fabric block.

    Args:
        wiser_token: Token for WISER API.
        used_fabric_block: The SecondLifeFabricBlock to analyze.
        fabric_block_amount_kg: Weight of the fabric block in kg.

    Returns:
        Dictionary with alternative fabric block details and emissions.
    """
    alternative = {
        "id": used_fabric_block.id,
        "location": used_fabric_block.location_name,
        "preparation_details": [],
        "transport_emission": 0,
    }

    # Calculate transport emissions
    transport_emission = 0
    if (
        used_fabric_block.location_name
        and used_fabric_block.location_name in distances_to_manufacturer
    ):
        distance = distances_to_manufacturer[used_fabric_block.location_name]
        transport_emission_per_unit = get_emission_per_unit(
            wiser_token, activity_id_transport
        )
        transport_emission = calculate_transport_emission(
            distance, fabric_block_amount_kg, transport_emission_per_unit
        )

    alternative["transport_emission"] = transport_emission or 0

    # Calculate preparation emissions
    prep_emissions, prep_details = calculate_process_emissions(
        wiser_token, used_fabric_block.processes
    )
    alternative["preparation_details"] = [
        {
            "preparation": detail["process"],
            "amount": detail["amount"],
            "emission": detail["emission"],
            "activity_id": detail["activity_id"],
        }
        for detail in prep_details
    ]
    alternative["emission"] = (transport_emission or 0) + prep_emissions

    return alternative


def process_fabric_block_emissions(
    wiser_token: str,
    fabric_block_name: str,
    fabric_block_data: FabricBlock,
    already_used_ids: list[int],
) -> dict:
    """
    Calculate total emissions for a fabric block including material, production, and alternatives.

    Args:
        wiser_token: Token for WISER API.
        fabric_block_name: Name of the fabric block.
        fabric_block_data: FabricBlock object with material and process info.
        already_used_ids: List of already-used fabric block IDs.

    Returns:
        Dictionary with fabric block emission details.
    """
    block_weight_kg = fabric_block_data.weight_kg
    if block_weight_kg is None:
        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to resolve fabric block weight for "
                f"'{fabric_block_name}' and material '{fabric_block_data.material}'"
            ),
        )

    # Material emission
    material_emission_per_unit = get_emission_per_unit(
        wiser_token, fabric_block_data.activity_id
    )
    material_emission = (
        material_emission_per_unit * block_weight_kg
        if material_emission_per_unit is not None
        else 0
    )

    # Production process emissions
    production_emission, production_details = calculate_process_emissions(
        wiser_token, fabric_block_data.processes
    )

    # Total fabric block emission
    total_emission = material_emission + production_emission

    # Used/alternative fabric block
    used_fabric_block = get_used_fabric_block(fabric_block_name, already_used_ids)
    used_fabric_block_alternative = {}

    if used_fabric_block:
        already_used_ids.append(used_fabric_block.id)
        used_fabric_block_alternative = calculate_used_fabric_block_alternative(
            wiser_token, used_fabric_block, block_weight_kg
        )

    return {
        "fabric_block": fabric_block_name,
        "material": fabric_block_data.material,
        "amount_kg": block_weight_kg,
        "activity_id": fabric_block_data.activity_id,
        "emission": total_emission,
        "material_emission": material_emission,
        "production_emission": production_emission,
        "production_processes": production_details,
        "alternative": used_fabric_block_alternative,
    }


def get_co2_for_garment(
    garment_type_id: int, wiser_token: str, material_id: int
) -> GarmentCo2Response:
    """
    Calculate CO2 emissions for a garment, including fabric blocks and assembly processes.

    Args:
        garment_type_id: The ID of the garment type to calculate emissions for.

    Returns:
        GarmentCo2Response with detailed emission breakdowns for fabric blocks and processes.

    Raises:
        HTTPException: If the garment recipe is not found.
    """

    recipe = get_full_garment_recipe(garment_type_id, material_id)
    if recipe is None:
        raise HTTPException(
            status_code=404,
            detail=f"Garment recipe not found for garment type ID: {garment_type_id}",
        )

    emission_details = GarmentCo2Response(
        fabric_blocks=EmissionDetails(details=[], total_emission=0),
        processes=EmissionDetails(details=[], total_emission=0),
    )

    # Process fabric block emissions
    already_used_fabric_block_ids = []
    for fabric_block_data in recipe.fabric_blocks:
        fabric_block_detail = process_fabric_block_emissions(
            wiser_token,
            fabric_block_data.name,
            fabric_block_data,
            already_used_fabric_block_ids,
        )
        emission_details.fabric_blocks.details.append(fabric_block_detail)
        emission_details.fabric_blocks.total_emission += fabric_block_detail["emission"]

    # Process garment assembly process emissions
    for process in recipe.processes:
        emission_per_unit = get_emission_per_unit(wiser_token, process.activity_id)
        process_emission = (
            emission_per_unit * process.amount if emission_per_unit is not None else 0
        )

        emission_details.processes.details.append(
            {
                "process": process.name,
                "duration": process.amount,
                "activity_id": process.activity_id,
                "emission": process_emission,
            }
        )
        emission_details.processes.total_emission += process_emission

    return emission_details


def calculate_replacement_fabric_blocks_emissions(
    replacement_names: list[str],
    token: str,
    emission_cache: dict[int, float | None],
    material_id: int,
) -> dict:
    """Calculate emissions for replacement fabric blocks for repair scenarios."""
    replacement_fabric_blocks = {"details": [], "total_emission": 0}

    for fabric_block_name in replacement_names:
        # Query fabric block type details
        fabric_block_data = get_fabric_block_recipe(fabric_block_name, material_id)
        if not fabric_block_data:
            continue

        # Get emission for material
        if fabric_block_data.activity_id in emission_cache:
            material_emission_per_unit = emission_cache[fabric_block_data.activity_id]
        else:
            material_emission_per_unit = get_emission_per_unit(
                token, fabric_block_data.activity_id
            )
            if material_emission_per_unit is None:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to fetch emission for activity {fabric_block_data.activity_id}",
                )
            emission_cache[fabric_block_data.activity_id] = material_emission_per_unit

        material_emission = (
            material_emission_per_unit * fabric_block_data.weight_kg
            if material_emission_per_unit is not None
            else 0
        )

        # Get processes for this fabric block
        processes_data = get_fabric_block_processes_for_emission(fabric_block_data.id)

        process_emissions_list = []
        for process_name, process_amount, process_activity_id in processes_data:
            # Get emission for process
            if process_activity_id in emission_cache:
                resource_emission_per_unit = emission_cache[process_activity_id]
            else:
                resource_emission_per_unit = get_emission_per_unit(
                    token, process_activity_id
                )
                if resource_emission_per_unit is None:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to fetch emission for activity {process_activity_id}",
                    )
                emission_cache[process_activity_id] = resource_emission_per_unit

            resource_emissions = (
                resource_emission_per_unit * process_amount
                if resource_emission_per_unit is not None
                else 0
            )

            process_emissions_list.append(
                {
                    "process": process_name,
                    "emission": resource_emissions,
                }
            )

        # Calculate total emissions for this fabric block
        total_processes_emission = sum(p["emission"] for p in process_emissions_list)
        fabric_block_total_emission = material_emission + total_processes_emission

        replacement_fabric_blocks["details"].append(
            {
                "fabric_block": fabric_block_name,
                "material": fabric_block_data.material,
                "amount_kg": fabric_block_data.weight_kg,
                "activity_id": fabric_block_data.activity_id,
                "material_emission": material_emission,
                "processes": process_emissions_list,
            }
        )
        replacement_fabric_blocks["total_emission"] += fabric_block_total_emission

    return replacement_fabric_blocks


def build_scenario_activities(
    transport_distance: float | None,
    amount_kg: float,
    per_unit_emission: float | None,
    replacement_fabric_blocks_data: dict,
) -> list[dict]:
    """
    Build activities list for a scenario, aggregated by activity name.

    Args:
        transport_distance: Distance in km for transport, or None.
        amount_kg: Weight of fabric blocks in kg.
        per_unit_emission: Emission per unit from WISER, or None.
        replacement_fabric_blocks_data: Dictionary with replacement fabric blocks details.

    Returns:
        List of activities with emissions for the scenario.
    """
    activity_map: dict[str, float] = {}

    # Add transport activity
    if transport_distance is not None:
        transport_emission = calculate_transport_emission(
            transport_distance, amount_kg, per_unit_emission
        )
        if transport_emission is not None:
            activity_map["Transport To Customer"] = transport_emission

    # Aggregate replacement fabric block activities by activity name
    for detail in replacement_fabric_blocks_data.get("details", []):
        material_emission = detail.get("material_emission", 0)
        if material_emission > 0:
            # Add material emission under the name "Fabric Block Material"
            activity_map["Fabric Block Material"] = (
                activity_map.get("Fabric Block Material", 0) + material_emission
            )

        # Aggregate process emissions by process name
        for process in detail.get("processes", []):
            process_name = f"Fabric Block {process.get('process', 'Unknown Process')}"
            process_emission = process.get("emission", 0)
            activity_map[process_name] = (
                activity_map.get(process_name, 0) + process_emission
            )

    # Convert aggregated map to activities list
    activities = [
        {
            "name": name,
            "costs": {
                "economic": 0,
                "co2_kg": emission,
            },
        }
        for name, emission in sorted(activity_map.items())
    ]

    return activities
