from collections import Counter
from urllib.parse import quote

import requests
from dash import dcc, html

from ceis_shop import config

# Map seeded garments to existing shop asset photos where available.
GARMENT_IMAGE_MAP = {
    "Basic Trousers": "1. Basic trousers.JPG",
    "Full Trousers": "2. Full Trousers.JPG",
    "Elegant cowl neck top": "5. Elegant cowl neck top.JPG",
    "Wrap Skirt": "7. Wrap Skirt.JPG",
    "Cocktail fitted dress": "9. Cocktail fitted dress.jpg",
    "Long tabard": "10. Long Tabard.JPG",
    "Orka jacket": "12. Orka jacket Refashion by SOLVE (1).jpg",
    "Nordlys Dress": "13. Nordlys dress.jpg",
    "Mangata Dress": "14. Mångata dress Refashion by SOLVE (1).jpg",
    "Måne top": "15. Måne top Refashion SOLVE (2).jpg",
}


def _fetch_json(path: str):
    response = requests.get(f"{config.BACKEND_API_URL}{path}", timeout=30)
    response.raise_for_status()
    return response.json()


def _format_fabric_blocks_from_co2(co2_payload: dict) -> list[html.Li]:
    block_counter: Counter[str] = Counter()
    for detail in co2_payload.get("fabric_blocks", {}).get("details", []):
        block_name = detail.get("fabric_block")
        if block_name:
            block_counter[block_name] += 1

    return [
        html.Li(f"{block_name} x {count}")
        for block_name, count in sorted(block_counter.items())
    ]


def render_recipe_content(co2_payload: dict) -> html.Div:
    fabric_blocks = _format_fabric_blocks_from_co2(co2_payload)

    return html.Div(
        children=[
            html.H3("Recipe"),
            html.Ul(fabric_blocks or [html.Li("No fabric blocks found.")]),
        ]
    )


def render_co2_content(selected_material_name: str, co2_payload: dict) -> html.Div:

    fabric_blocks_total = co2_payload.get("fabric_blocks", {}).get("total_emission", 0)
    processes_total = co2_payload.get("processes", {}).get("total_emission", 0)
    total_emission = fabric_blocks_total + processes_total

    return html.Div(
        children=[
            html.H3("CO2 Emissions"),
            html.P(f"Material for CO2 calculation: {selected_material_name}."),
            html.P(f"Total: {total_emission:.3f} kg CO2eq"),
        ]
    )


def render_waiting_for_material_co2_content() -> html.Div:
    return html.Div(
        [
            html.H3("CO2 Emissions"),
            html.P("Select a material to view total CO2."),
        ]
    )


def _image_component(garment_name: str):
    file_name = GARMENT_IMAGE_MAP.get(garment_name)
    if not file_name:
        return html.Div("No image available.", className="product-image-fallback")

    encoded_name = quote(file_name)
    return html.Img(
        src=f"/assets/Garment Photos/{encoded_name}",
        alt=garment_name,
        style={"width": "100%", "border-radius": "8px"},
    )


def garment_page(garment_type_id: int):
    try:
        garment_types = _fetch_json("/garment-types")
        garment = next(
            (g for g in garment_types if g.get("id") == garment_type_id), None
        )
        if not garment:
            return html.Div("Garment not found.")

        materials = _fetch_json(f"/garment-types/{garment_type_id}/materials")
        if not materials:
            return html.Div(
                [
                    html.H1(garment["name"], className="product-title"),
                    html.P("No materials configured for this garment."),
                    dcc.Link("Back to Home", href="/", className="back-link"),
                ],
                className="product-detail",
            )

        material_options = [
            {"label": material["name"], "value": material["id"]}
            for material in materials
        ]
        # Recipe does not depend on selected material, so render it once from any valid material.
        recipe_seed_material = materials[0]
        recipe_payload = _fetch_json(
            f"/co2/{garment_type_id}?material_id={recipe_seed_material['id']}"
        )
        recipe_content = render_recipe_content(recipe_payload)
        initial_co2_content = render_waiting_for_material_co2_content()

        return html.Div(
            className="product-detail",
            children=[
                html.H1(garment["name"], className="product-title"),
                dcc.Store(id="garment-type-id-store", data=garment_type_id),
                dcc.Store(id="garment-materials-store", data=materials),
                html.Div(
                    [
                        html.Label("Material", htmlFor="garment-material-dropdown"),
                        dcc.Dropdown(
                            id="garment-material-dropdown",
                            options=material_options,
                            value=None,
                            placeholder="Select a material",
                            clearable=True,
                        ),
                    ],
                    className="form-actions",
                ),
                html.Div(
                    className="product-content",
                    children=[
                        html.Div(
                            className="product-image",
                            children=_image_component(garment["name"]),
                        ),
                        html.Div(
                            className="product-description",
                            children=[
                                html.Div(id="garment-recipe-content", children=recipe_content),
                                dcc.Loading(
                                    id="garment-co2-loading",
                                    type="circle",
                                    children=html.Div(
                                        id="garment-co2-content",
                                        children=initial_co2_content,
                                    ),
                                ),
                            ],
                        ),
                    ],
                ),
                dcc.Link("Back to Home", href="/", className="back-link"),
            ],
        )
    except Exception as exc:
        return html.Div(
            className="product-detail",
            children=[
                html.H1("Unable to load garment"),
                html.P(str(exc)),
                dcc.Link("Back to Home", href="/", className="back-link"),
            ],
        )
