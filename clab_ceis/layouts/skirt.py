from dash import html, dash_table, dcc


def skirt_page():
    return html.Div(
        className="product-detail",
        children=[
            html.H1("Skirt", className="product-title"),
            html.Div(
                className="product-content",
                children=[
                    html.Div(
                        className="product-image",
                        children=html.Img(
                            src="/assets/skirt.jpg",
                            alt="Skirt",
                            style={"width": "100%", "border-radius": "8px"},
                        ),
                    ),
                    html.Div(
                        className="product-description",
                        children=[
                            html.P(
                                "Wrapped Skirt made of double-sided fabric, in light blue and dark blue colors.",
                                style={"font-size": "18px"},
                            ),
                        ],
                    ),
                ],
                style={"display": "flex", "gap": "20px"},
            ),
            dcc.Link(
                "Back to Home",
                href="/",
                className="back-link",
                style={
                    "margin-top": "20px",
                    "display": "block",
                    "text-align": "center",
                },
            ),
        ],
    )
