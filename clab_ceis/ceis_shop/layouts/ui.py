from dash import dcc


def shop_home_link():
    return dcc.Link(
        "Home",
        href="/",
        id="shop-home-button",
        className="page-home-link shop-home-button",
        title="Go to home page",
    )
