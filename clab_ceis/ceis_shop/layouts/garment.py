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


def _format_fabric_blocks(recipe_payload: list[dict]) -> list[html.Li]:
    block_counter: Counter[str] = Counter()
    for index, detail in enumerate(recipe_payload):
        block_name = detail.get("fabric_block")
        amount = detail.get("amount")

        if not block_name:
            raise ValueError(f"Missing fabric_block in recipe item {index}.")
        if amount is None:
            raise ValueError(f"Missing amount for fabric block '{block_name}'.")
        if not isinstance(amount, int) or amount <= 0:
            raise ValueError(
                f"Invalid amount '{amount}' for fabric block '{block_name}'."
            )

        block_counter[block_name] += amount

    return [
        html.Li(f"{block_name} x {count}")
        for block_name, count in sorted(block_counter.items())
    ]


def render_recipe_content(recipe_payload: list[dict]) -> html.Div:
    fabric_blocks = _format_fabric_blocks(recipe_payload)

    return html.Div(
        children=[
            html.H3("Fabric Blocks"),
            html.Ul(fabric_blocks or [html.Li("No fabric blocks found.")]),
        ]
    )


def _get_discount_rate(co2_payload: dict) -> float:
    fabric_block_details = co2_payload.get("fabric_blocks", {}).get("details", [])
    lower_quality_blocks = 0

    for detail in fabric_block_details:
        alternative = detail.get("alternative") or {}
        quality = alternative.get("quality")
        if quality is not None and float(quality) < 100:
            lower_quality_blocks += 1

    return min(
        lower_quality_blocks * 0.2, 0.6
    )  # 20% discount per lower-quality block, capped at 60% total discount


def _build_alternative_fabric_block_items(co2_payload: dict) -> list[html.Li]:
    items: list[html.Li] = []

    for detail in co2_payload.get("fabric_blocks", {}).get("details", []):
        alternative = detail.get("alternative") or {}
        alternative_id = alternative.get("id")
        quality = alternative.get("quality")
        alternative_material = alternative.get("material") or "unknown material"

        if alternative_id is None or quality is None:
            continue
        if float(quality) >= 100:
            continue

        items.append(
            html.Li(
                f"{detail.get('fabric_block', 'Unknown')} can be replaced by a "
                f"second-life {alternative_material} block "
                f"with quality {float(quality):.0f} %"
            )
        )

    return items


def render_co2_content(
    selected_material_name: str, co2_payload: dict, base_price_chf: float | None = None
) -> html.Div:
    try:
        fabric_blocks_total = co2_payload["fabric_blocks"]["total_emission"]
        processes_total = co2_payload["processes"]["total_emission"]
    except KeyError as exc:
        raise ValueError(f"Missing CO2 payload field: {exc}") from exc

    total_emission = fabric_blocks_total + processes_total
    discount_rate = _get_discount_rate(co2_payload)
    discounted_price = (
        base_price_chf * (1 - discount_rate) if base_price_chf is not None else None
    )
    alternative_items = _build_alternative_fabric_block_items(co2_payload)

    return html.Div(
        children=[
            html.H3("CO2 Emissions"),
            html.P(f"Material for CO2 calculation: {selected_material_name}."),
            html.P(f"Total: {total_emission:.3f} kg CO2eq"),
            html.H3("Alternatives"),
            html.Ul(
                alternative_items
                or [html.Li("No second-life fabric block replacements available.")]
            ),
            (
                html.P(
                    f"Price: CHF {discounted_price:.2f} "
                    f"({int(discount_rate * 100)}% discount from CHF {base_price_chf:.2f})"
                )
                if discounted_price is not None
                else html.P("Price unavailable.")
            ),
        ]
    )


def render_waiting_for_material_co2_content() -> html.Div:
    return html.Div(
        [
            html.H3("CO2 Emissions"),
            html.P("Select a material to view CO2 emissions."),
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
        selected_material = materials[0] if len(materials) == 1 else None
        selected_material_id = (
            selected_material.get("id") if selected_material is not None else None
        )
        try:
            recipe_payload = _fetch_json(
                f"/garment-types/{garment_type_id}/fabric-blocks"
            )
            recipe_content = render_recipe_content(recipe_payload)
        except Exception as exc:
            recipe_content = html.Div(
                [
                    html.H3("Fabric Blocks"),
                    html.P("Unable to load recipe details."),
                    html.P(str(exc)),
                ]
            )
        initial_co2_content = render_waiting_for_material_co2_content()

        return html.Div(
            className="product-detail",
            children=[
                html.H1(garment["name"], className="product-title"),
                dcc.Store(id="garment-type-id-store", data=garment_type_id),
                dcc.Store(id="garment-materials-store", data=materials),
                dcc.Store(id="garment-base-price-store", data=garment.get("price_chf")),
                html.Div(
                    [
                        html.Label("Material", htmlFor="garment-material-dropdown"),
                        dcc.Dropdown(
                            id="garment-material-dropdown",
                            options=material_options,
                            value=selected_material_id,
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
                                (
                                    html.P(
                                        f"Base price: CHF {float(garment['price_chf']):.2f}"
                                    )
                                    if garment.get("price_chf") is not None
                                    else html.P("Base price unavailable.")
                                ),
                                html.Div(
                                    id="garment-recipe-content", children=recipe_content
                                ),
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
