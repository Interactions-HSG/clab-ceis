from dash import dcc, html


def shop_topbar(active: str = ""):
    """Shared customer-facing navigation for every shop page."""
    return html.Header(
        [
            dcc.Link(
                [
                    html.Span("CL", className="brand-mark"),
                    html.Span(
                        [
                            html.Strong("Circular Lab"),
                            html.Small("Made for many lives"),
                        ],
                        className="brand-copy",
                    ),
                ],
                href="/",
                className="brand shop-brand-link",
                title="Circular Lab shop home",
            ),
            html.Nav(
                [
                    dcc.Link(
                        "Shop",
                        href="/",
                        className="is-active" if active == "shop" else "",
                    ),
                    dcc.Link(
                        "Circular care",
                        href="/repair-return",
                        className="is-active" if active == "care" else "",
                    ),
                    dcc.Link(
                        "Impact guide",
                        href="/scenarios",
                        className="is-active" if active == "impact" else "",
                    ),
                ],
                className="shop-actions",
            ),
        ],
        className="shop-topbar",
    )


def shop_home_link():
    return dcc.Link(
        "← Back to shop",
        href="/",
        id="shop-home-button",
        className="page-home-link shop-home-button",
        title="Back to all garments",
    )
