from urllib.parse import quote

from dash import html, dcc, dash_table

from ceis_dashboard.callbacks.api import fetch_garment_types
from pages.ui import app_topbar, page_hero

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


def get_index_layout():
    inventory_form = html.Div(
        [
            html.H2("Second-hand Fabric Block Inventory"),
            html.Button(
                "Refresh Fabric Blocks",
                id="refresh-fabric-blocks",
                n_clicks=0,
            ),
            dash_table.DataTable(
                id="fabric-blocks-table",
                columns=[
                    {"name": "id", "id": "id"},
                    {"name": "type", "id": "type"},
                    {"name": "material", "id": "material"},
                    {"name": "quality (%)", "id": "quality"},
                    {"name": "co2eq", "id": "co2eq"},
                    {"name": "location", "id": "location"},
                    {
                        "name": "processes",
                        "id": "processes",
                    },
                ],
                data=[],  # populated via callback
                style_table={"overflowX": "auto"},
                style_cell={"textAlign": "center", "padding": "10px"},
                style_header={"fontWeight": "bold"},
            ),
        ],
        className="panel table-panel",
    )

    fabric_form = html.Div(
        [
            html.H2("Add Second-hand Fabric Blocks to inventory"),
            html.Div(
                [
                    html.Div(
                        [
                            html.Label("Type"),
                            dcc.Dropdown(
                                id="fabric-type",
                                options=[],
                                placeholder="Select a fabric type",
                            ),
                        ],
                        className="field-panel",
                    ),
                    html.Div(
                        [
                            html.Label("Location"),
                            dcc.Dropdown(
                                id="fabric-location",
                                options=[],
                                placeholder="Select a location",
                                clearable=True,
                            ),
                        ],
                        className="field-panel",
                    ),
                    html.Div(
                        [
                            html.Label("Material"),
                            dcc.Dropdown(
                                id="fabric-material",
                                options=[],
                                placeholder="Select a material",
                                clearable=True,
                            ),
                        ],
                        className="field-panel",
                    ),
                    html.Div(
                        [
                            html.Label("Quality (%)"),
                            dcc.Input(
                                id="fabric-quality",
                                type="number",
                                min=0,
                                max=100,
                                step=1,
                                value=100,
                                placeholder="e.g., 95",
                            ),
                        ],
                        className="field-panel",
                    ),
                ],
                className="form-grid",
            ),
            html.H3("Processes"),
            html.Div(id="processes-container", children=[]),
            html.Div(
                [
                    html.Button("Add Process", id="add-process-button", n_clicks=0),
                    html.Button(
                        "Remove Last Process",
                        id="remove-process-button",
                        n_clicks=0,
                    ),
                ],
                className="button-row",
            ),
            html.Button("Add Fabric Block", id="add-fabric-blocks", n_clicks=0),
            html.Div(
                id="fabric-add-status", style={"marginTop": "8px", "color": "green"}
            ),
            html.H3("Remove Second-hand Fabric Block"),
            html.Div(
                [
                    html.Label("Fabric block"),
                    dcc.Dropdown(
                        id="delete-fabric-block-id",
                        options=[],
                        placeholder="Select a fabric block",
                        clearable=False,
                    ),
                    html.Button(
                        "Remove Fabric Block",
                        id="delete-fabric-block-button",
                        n_clicks=0,
                    ),
                    html.Div(
                        id="fabric-remove-status",
                        style={"marginTop": "8px", "color": "green"},
                    ),
                ],
                className="field-panel",
            ),
        ],
        className="fabric-add-form",
    )

    garment_types = fetch_garment_types()
    co2_cards = [
        dcc.Link(
            href=f"/co2/{garment['id']}",
            children=html.Div(
                [
                    html.Div(
                        _assessment_image(garment["name"]),
                        className="product-thumb",
                    ),
                    html.Div(garment["name"], className="product-label"),
                ],
                className="product assessment-product",
            ),
        )
        for garment in garment_types
    ]

    co2_form = html.Div(
        [
            html.H2("CO2 Assessment"),
            html.P("Select a garment to review its material and process emissions."),
            (
                html.Div(co2_cards, className="assessment-grid")
                if co2_cards
                else html.Div(
                    "No garment types available.",
                    className="panel-muted",
                )
            ),
        ],
        className="panel",
    )

    return html.Div(
        [
            app_topbar(),
            page_hero(
                "Operations",
                "Welcome",
                "Manage reusable fabric inventory, recipe references, and garment-level assessments from one cockpit.",
            ),
            inventory_form,
            fabric_form,
            co2_form,
        ],
        className="wrapper inventory-page",
    )


def _assessment_image(garment_name: str):
    file_name = GARMENT_IMAGE_MAP.get(garment_name)
    if not file_name:
        return html.Div("Image pending", className="product-image-fallback")

    encoded_name = quote(file_name)
    return html.Img(
        src=f"/assets/Garment Photos/{encoded_name}",
        alt=garment_name,
    )
