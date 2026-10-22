from collections import Counter
from urllib.parse import quote

import requests
from dash import dcc, html

from ceis_shop import config
from ceis_shop.layouts.ui import shop_home_link, shop_topbar

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


def _format_fabric_blocks(recipe_payload: list[dict]) -> tuple[int, int]:
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

    return sum(block_counter.values()), len(block_counter)


def render_recipe_content(recipe_payload: list[dict]) -> html.Div:
    piece_count, shape_count = _format_fabric_blocks(recipe_payload)

    return html.Div(
        children=[
            html.Div("How it is made", className="section-eyebrow"),
            html.H3("Cut efficiently, built for longevity"),
            html.P(
                (
                    f"This garment is assembled from {piece_count} fabric pieces "
                    f"across {shape_count} cut shapes."
                    if piece_count
                    else "Construction information is not available yet."
                )
            ),
        ],
        className="construction-summary",
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


def _format_condition(quality: float) -> str:
    """Translate the internal quality score into customer-friendly condition text."""
    if quality >= 90:
        return "excellent condition"
    if quality >= 75:
        return "very good condition"
    if quality >= 50:
        return "good condition"
    return "fair condition"


def _build_alternative_fabric_block_items(co2_payload: dict) -> list[html.Div]:
    items: list[html.Div] = []

    for detail in co2_payload.get("fabric_blocks", {}).get("details", []):
        alternative = detail.get("alternative") or {}
        alternative_id = alternative.get("id")
        quality = alternative.get("quality")
        alternative_material = alternative.get("material") or "unknown material"

        if alternative_id is None or quality is None:
            continue
        quality_score = float(quality)
        if quality_score >= 100:
            continue

        items.append(
            html.Div(
                [
                    html.Strong(f"Second-life {alternative_material}"),
                    html.Span(_format_condition(quality_score)),
                ],
                className="alternative-item",
            )
        )

    return items


def _get_alternative_emissions(co2_payload: dict) -> float | None:
    alternative_total = co2_payload.get("processes", {}).get("total_emission", 0.0)
    has_alternative = False

    for detail in co2_payload.get("fabric_blocks", {}).get("details", []):
        alternative = detail.get("alternative") or {}
        if alternative.get("id") is not None:
            alternative_total += float(alternative.get("emission", 0))
            has_alternative = True
        else:
            alternative_total += float(detail.get("emission", 0))

    return alternative_total if has_alternative else None


def render_co2_content(
    selected_material_name: str,
    co2_payload: dict,
    base_price_chf: float | None = None,
    material_cost_per_sqm_chf: float | None = None,
) -> html.Div:
    try:
        fabric_blocks_total = co2_payload["fabric_blocks"]["total_emission"]
        processes_total = co2_payload["processes"]["total_emission"]
    except KeyError as exc:
        raise ValueError(f"Missing CO2 payload field: {exc}") from exc

    total_emission = fabric_blocks_total + processes_total
    alternative_emission = _get_alternative_emissions(co2_payload)
    co2_saved = (
        total_emission - alternative_emission
        if alternative_emission is not None
        else None
    )
    discount_rate = _get_discount_rate(co2_payload)
    discounted_price = (
        base_price_chf * (1 - discount_rate) if base_price_chf is not None else None
    )
    alternative_items = _build_alternative_fabric_block_items(co2_payload)

    return html.Div(
        children=[
            (
                html.Section(
                    [
                        html.Div(
                            f"SAVE {int(discount_rate * 100)}%",
                            className="discount-badge",
                        ),
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.Div(
                                            "Best circular choice",
                                            className="section-eyebrow",
                                        ),
                                        html.H3(
                                            "Choose available second-life fabric"
                                        ),
                                        html.P(
                                            f"Pay CHF {discounted_price:.2f} instead of CHF {base_price_chf:.2f} and save {co2_saved:.3f} kg CO2eq.",
                                            className="alternative-lead",
                                        ),
                                    ]
                                ),
                                html.Div(
                                    [
                                        html.Span(
                                            f"CHF {discounted_price:.2f}",
                                            className="discount-price",
                                        ),
                                        html.Span(
                                            f"CHF {base_price_chf:.2f}",
                                            className="original-price",
                                        ),
                                    ],
                                    className="price-stack",
                                ),
                            ],
                            className="alternative-offer-heading",
                        ),
                        html.Div(alternative_items, className="alternative-list"),
                        html.P(
                            f"Estimated impact: {alternative_emission:.3f} kg CO2eq with the currently available alternatives.",
                            className="alternative-impact",
                        ),
                    ],
                    className="alternative-offer",
                )
                if alternative_emission is not None
                and co2_saved is not None
                and discounted_price is not None
                and alternative_items
                else html.Div(
                    [
                        html.H3("No second-life fabric available right now"),
                        html.P(
                            "You can still order this garment in your selected material."
                        ),
                    ],
                    className="availability-note",
                )
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.Span("Selected material", className="impact-label"),
                            html.Strong(selected_material_name),
                        ],
                        className="impact-stat",
                    ),
                    html.Div(
                        [
                            html.Span("Estimated impact", className="impact-label"),
                            html.Strong(f"{total_emission:.3f} kg CO2eq"),
                        ],
                        className="impact-stat",
                    ),
                ],
                className="impact-strip",
            ),
        ],
        className="purchase-impact",
    )


def render_waiting_for_material_co2_content() -> html.Div:
    return html.Div(
        [
            html.H3("See your price and impact"),
            html.P(
                "Choose a material to reveal available second-life alternatives and savings."
            ),
        ],
        className="availability-note",
    )


def render_returned_garment_comparison(payload: dict) -> html.Div:
    """Render the like-for-like climate comparison for a returned garment."""
    returned_total = float(payload["returned_total_co2eq"])
    new_total = float(payload["new_total_co2eq"])
    saving = float(payload["saving_co2eq"])
    saving_percent = float(payload["saving_percent"])

    return html.Div(
        [
            html.Div(
                [
                    html.Div(
                        [
                            html.Span("CO2 saved", className="impact-label"),
                            html.Strong(
                                f"{saving:.3f} kg ({saving_percent:.1f}%)"
                            ),
                        ],
                        className="impact-stat positive",
                    ),
                    html.Div(
                        [
                            html.Span(
                                "Second-life garment", className="impact-label"
                            ),
                            html.Strong(f"{returned_total:.3f} kg CO2eq"),
                        ],
                        className="impact-stat",
                    ),
                    html.Div(
                        [
                            html.Span("Equivalent new", className="impact-label"),
                            html.Strong(f"{new_total:.3f} kg CO2eq"),
                        ],
                        className="impact-stat",
                    ),
                ],
                className="impact-strip",
            ),
        ],
        className="returned-impact-comparison",
    )


def _render_returned_garment_offer(returned_garments: list[dict]) -> html.Div:
    if not returned_garments:
        return html.Div(
            [
                dcc.Dropdown(id="returned-garment-dropdown", options=[]),
                html.Div(id="returned-garment-comparison"),
                html.Button(
                    "Order returned garment",
                    id="returned-garment-order-button",
                    n_clicks=0,
                ),
                html.Div(id="returned-garment-order-result"),
            ],
            id="returned-garment-offer",
            hidden=True,
        )

    selected = returned_garments[0]
    options = [
        {
            "label": f"Second-life {selected['garment']}",
            "value": selected["id"],
        }
    ]
    return html.Div(
        [
            html.Div("50% OFF · ONE AVAILABLE", className="discount-badge"),
            html.Div("Whole-garment alternative", className="section-eyebrow"),
            html.H2("Give a returned garment its next life"),
            html.P(
                "Professionally prepared and ready to wear, with no new fabric required."
            ),
            dcc.Dropdown(
                id="returned-garment-dropdown",
                options=options,
                value=selected["id"],
                clearable=False,
                disabled=True,
            ),
            html.Div(
                [
                    html.Span(
                        f"CHF {float(selected['price_chf']):.2f}",
                        className="discount-price",
                    ),
                    html.Span(
                        f"CHF {float(selected['base_price_chf']):.2f}",
                        className="original-price",
                    ),
                ],
                className="price-stack horizontal",
            ),
            html.P(
                "Choosing the returned garment avoids new-fabric emissions.",
                className="alternative-impact",
            ),
            html.Div(
                "Select a material above to compare it with the equivalent new garment.",
                id="returned-garment-comparison",
                className="returned-comparison-slot",
            ),
            html.Button(
                "Order returned garment",
                id="returned-garment-order-button",
                n_clicks=0,
                className="primary-button",
            ),
            html.Div(id="returned-garment-order-result"),
        ],
        id="returned-garment-offer",
        className="returned-garment-offer",
    )


def _image_component(garment_name: str):
    file_name = GARMENT_IMAGE_MAP.get(garment_name)
    if not file_name:
        return html.Div(
            [
                html.Span("CL", className="fallback-monogram"),
                html.Span(garment_name, className="fallback-name"),
            ],
            className="product-image-fallback",
        )

    encoded_name = quote(file_name)
    return html.Img(
        src=f"/assets/Garment Photos/{encoded_name}",
        alt=garment_name,
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
                    shop_topbar("shop"),
                    html.Section(
                        [
                            html.Div(
                                [
                                    html.Div(
                                        "Garment configurator",
                                        className="shop-kicker",
                                    ),
                                    html.H1(
                                        garment["name"],
                                        className="product-title",
                                    ),
                                ],
                                className="shop-hero-copy",
                            ),
                            shop_home_link(),
                        ],
                        className="shop-hero shop-hero-with-action",
                    ),
                    html.P("No materials configured for this garment."),
                ],
                className="product-detail shop-page garment-page",
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
                    html.H3("How it is made"),
                    html.P("Construction details are unavailable right now."),
                    html.P(str(exc)),
                ],
                className="construction-summary",
            )
        try:
            returned_garments = _fetch_json(
                f"/garment-types/{garment_type_id}/returned-garments"
            )
        except Exception:
            returned_garments = []
        initial_co2_content = render_waiting_for_material_co2_content()

        return html.Div(
            className="product-detail shop-page garment-page",
            children=[
                shop_topbar("shop"),
                html.Section(
                    [
                        html.Div(
                            [
                                html.Div(
                                    "Circular garment", className="shop-kicker"
                                ),
                                html.H1(garment["name"], className="product-title"),
                                html.P(
                                    "Choose your material, compare its impact, and check whether a lower-price second-life option is available.",
                                    className="shop-intro",
                                ),
                            ],
                            className="shop-hero-copy",
                        ),
                        shop_home_link(),
                    ],
                    className="shop-hero shop-hero-with-action",
                ),
                dcc.Store(id="garment-type-id-store", data=garment_type_id),
                dcc.Store(id="garment-materials-store", data=materials),
                dcc.Store(id="garment-base-price-store", data=garment.get("price_chf")),
                dcc.Store(id="returned-garments-store", data=returned_garments),
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
                                    html.Div(
                                        [
                                            html.Div(
                                                "Garment price",
                                                className="purchase-price-label",
                                            ),
                                            html.Div(
                                                f"CHF {float(garment['price_chf']):.2f}",
                                                className="purchase-price",
                                            ),
                                            html.P(
                                                "Second-life materials may unlock a lower price after you choose a material.",
                                                className="purchase-price-note",
                                            ),
                                        ],
                                        className="purchase-price-card",
                                    )
                                    if garment.get("price_chf") is not None
                                    else html.P("Base price unavailable.")
                                ),
                                html.Div(
                                    [
                                        html.Label(
                                            "Choose a material",
                                            htmlFor="garment-material-dropdown",
                                        ),
                                        dcc.Dropdown(
                                            id="garment-material-dropdown",
                                            options=material_options,
                                            value=selected_material_id,
                                            placeholder="Select a material",
                                            clearable=True,
                                        ),
                                        html.P(
                                            "We will immediately show available alternatives and savings.",
                                            className="field-help",
                                        ),
                                    ],
                                    className="material-choice",
                                ),
                                dcc.Loading(
                                    id="garment-co2-loading",
                                    type="circle",
                                    children=html.Div(
                                        id="garment-co2-content",
                                        children=initial_co2_content,
                                    ),
                                ),
                                html.Button(
                                    "Order garment",
                                    id="garment-order-button",
                                    n_clicks=0,
                                    className="primary-button",
                                ),
                                html.Div(id="garment-order-result"),
                                _render_returned_garment_offer(returned_garments),
                                html.Div(
                                    id="garment-recipe-content", children=recipe_content
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        )
    except Exception as exc:
        return html.Div(
            className="product-detail shop-page garment-page",
            children=[
                shop_topbar("shop"),
                html.Section(
                    [
                        html.Div(
                            [
                                html.Div(
                                    "Garment configurator",
                                    className="shop-kicker",
                                ),
                                html.H1(
                                    "Unable to load garment",
                                    className="product-title",
                                ),
                                html.P(str(exc), className="shop-intro"),
                            ],
                            className="shop-hero-copy",
                        ),
                        shop_home_link(),
                    ],
                    className="shop-hero shop-hero-with-action",
                ),
            ],
        )
