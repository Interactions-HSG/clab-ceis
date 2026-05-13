from dash import dcc, html
from pages.ui import app_topbar, page_hero


def get_recipe_layout():
    return html.Div(
        [
            html.Div(
                [
                    app_topbar(),
                    page_hero(
                        "Reference data",
                        "Add Recipe",
                        "Create garment recipes, fabric block types, process types, and material references for downstream circularity calculations.",
                    ),
                    html.H2("Add Garment Recipe"),
                    html.Div(
                        [
                            html.Label("Garment type name"),
                            dcc.Input(
                                id="recipe-garment-type-name",
                                type="text",
                                placeholder="e.g., jacket",
                            ),
                            html.Label("Garment price (CHF)"),
                            dcc.Input(
                                id="recipe-garment-price",
                                type="number",
                                min=0,
                                step=1,
                                placeholder="e.g., 100",
                            ),
                            html.H3("Fabric blocks in recipe"),
                            html.Div(id="recipe-fabric-blocks-container", children=[]),
                            html.Div(
                                [
                                    html.Button(
                                        "Add Fabric Block",
                                        id="add-recipe-fabric-block",
                                        n_clicks=0,
                                    ),
                                    html.Button(
                                        "Remove Last Fabric Block",
                                        id="remove-recipe-fabric-block",
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
                            html.H3("Materials in recipe"),
                            html.Div(id="recipe-materials-container", children=[]),
                            html.Div(
                                [
                                    html.Button(
                                        "Add Material",
                                        id="add-recipe-material",
                                        n_clicks=0,
                                    ),
                                    html.Button(
                                        "Remove Last Material",
                                        id="remove-recipe-material",
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
                            html.H3("Processes (optional)"),
                            html.Div(id="recipe-processes-container", children=[]),
                            html.Div(
                                [
                                    html.Button(
                                        "Add Process",
                                        id="add-recipe-process",
                                        n_clicks=0,
                                    ),
                                    html.Button(
                                        "Remove Last Process",
                                        id="remove-recipe-process",
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
                            html.Button(
                                "Save Garment Recipe",
                                id="add-garment-recipe",
                                n_clicks=0,
                            ),
                            html.Div(
                                id="garment-recipe-status",
                                style={"marginTop": "6px", "color": "green"},
                            ),
                        ],
                        style={"marginBottom": "20px"},
                    ),
                    # html.H2("Delete Garment Recipe"),
                    # html.Div(
                    #     [
                    #         html.Label("Garment type"),
                    #         dcc.Dropdown(
                    #             id="delete-garment-recipe-type",
                    #             options=[],
                    #             placeholder="Select a garment type",
                    #             clearable=False,
                    #         ),
                    #         html.Button(
                    #             "Delete Garment Recipe",
                    #             id="delete-garment-recipe",
                    #             n_clicks=0,
                    #         ),
                    #         html.Div(
                    #             id="delete-garment-recipe-status",
                    #             style={"marginTop": "6px", "color": "green"},
                    #         ),
                    #     ],
                    #     style={"marginBottom": "20px"},
                    # ),
                    html.H2("Add Fabric Block Type"),
                    html.Div(
                        [
                            html.Label("Name"),
                            dcc.Input(
                                id="fabric-block-type-name",
                                type="text",
                                placeholder="e.g., FB3",
                            ),
                            html.Label("Area (sqm)"),
                            dcc.Input(
                                id="fabric-block-type-sqm",
                                type="number",
                                min=0,
                                step=0.1,
                                placeholder="e.g., 1.2",
                            ),
                            html.H3("Processes (optional)"),
                            html.Div(
                                id="fabric-block-type-processes-container",
                                children=[],
                            ),
                            html.Div(
                                [
                                    html.Button(
                                        "Add Process Step",
                                        id="add-fabric-block-type-process",
                                        n_clicks=0,
                                    ),
                                    html.Button(
                                        "Remove Last Process Step",
                                        id="remove-fabric-block-type-process",
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
                            html.Button(
                                "Add Fabric Block Type",
                                id="add-fabric-block-type",
                                n_clicks=0,
                            ),
                            html.Div(
                                id="fabric-block-type-status",
                                style={"marginTop": "6px", "color": "green"},
                            ),
                        ],
                        style={"marginBottom": "20px"},
                    ),
                    # html.H2("Delete Fabric Block Type"),
                    # html.Div(
                    #     [
                    #         html.Label("Fabric block type"),
                    #         dcc.Dropdown(
                    #             id="delete-fabric-block-type",
                    #             options=[],
                    #             placeholder="Select a fabric block type",
                    #             clearable=False,
                    #         ),
                    #         html.Button(
                    #             "Delete Fabric Block Type",
                    #             id="delete-fabric-block-type-button",
                    #             n_clicks=0,
                    #         ),
                    #         html.Div(
                    #             id="delete-fabric-block-type-status",
                    #             style={"marginTop": "6px", "color": "green"},
                    #         ),
                    #     ],
                    #     style={"marginBottom": "20px"},
                    # ),
                    html.H2("Add Process Type"),
                    html.Div(
                        [
                            html.Label("Process type name"),
                            dcc.Input(
                                id="process-type-name",
                                type="text",
                                placeholder="e.g., ironing",
                            ),
                            html.Label("Unit"),
                            dcc.Input(
                                id="process-type-unit",
                                type="text",
                                placeholder="e.g., kWh",
                            ),
                            html.Label("Activity ID"),
                            dcc.Input(
                                id="process-type-activity-id",
                                type="number",
                                min=0,
                                step=1,
                                placeholder="e.g., 6566",
                            ),
                            html.Button(
                                "Add Process Type",
                                id="add-process-type",
                                n_clicks=0,
                            ),
                            html.Div(
                                id="process-type-status",
                                style={"marginTop": "6px", "color": "green"},
                            ),
                        ],
                        style={"marginBottom": "20px"},
                    ),
                    html.H2("Add / Update Material"),
                    html.Div(
                        [
                            html.Label("Material name"),
                            dcc.Input(
                                id="material-name",
                                type="text",
                                placeholder="e.g., hemp",
                            ),
                            html.Label("kg per sqm"),
                            dcc.Input(
                                id="material-kg-per-sqm",
                                type="number",
                                min=0,
                                step=0.01,
                                placeholder="e.g., 0.21",
                            ),
                            html.Label("Activity ID"),
                            dcc.Input(
                                id="material-activity-id",
                                type="number",
                                min=0,
                                step=1,
                                placeholder="e.g., 276186",
                            ),
                            html.Button(
                                "Save Material",
                                id="add-material",
                                n_clicks=0,
                            ),
                            html.Div(
                                id="material-status",
                                style={"marginTop": "6px", "color": "green"},
                            ),
                        ],
                        style={"marginBottom": "20px"},
                    ),
                    # html.H2("Delete Process Type"),
                    # html.Div(
                    #     [
                    #         html.Label("Process type"),
                    #         dcc.Dropdown(
                    #             id="delete-process-type",
                    #             options=[],
                    #             placeholder="Select a process type",
                    #             clearable=False,
                    #         ),
                    #         html.Button(
                    #             "Delete Process Type",
                    #             id="delete-process-type-button",
                    #             n_clicks=0,
                    #         ),
                    #         html.Div(
                    #             id="delete-process-type-status",
                    #             style={"marginTop": "6px", "color": "green"},
                    #         ),
                    #     ],
                    #     style={"marginBottom": "20px"},
                    # ),
                    html.Br(),
                    html.H2("Search Ecoinvent for activity ID of a process"),
                    html.Div(
                        [
                            html.Label("Search query"),
                            dcc.Input(
                                id="activity-search-query",
                                type="text",
                                placeholder="e.g., electricity",
                            ),
                            html.Button(
                                "Search",
                                id="activity-search-button",
                                n_clicks=0,
                            ),
                            html.Div(
                                id="activity-search-status",
                                style={"marginTop": "6px", "color": "green"},
                            ),
                            html.Div(
                                id="activity-search-results",
                                style={"marginTop": "10px"},
                            ),
                        ],
                        style={"marginBottom": "20px"},
                    ),
                    # html.H2("Delete Resource Type"),
                    # html.Div(
                    #     [
                    #         html.Label("Resource type"),
                    #         dcc.Dropdown(
                    #             id="delete-resource-type",
                    #             options=[],
                    #             placeholder="Select a resource type",
                    #             clearable=False,
                    #         ),
                    #         html.Button(
                    #             "Delete Resource Type",
                    #             id="delete-resource-type-button",
                    #             n_clicks=0,
                    #         ),
                    #         html.Div(
                    #             id="delete-resource-type-status",
                    #             style={"marginTop": "6px", "color": "green"},
                    #         ),
                    #     ],
                    #     style={"marginBottom": "20px"},
                    # ),
                ],
                className="wrapper",
            ),
        ],
        className="recipe-page",
    )
