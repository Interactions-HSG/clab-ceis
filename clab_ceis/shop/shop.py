from dash import Dash, dcc, html
from .layouts.home import home_page
from .layouts.skirt import skirt_page
from .layouts.top import top_page
from .shop_callbacks import get_callbacks
from dash.dependencies import Input, Output
from pathlib import Path

from . import config

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
        html.Div(id="page-content", style={"padding": "20px"}),
    ]
)

# Register callbacks
get_callbacks(app)


# Page routing callback
@app.callback(Output("page-content", "children"), [Input("url", "pathname")])
def display_page(pathname):
    if pathname == "/skirt":
        return skirt_page()
    elif pathname == "/top":
        return top_page()
    else:
        return home_page()


def main():
    app.run(host=config.CEIS_SHOP_HOSTNAME, port=config.CEIS_SHOP_PORT, debug=True)


if __name__ == "__main__":
    main()
