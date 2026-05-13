from dash import html, dcc, dash_table

from ceis_dashboard.callbacks.api import fetch_garment_types
from pages.ui import app_topbar, page_hero


def get_index_layout():
    inventory_form = html.Div(
        [
            html.Div(
                [
                    dcc.Link(
                        "Lifecycle Strategy Board",
                        href="/dashboard",
                        id="dashboard-link",
                    ),
                    dcc.Link(
                        "Garment Scenario Planner",
                        href="/designer-balance",
                        id="designer-balance-link",
                    ),
                    dcc.Link(
                        "New Garment Designer",
                        href="/garment-designer",
                        id="garment-designer-link",
                    ),
                    dcc.Link(
                        "Add Recipe",
                        href="/add-recipe",
                        id="add-recipe-link",
                    ),
                ],
                className="nav-links",
            ),
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
                    {"name": "garment_id", "id": "garment_id"},
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
    co2_links = [
        html.Li(
            dcc.Link(
                f"{garment['name']} CO2 Assessment",
                href=f"/co2/{garment['id']}",
            )
        )
        for garment in garment_types
    ]

    co2_form = html.Div(
        [
            html.H2("CO2 Assessment"),
            html.P("Open a garment page to view its CO2 details."),
            html.Ul(co2_links or [html.Li("No garment types available.")]),
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
            html.Div([fabric_form, co2_form], className="dashboard-grid"),
        ],
        className="wrapper",
    )
