from dash import html, dash_table, dcc


def top_page():
    return html.Div(
        className="product-detail",
        children=[
            html.H1("Top", className="product-title"),
            html.Div(
                className="product-content",
                children=[
                    html.Div(
                        className="product-image",
                        children=html.Img(
                            src="/assets/top.jpg",
                            alt="Top",
                            style={"width": "100%", "border-radius": "8px"},
                        ),
                    ),
                    html.Div(
                        className="product-description",
                        children=[
                            html.P(
                                "Crop top made from fine hemp fabric in a linen weave."
                                "Loose fit with a T-shape geometric opening at the neck.",
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
