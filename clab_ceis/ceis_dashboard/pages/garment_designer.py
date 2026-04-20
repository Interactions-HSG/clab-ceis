from dash import dcc, html


def get_garment_designer_layout():
    return html.Div(
        [
            dcc.Link(
                "Home",
                href="/",
                id="garment-designer-home-link",
            ),
            html.H1("New Garment Designer"),
            html.P(
                "Use this view to design new garments with material longevity, process economics/ecology, and recipe-level fabric block/process references."
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.Label("New garment name"),
                            dcc.Input(
                                id="garment-designer-name",
                                type="text",
                                placeholder="e.g., Modular Utility Jacket",
                            ),
                        ],
                        className="garment-designer-control",
                    ),
                    html.Div(
                        [
                            html.Label("Target sales price (CHF)"),
                            dcc.Input(
                                id="garment-designer-target-price",
                                type="number",
                                min=0,
                                step=1,
                                placeholder="e.g., 220",
                            ),
                        ],
                        className="garment-designer-control",
                    ),
                    html.Div(
                        [
                            html.Label("Reference garment type"),
                            dcc.Dropdown(
                                id="garment-designer-reference-garment",
                                options=[],
                                placeholder="Select a reference garment",
                                clearable=False,
                            ),
                        ],
                        className="garment-designer-control",
                    ),
                ],
                className="garment-designer-controls",
            ),
            dcc.Loading(
                id="garment-designer-loading",
                type="circle",
                color="#155e75",
                children=html.Div(id="garment-designer-content"),
            ),
        ],
        className="wrapper garment-designer-page",
    )
