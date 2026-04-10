from dash import html, dcc, dash_table

from ceis_dashboard.callbacks.api import fetch_garment_types


def get_index_layout():
    inventory_form = html.Div(
        [
            dcc.Link(
                "CE Flow Cockpit",
                href="/dashboard",
                id="dashboard-link",
            ),
            html.Br(),
            dcc.Link(
                "Designer Balance",
                href="/designer-balance",
                id="designer-balance-link",
            ),
            html.H1("Welcome"),
            dcc.Link(
                "Add Recipe",
                href="/add-recipe",
                id="add-recipe-link",
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
                style_table={"maxWidth": "800px"},
                style_cell={"textAlign": "center"},
                style_header={"fontWeight": "bold"},
            ),
        ],
    )

    fabric_form = html.Div(
        [
            html.H2("Add Second-hand Fabric Blocks to inventory"),
            html.Div(
                [
                    html.Label("Type"),
                    dcc.Dropdown(
                        id="fabric-type",
                        options=[
                            # {"label": "Fabric Block 1", "value": "1"},
                            # {"label": "Fabric Block 2", "value": "2"},
                            # {"label": "Fabric Block 3", "value": "FB3"},
                            # {"label": "Fabric Block 4", "value": "FB4"},
                        ],
                        placeholder="Select a fabric type",
                    ),
                ],
                style={"marginBottom": "12px", "maxWidth": "400px"},
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
                style={"marginBottom": "12px", "maxWidth": "400px"},
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
                style={"marginBottom": "12px", "maxWidth": "400px"},
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
                style={"marginBottom": "12px", "maxWidth": "400px"},
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
                style={
                    "marginTop": "8px",
                    "marginBottom": "12px",
                    "display": "flex",
                    "gap": "8px",
                },
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
                style={"marginTop": "12px", "maxWidth": "400px"},
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
        ]
    )

    return html.Div(
        [
            html.Header([html.Div("Circular Lab Cockpit", className="logo")]),
            inventory_form,
            fabric_form,
            co2_form,
        ],
        className="wrapper",
    )
