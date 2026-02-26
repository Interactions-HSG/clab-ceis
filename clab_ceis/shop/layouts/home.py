from dash import html, dcc


def home_page():
    return html.Div(
        className="wrapper",
        children=[
            html.Header(
                html.H1(
                    "Welcome to Our Clothing Order Website", className="header-title"
                ),
                className="card",
            ),
            html.Div(
                className="card",
                children=[
                    html.H2("Select the Type of Clothing You Want to Order"),
                    html.Div(
                        className="order-form",
                        children=[
                            dcc.Link(
                                href="/skirt",
                                children=html.Div(
                                    className="product",
                                    children=[
                                        html.Img(
                                            src="/assets/skirt.jpg",
                                            alt="Skirt",
                                            className="product-image",
                                        ),
                                    ],
                                ),
                            ),
                            dcc.Link(
                                href="/top",
                                children=html.Div(
                                    className="product",
                                    children=[
                                        html.Img(
                                            src="/assets/top.jpg",
                                            alt="Top",
                                            className="product-image",
                                        ),
                                    ],
                                ),
                            ),
                        ],
                        style={"display": "flex", "gap": "20px"},
                    ),
                ],
            ),
            html.Div(
                className="card",
                children=[
                    html.H2("Customer Repair Requests"),
                    dcc.Loading(
                        id="customer-repair-loading",
                        type="circle",
                        children=html.Div(id="customer-repair-content"),
                        color="green",
                    ),
                ],
            ),
        ],
    )
