from dash import html


def shop_home_link():
    return html.Button(
        "Home",
        id="shop-home-button",
        className="page-home-link shop-home-button",
        n_clicks=0,
        title="Go to home page",
    )
