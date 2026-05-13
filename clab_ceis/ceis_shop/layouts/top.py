from dash import html, dcc

from ceis_shop.layouts.ui import shop_home_link


def top_page():
    return html.Div(
        className="product-detail",
        children=[
            html.Header(
                [
                    html.Div("Circular Lab Shop", className="brand"),
                    html.Nav(
                        [
                            dcc.Link("Home", href="/", className="home-nav-link"),
                            dcc.Link("End of life", href="/scenarios"),
                        ],
                        className="shop-actions",
                    ),
                ],
                className="shop-topbar",
            ),
            html.Section(
                [
                    html.Div(
                        [
                            html.Div("Garment detail", className="shop-kicker"),
                            html.H1("Top", className="product-title"),
                        ],
                        className="shop-hero-copy",
                    ),
                    shop_home_link(),
                ],
                className="shop-hero shop-hero-with-action",
            ),
            html.Div(
                className="product-content",
                children=[
                    html.Div(
                        className="product-image",
                        children=html.Img(
                            src="/assets/top.jpg",
                            alt="Top",
                        ),
                    ),
                    html.Div(
                        className="product-description",
                        children=[
                            html.P(
                                "Crop top made from fine hemp fabric in a linen weave."
                                "Loose fit with a T-shape geometric opening at the neck.",
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )
