from dash import dcc, html


def get_co2_layout(garment_type_id: int):
    return html.Div(
        [
            dcc.Link(
                "Home",
                href="/",
                id="home-link",
            ),
            html.H1("CO2 Assessment"),
            dcc.Store(id="co2-garment-id", data=garment_type_id),
            dcc.Loading(
                id="co2-loading",
                type="circle",
                color="green",
                children=html.Div(id="co2-form-content"),
            ),
        ],
        className="wrapper",
    )
