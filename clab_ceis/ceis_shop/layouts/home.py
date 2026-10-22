from urllib.parse import quote

import requests
from dash import dcc, html

from ceis_shop import config
from ceis_shop.layouts.garment import GARMENT_IMAGE_MAP
from ceis_shop.layouts.ui import shop_topbar

SECOND_COLLECTION_NAMES = (
    "Basic Trousers",
    "Cocktail fitted dress",
    "Elegant cowl neck top",
    "Full Trousers",
    "Long tabard",
    "Wrap Skirt",
)

FIRST_COLLECTION_NAMES = (
    "Mangata Dress",
    "Måne top",
    "Nordlys Dress",
    "Orka jacket",
)


def _fetch_garment_types() -> list[dict]:
    response = requests.get(f"{config.BACKEND_API_URL}/garment-types", timeout=30)
    response.raise_for_status()
    garments = response.json()
    return sorted(garments, key=lambda g: g.get("name", ""))


def _product_card(garment: dict):
    price = garment.get("price_chf")
    return dcc.Link(
        href=f"/garment/{garment['id']}",
        className="product-link",
        children=html.Article(
            className="product",
            children=[
                html.Div(
                    [
                        _product_image(garment["name"]),
                    ],
                    className="product-thumb",
                ),
                html.Div(
                    [
                        html.Div(garment["name"], className="product-label"),
                        html.Div(
                            f"CHF {float(price):.2f}"
                            if price is not None
                            else "Price on request",
                            className="product-price",
                        ),
                    ],
                    className="product-card-copy",
                ),
            ],
        ),
    )


def _collection_group(title: str, garments: list[dict]):
    return html.Div(
        [
            html.H3(title, className="collection-group-title"),
            html.Div(
                className="order-form",
                children=[_product_card(garment) for garment in garments],
            ),
        ],
        className="collection-group",
    )


def home_page():
    try:
        garment_types = _fetch_garment_types()
        garments_by_name = {
            garment["name"]: garment
            for garment in garment_types
            if garment.get("name") in GARMENT_IMAGE_MAP
        }
        collection_groups = []
        for title, garment_names in (
            ("Second collection", SECOND_COLLECTION_NAMES),
            ("First collection", FIRST_COLLECTION_NAMES),
        ):
            garments = [
                garments_by_name[name]
                for name in garment_names
                if name in garments_by_name
            ]
            if garments:
                collection_groups.append(_collection_group(title, garments))
    except Exception:
        collection_groups = [
            html.Div(
                "We could not load the collection. Please try again shortly.",
                className="collection-error",
            )
        ]

    return html.Div(
        className="wrapper shop-page shop-home-page",
        children=[
            shop_topbar("shop"),
            html.Section(
                className="shop-hero home-hero",
                children=[
                    html.Div(
                        [
                            html.Div(
                                "Circular clothing, designed to return",
                                className="shop-kicker",
                            ),
                            html.H1(
                                "Choose clothes with a life beyond the first wear.",
                                className="header-title",
                            ),
                            html.P(
                                "Explore circular garments, compare their climate impact, and save with available second-life alternatives.",
                                className="shop-intro",
                            ),
                            dcc.Link(
                                "Browse the collection",
                                href="#collection",
                                className="primary-link",
                            ),
                        ],
                        className="shop-hero-copy",
                    ),
                    html.Div(
                        [
                            html.Div(
                                "Designed for long use", className="hero-proof-item"
                            ),
                            html.Div(
                                "Lower-impact choices", className="hero-proof-item"
                            ),
                            html.Div(
                                "Repair & return support", className="hero-proof-item"
                            ),
                        ],
                        className="hero-proof",
                    ),
                ],
            ),
            html.Section(
                id="collection",
                className="shop-collection",
                children=[
                    html.Div(
                        [
                            html.Div("The collection", className="section-eyebrow"),
                            html.H2("Find your next long-life garment"),
                            html.P(
                                "Each piece can be configured before you order.",
                                className="section-intro",
                            ),
                        ],
                        className="section-heading",
                    ),
                    *collection_groups,
                ],
            ),
            html.Section(
                className="circular-care-banner",
                children=[
                    html.Div(
                        [
                            html.Div("Keep it in use", className="section-eyebrow"),
                            html.H2("Already own a Circular Lab garment?"),
                            html.P(
                                "Compare repair, return, and replacement options before deciding what comes next."
                            ),
                        ]
                    ),
                    html.Div(
                        [
                            dcc.Link(
                                "Explore circular care",
                                href="/repair-return",
                                className="primary-link light",
                            ),
                            dcc.Link(
                                "See the impact guide →",
                                href="/scenarios",
                                className="text-link-light",
                            ),
                        ],
                        className="shop-actions",
                    ),
                ],
            ),
        ],
    )


def _product_image(garment_name: str):
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
