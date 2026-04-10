from dash import dcc, html


def get_designer_balance_layout():
    return html.Div(
        [
            dcc.Link(
                "Home",
                href="/",
                id="designer-balance-home-link",
            ),
            html.H1("Designer Balance"),
            html.P(
                "Inspect one garment type at a time, switch suppliers, and review how materials, processes, transport, delays, and margin change together."
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.Label("Garment type"),
                            dcc.Dropdown(
                                id="designer-balance-garment",
                                options=[],
                                placeholder="Select a garment type",
                                clearable=False,
                            ),
                        ],
                        className="designer-balance-control",
                    ),
                    html.Div(
                        [
                            html.Label("Material"),
                            dcc.Dropdown(
                                id="designer-balance-material",
                                options=[],
                                placeholder="Select a material",
                                clearable=False,
                            ),
                        ],
                        className="designer-balance-control",
                    ),
                    html.Div(
                        [
                            html.Label("Fabric supplier"),
                            dcc.Dropdown(
                                id="designer-balance-fabric-supplier",
                                options=[],
                                placeholder="Select a fabric supplier",
                                clearable=False,
                            ),
                        ],
                        className="designer-balance-control",
                    ),
                    html.Div(
                        [
                            html.Label("Garment manufacturer"),
                            dcc.Dropdown(
                                id="designer-balance-garment-supplier",
                                options=[],
                                placeholder="Select a garment manufacturer",
                                clearable=False,
                            ),
                        ],
                        className="designer-balance-control",
                    ),
                    html.Div(
                        [
                            html.Label("Finishing supplier"),
                            dcc.Dropdown(
                                id="designer-balance-finishing-supplier",
                                options=[],
                                placeholder="Select a finishing supplier",
                                clearable=False,
                            ),
                        ],
                        className="designer-balance-control",
                    ),
                ],
                className="designer-balance-controls",
            ),
            dcc.Loading(
                id="designer-balance-loading",
                type="circle",
                color="#0f766e",
                children=html.Div(id="designer-balance-content"),
            ),
        ],
        className="wrapper designer-balance-page",
    )
