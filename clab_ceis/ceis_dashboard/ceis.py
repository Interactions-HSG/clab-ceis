from enum import Enum

import pandas as pd
from clab_ceis.ceis_dashboard.pages.home import get_index_layout
from clab_ceis.ceis_dashboard.pages.old_dashboard import (
    get_dashboard_layout,
    get_flow_chart_data,
)
from clab_ceis.ceis_dashboard.pages.recipe import get_recipe_layout
from dash import Dash, html, dcc, dash_table
from dash.dependencies import Input, Output
from flask import request, jsonify

from clab_ceis.ceis_dashboard import ceis_data, ceis_callbacks
from clab_ceis import config


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
        self.get_route(self._app.server)
        ceis_callbacks.get_callbacks(self._app, self._model)

    def make_layout(self) -> None:
        self._dashboard_layout = get_dashboard_layout()

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
            required_cols = ["id", "type", "co2eq", "garment_id", "preparations"]
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
                return self._dashboard_layout
            elif pathname == "/add-recipe":
                return self._add_recipe_layout
            # default / or unknown paths -> index
            return self._index_layout

    def get_route(self, server):
        @server.route("/quote", methods=["PUT"])
        def quote_endpoint():
            # Retrieve data from the HTTP request
            data = request.json
            # Safely compute next EventID
            last_id_series = self._model.get_data().get("EventID")
            last_id = (
                int(last_id_series.iloc[-1])
                if (last_id_series is not None and not last_id_series.empty)
                else 0
            )
            data["EventID"] = last_id + 1
            self._model.set_data(
                pd.concat(
                    [self._model.get_data(), pd.DataFrame([data])], ignore_index=True
                )
            )

            return jsonify(ceis_data.CeisTrade.get_offer(self._model.get_data()))


def main():
    app = Dash(
        __name__,
        # needed when callbacks and app are specified in different modules
        suppress_callback_exceptions=True,
        assets_folder="/app/clab_ceis/assets",
    )
    mon = CeisMonitor(app)
    # TODO: implement a good way to change the configuration
    # app.run_server(host="ceis", port="8051", debug=True)
    app.run_server(
        host=config.CEIS_MONITOR_HOSTNAME, port=config.CEIS_MONITOR_PORT, debug=True
    )


if __name__ == "__main__":
    main()
