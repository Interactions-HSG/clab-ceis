from dash import html, dcc

from ceis_shop.layouts.ui import shop_home_link, shop_topbar


def top_page():
    return html.Div(
        className="product-detail shop-page garment-page",
        children=[
            shop_topbar("shop"),
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
                            html.Div("Thoughtfully cut", className="section-eyebrow"),
                            html.P(
                                "Crop top made from fine hemp fabric in a linen weave."
                                "Loose fit with a T-shape geometric opening at the neck.",
                            ),
                            dcc.Link(
                                "Explore the full collection →",
                                href="/",
                                className="primary-link",
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )
