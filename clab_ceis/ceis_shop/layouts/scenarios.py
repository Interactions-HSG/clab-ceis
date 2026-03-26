from dash import dcc, html


def scenarios_page():
    return html.Div(
        className="wrapper",
        children=[
            html.Header(
                html.H1("End of Life Options", className="header-title"),
                className="card",
            ),
            html.Div(
                className="card",
                children=[
                    html.P(
                        "Manufacturer: Bucharest, Repair Center: St. Gallen, Consumer: Sigmaringen."
                    ),
                    dcc.Loading(
                        id="customer-repair-loading",
                        type="circle",
                        children=html.Div(id="customer-repair-content"),
                        color="green",
                    ),
                ],
            ),
            dcc.Link("Back to Home", href="/", className="back-link"),
        ],
    )
