from dash import dcc, html
from pages.ui import app_topbar, page_hero


def get_garment_designer_layout():
    return html.Div(
        [
            dcc.Store(id="garment-designer-reference-data-store", data={}),
            dcc.Store(id="garment-designer-reference-scenario-store", data={}),
            dcc.Store(id="garment-designer-custom-bom-store", data=[]),
            dcc.Store(id="garment-designer-custom-process-store", data=[]),
            app_topbar(),
            page_hero(
                "Prototype",
                "New Garment Designer",
                "Design new garments with material longevity, process economics, ecology, and recipe-level fabric block and process references.",
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
