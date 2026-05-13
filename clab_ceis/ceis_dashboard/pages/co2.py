from dash import dcc, html
from pages.ui import app_topbar, page_hero


def get_co2_layout(garment_type_id: int):
    return html.Div(
        [
            app_topbar(),
            page_hero(
                "Assessment",
                "CO2 Assessment",
                "Review garment-level material and process emissions with circular fabric block alternatives.",
            ),
            dcc.Store(id="co2-garment-id", data=garment_type_id),
            dcc.Loading(
                id="co2-loading",
                type="circle",
                color="green",
                children=html.Div(id="co2-form-content", className="panel"),
            ),
        ],
        className="wrapper",
    )
