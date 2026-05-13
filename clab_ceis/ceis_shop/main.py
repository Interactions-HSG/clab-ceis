from pathlib import Path

from dash import Dash, dcc, html, no_update
from dash.dependencies import Input, Output

from ceis_shop.layouts.scenarios import scenarios_page
from ceis_shop.layouts.garment import garment_page
from ceis_shop.layouts.home import home_page
from ceis_shop.layouts.skirt import skirt_page
from ceis_shop.layouts.top import top_page
from ceis_shop.shop_callbacks import get_callbacks
from ceis_shop import config

# Initialize the app
app = Dash(
    __name__,
    assets_folder=str(Path(__file__).parent.parent / "assets"),
    suppress_callback_exceptions=True,
)
server = app.server


# Define app layout
app.layout = html.Div(
    children=[
        dcc.Location(id="url", refresh=False),
        html.Div(id="page-content"),
    ],
    className="app-shell",
)

# Register callbacks
get_callbacks(app)


@app.callback(
    Output("url", "pathname"),
    [Input("shop-home-button", "n_clicks")],
    prevent_initial_call=True,
)
def navigate_home(n_clicks):
    if n_clicks:
        return "/"
    return no_update


# Page routing callback
@app.callback(Output("page-content", "children"), [Input("url", "pathname")])
def display_page(pathname):
    if pathname and pathname.startswith("/garment/"):
        try:
            garment_type_id = int(pathname.split("/garment/")[1])
            return garment_page(garment_type_id)
        except (ValueError, IndexError):
            return html.Div("Invalid garment page.")
    if pathname == "/skirt":
        return skirt_page()
    elif pathname == "/scenarios":
        return scenarios_page()
    elif pathname == "/top":
        return top_page()
    else:
        return home_page()


def main():
    app.run(host=config.CEIS_SHOP_HOSTNAME, port=config.CEIS_SHOP_PORT, debug=True)


if __name__ == "__main__":
    main()
