from dash import dcc, html


def scenarios_page():
    return html.Div(
        className="wrapper",
        children=[
            html.Header(
                [
                    html.Div("Circular Lab Shop", className="brand"),
                    html.Nav(
                        [
                            dcc.Link("Garments", href="/"),
                            dcc.Link("End of life", href="/scenarios"),
                        ],
                        className="shop-actions",
                    ),
                ],
                className="shop-topbar",
            ),
            html.Section(
                [
                    html.Div("Circular services", className="shop-kicker"),
                    html.H1("End of Life Options", className="header-title"),
                    html.P(
                        "Compare practical return, repair, and replacement scenarios for the current garment journey.",
                        className="shop-intro",
                    ),
                ],
                className="shop-hero",
            ),
            html.Section(
                className="panel",
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
