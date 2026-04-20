import pandas as pd
from dash import Dash, html, dcc
from dash.dependencies import Input, Output

from pages.recipe import get_recipe_layout
from pages.flow import get_dashboard_layout
from pages.home import get_index_layout
from pages.co2 import get_co2_layout
from pages.designer_balance import get_designer_balance_layout
from pages.garment_designer import get_garment_designer_layout
import ceis_data
import ceis_callbacks
import config
from callbacks.api import fetch_strategy_progress


class CeisMonitor:
    _model: pd.DataFrame
    _app: Dash
    _layout = None

    @property
    def layout(self):
        return self._layout

    def __init__(self, app) -> None:
        self._app = app
        self._model = ceis_data.CeisData()
        self.make_layout()
        ceis_callbacks.get_callbacks(self._app, self._model)

    def make_layout(self) -> None:
        self._add_recipe_layout = get_recipe_layout()

        self._index_layout = get_index_layout()

        # Append form to the existing wrapper in the index layout
        try:
            # _index_layout structure: [Header, html.Div(wrapper...)]
            wrapper_div = self._index_layout.children[1]
            # append the form after existing fabric-blocks-table area
            wrapper_children = list(wrapper_div.children)
            wrapper_div.children = wrapper_children
        except Exception:
            # If structure differs, append to top-level index layout as fallback
            index_children = list(self._index_layout.children)
            self._index_layout.children = index_children

        # Helper to extract current fabric table subset (ensures columns exist)
        def _fabric_table_records():
            df = self._model.get_data()
            if df is None or df.empty:
                return []
            # Ensure columns used in the fabric table exist in df
            required_cols = ["id", "type", "co2eq", "garment_id", "processes"]
            for c in required_cols:
                if c not in df.columns:
                    df[c] = None
            return df[required_cols].to_dict("records")

        # App-level layout handling routing (client-side)
        self._layout = html.Div(
            [dcc.Location(id="url", refresh=False), html.Div(id="page-content")]
        )
        self._app.layout = self._layout

        # Callback to render page content based on the pathname
        @self._app.callback(
            Output("page-content", "children"), [Input("url", "pathname")]
        )
        def display_page(pathname):
            if pathname == "/dashboard":
                return get_dashboard_layout(fetch_strategy_progress())
            elif pathname == "/add-recipe":
                return self._add_recipe_layout
            elif pathname == "/designer-balance":
                return get_designer_balance_layout()
            elif pathname == "/garment-designer":
                return get_garment_designer_layout()
            elif pathname and pathname.startswith("/co2/"):
                try:
                    garment_type_id = int(pathname.split("/co2/")[1])
                    return get_co2_layout(garment_type_id)
                except (ValueError, IndexError):
                    return html.Div("Invalid CO2 garment page.")
            # default / or unknown paths -> index
            return self._index_layout


def main():
    app = Dash(
        __name__,
        # needed when callbacks and app are specified in different modules
        suppress_callback_exceptions=True,
        assets_folder="../assets",
    )
    mon = CeisMonitor(app)
    # TODO: implement a good way to change the configuration
    # app.run_server(host="ceis", port="8051", debug=True)
    app.run(
        host=config.CEIS_MONITOR_HOSTNAME, port=config.CEIS_MONITOR_PORT, debug=True
    )


if __name__ == "__main__":
    main()
