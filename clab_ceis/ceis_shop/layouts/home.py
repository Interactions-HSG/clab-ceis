import requests
from dash import html, dcc

from ceis_shop import config


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
                html.H1(
                    "Welcome to Our Clothing Order Website", className="header-title"
                ),
                className="card",
            ),
            html.Div(
                className="card",
                children=[
                    html.H2("Select the Type of Clothing You Want to Order"),
                    html.Div(
                        className="order-form",
                        children=product_links,
                        style={"display": "flex", "gap": "20px", "flex-wrap": "wrap"},
                    ),
                ],
            ),
            html.Div(
                className="card",
                children=[
                    html.H2("End of Life Options"),
                    html.P(
                        "Manufacturer: Bucharest, Repair Center: St. Gallen, Consumer: Sigmaringen."
                    ),
                    dcc.Loading(
                        id="customer-repair-loading",
                        type="circle",
                        children=html.Div(id="customer-repair-content"),
                        color="green",
                    ),
                ],
            ),
        ],
    )
