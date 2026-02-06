from dash import html, dcc, dash_table


def get_index_layout():
    inventory_form = html.Div(
        [
            dcc.Link(
                "Go to old Dashboard",
                href="/dashboard",
                id="dashboard-link",
            ),
            html.H1("Welcome"),
            dcc.Link(
                "Add Recipe",
                href="/add-recipe",
                id="add-recipe-link",
            ),
            html.H2("Fabric Block Inventory"),
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
                    {"name": "co2eq", "id": "co2eq"},
                    {"name": "garment_id", "id": "garment_id"},
                    {
                        "name": "preparations necessary",
                        "id": "preparations",
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
            html.H2("Add Fabric Blocks to inventory"),
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
            html.H3("Preparations"),
            html.Div(id="preparations-container", children=[]),
            html.Div(
                [
                    html.Button("Add Preparation", id="add-prep-button", n_clicks=0),
                    html.Button(
                        "Remove Last Preparation",
                        id="remove-prep-button",
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
        ],
        className="fabric-add-form",
    )

    co2_form = html.Div(
        [
            html.H2("CO2 Assessment"),
            dcc.Loading(
                id="co2-loading",
                type="circle",  # "default", "circle", "dot"
                children=html.Div(id="co2-form-content"),
                color="green",  # optional spinner color
            ),
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
