from dash import html, dcc

from ceis_shop.layouts.ui import shop_home_link, shop_topbar


def skirt_page():
    return html.Div(
        className="product-detail shop-page garment-page",
        children=[
            shop_topbar("shop"),
            html.Section(
                [
                    html.Div(
                        [
                            html.Div("Garment detail", className="shop-kicker"),
                            html.H1("Skirt", className="product-title"),
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
                            src="/assets/skirt.jpg",
                            alt="Skirt",
                        ),
                    ),
                    html.Div(
                        className="product-description",
                        children=[
                            html.Div("Reversible design", className="section-eyebrow"),
                            html.P(
                                "Wrapped Skirt made of double-sided fabric, in light blue and dark blue colors.",
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
