from urllib.parse import quote

import requests
from dash import html, dcc

from ceis_shop import config
from ceis_shop.layouts.garment import GARMENT_IMAGE_MAP


def _fetch_garment_types() -> list[dict]:
    response = requests.get(f"{config.BACKEND_API_URL}/garment-types", timeout=30)
    response.raise_for_status()
    garments = response.json()
    return sorted(garments, key=lambda g: g.get("name", ""))


def home_page():
    try:
        garment_types = _fetch_garment_types()
        product_links = [
            dcc.Link(
                href=f"/garment/{garment['id']}",
                children=html.Div(
                    className="product",
                    children=[
                        html.Div(
                            _product_image(garment["name"]),
                            className="product-thumb",
                        ),
                        html.Div(garment["name"], className="product-label"),
                    ],
                ),
            )
            for garment in garment_types
        ]
    except Exception:
        product_links = [
            html.Div(
                "Unable to load garments from backend.",
                className="product-label",
            )
        ]

    return html.Div(
        className="wrapper",
        children=[
            html.Header(
                [
                    html.Div("Circular Lab Shop", className="brand"),
                    html.Nav(
                        [
                            dcc.Link("Home", href="/", className="home-nav-link"),
                            dcc.Link("End of life", href="/scenarios"),
                        ],
                        className="shop-actions",
                    ),
                ],
                className="shop-topbar",
            ),
            html.Section(
                className="shop-hero",
                children=[
                    html.Div(
                        "Made-to-order circular garments", className="shop-kicker"
                    ),
                    html.H1(
                        "Welcome to Our Clothing Order Website",
                        className="header-title",
                    ),
                    html.P(
                        "Choose a garment, compare material options, and see the recipe, CO2 impact, and circular alternatives before ordering.",
                        className="shop-intro",
                    ),
                ],
            ),
            html.Section(
                className="panel",
                children=[
                    html.Div(
                        className="order-form",
                        children=product_links,
                    ),
                ],
            ),
            html.Section(
                className="panel-muted",
                children=[
                    html.H2("Circular services"),
                    html.P(
                        "Explore repair and return routes for garments at the end of use."
                    ),
                    dcc.Link(
                        "View End of Life Options",
                        href="/scenarios",
                        className="back-link",
                    ),
                ],
            ),
        ],
    )


def _product_image(garment_name: str):
    file_name = GARMENT_IMAGE_MAP.get(garment_name)
    if not file_name:
        return html.Div("Image pending", className="product-image-fallback")

    encoded_name = quote(file_name)
    return html.Img(
        src=f"/assets/Garment Photos/{encoded_name}",
        alt=garment_name,
    )
