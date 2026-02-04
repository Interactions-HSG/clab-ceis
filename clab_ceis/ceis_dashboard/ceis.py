from enum import Enum

import pandas as pd
from dash import Dash, html, dcc, dash_table
from dash.dependencies import Input, Output
import dash_cytoscape as cyto
from flask import request, jsonify

from clab_ceis.ceis_dashboard import ceis_data, ceis_callbacks
from clab_ceis import config


class CeStages(Enum):
    Extraction = 1
    Production = 2
    Use = 3
    Waste = 4


class CeLoops(Enum):
    Repair = 11
    Remanufacture = 12
    Recycle = 13
    Composting = 14


class CeisMonitor:
    _model: pd.DataFrame
    _app: Dash
    _layout = None
    _chart_height = 400

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
        # Sample flow chart data
        flow_chart_data = {
            "elements": [
                {
                    "data": {
                        "id": f"{CeStages.Extraction.value}",
                        "label": f"{CeStages.Extraction.name}",
                    },
                    "position": {"x": 100, "y": 0.5 * self._chart_height},
                },
                {
                    "data": {
                        "id": f"{CeStages.Production.value}",
                        "label": f"{CeStages.Production.name}",
                    },
                    "position": {"x": 300, "y": 0.5 * self._chart_height},
                },
                {
                    "data": {
                        "id": f"{CeStages.Use.value}",
                        "label": f"{CeStages.Use.name}",
                    },
                    "position": {"x": 500, "y": 0.5 * self._chart_height},
                },
                {
                    "data": {
                        "id": f"{CeStages.Waste.value}",
                        "label": f"{CeStages.Waste.name}",
                    },
                    "position": {"x": 700, "y": 0.5 * self._chart_height},
                },
                {
                    "data": {
                        "source": f"{CeStages.Extraction.value}",
                        "target": f"{CeStages.Production.value}",
                        "label": "Supply",
                    }
                },
                {
                    "data": {
                        "source": f"{CeStages.Production.value}",
                        "target": f"{CeStages.Use.value}",
                        "label": "Deliver",
                    }
                },
                {
                    "data": {
                        "source": f"{CeStages.Use.value}",
                        "target": f"{CeStages.Waste.value}",
                        "label": "Release",
                    }
                },
                # loops
                {
                    "data": {
                        "id": f"{CeLoops.Repair.value}",
                        "label": f"{CeLoops.Repair.name}",
                        "source": f"{CeStages.Use.value}",
                        "target": f"{CeStages.Use.value}",
                    }
                },
                {
                    "data": {
                        "id": f"{CeLoops.Remanufacture.value}",
                        "label": f"{CeLoops.Remanufacture.name}",
                        "source": f"{CeStages.Use.value}",
                        "target": f"{CeStages.Production.value}",
                    }
                },
                {
                    "data": {
                        "id": f"{CeLoops.Recycle.value}",
                        "label": f"{CeLoops.Recycle.name}",
                        "source": f"{CeStages.Waste.value}",
                        "target": f"{CeStages.Production.value}",
                    }
                },
                {
                    "data": {
                        "id": f"{CeLoops.Composting.value}",
                        "label": f"{CeLoops.Composting.name}",
                        "source": f"{CeStages.Waste.value}",
                        "target": f"{CeStages.Extraction.value}",
                    }
                },
            ]
        }

        # Build the dashboard layout (the full content previously used as app.layout)
        self._dashboard_layout = html.Div(
            children=[
                html.Header([html.Div("Circular Lab Cockpit", className="logo")]),
                html.Div(
                    [
                        html.H1("Product Lifecycle"),
                        cyto.Cytoscape(
                            id="flow-chart",
                            layout={"name": "preset"},
                            style={"height": f"{self._chart_height}px"},
                            autolock=True,
                            elements=flow_chart_data["elements"],
                            panningEnabled=False,
                            zoom=1,
                            stylesheet=[
                                {
                                    "selector": "node",
                                    "style": {
                                        "label": "data(label)",
                                        "shape": "tag",
                                        "text-halign": "left",
                                        "text-valign": "bottom",
                                        "text-margin-x": "-10%",
                                        "line-color": "yellow",
                                        "background-color": "darkblue",
                                        "text-background-color": "grey",
                                        "text-background-opacity": 0.7,
                                    },
                                },
                                {
                                    "selector": "edge",
                                    "style": {
                                        "label": "data(label)",
                                        "target-arrow-shape": "triangle",
                                        "arrow-scale": 1.5,
                                        "line-color": "darkblue",
                                        "text-margin-y": "-15%",
                                    },
                                },
                                {
                                    "selector": f"#{CeLoops.Repair.value}, #{CeLoops.Recycle.value}, #{CeLoops.Remanufacture.value}, #{CeLoops.Composting.value}",
                                    "style": {
                                        "label": "data(label)",
                                        "curve-style": "unbundled-bezier",
                                        "control-point-distance": "200",
                                        "line-color": "orange",
                                    },
                                },
                                {
                                    "selector": f"#{CeLoops.Composting.value}",
                                    "style": {
                                        "label": "data(label)",
                                        "curve-style": "unbundled-bezier",
                                        "control-point-distance": "-300",
                                        "text-margin-y": "15%",
                                    },
                                },
                                {
                                    "selector": f"#{CeLoops.Remanufacture.value}",
                                    "style": {
                                        "label": "data(label)",
                                        "curve-style": "unbundled-bezier",
                                        "control-point-distance": "-200",
                                        "text-margin-y": "15%",
                                    },
                                },
                            ],
                        ),
                        html.P(id="cytoscape-output"),
                        html.H1("Resource Event Dashboard"),
                        html.Button("Update DataTable", id="update-button", n_clicks=0),
                        dash_table.DataTable(
                            id="res-dashboard-table",
                            columns=[
                                {"name": col, "id": col}
                                for col in self._model.get_data().columns
                            ],
                            data=self._model.get_data().to_dict("records"),
                            style_table={"maxWidth": f"{self._chart_height}px"},
                            style_cell={"textAlign": "center"},
                            style_header={"fontWeight": "bold"},
                        ),
                        html.H1("Circular Economy Dashboard"),
                        dash_table.DataTable(
                            id="dashboard-table",
                            columns=[
                                {"name": "Metric", "id": "metric"},
                                {"name": "Value", "id": "value"},
                            ],
                            data=[
                                {
                                    "metric": "Circular Economy Metric 1",
                                    "value": "1234",
                                },
                                {
                                    "metric": "Circular Economy Metric 2",
                                    "value": "5678",
                                },
                                {
                                    "metric": "Circular Economy Metric 3",
                                    "value": "9012",
                                },
                            ],
                            style_table={"maxWidth": "600px"},
                            style_cell={"textAlign": "center"},
                            style_header={"fontWeight": "bold"},
                        ),
                    ],
                    className="wrapper",
                ),
            ]
        )

        # Simple index layout with a link to /dashboard and fabric block inventory
        self._index_layout = html.Div(
            [
                html.Header([html.Div("Circular Lab Cockpit", className="logo")]),
                html.Div(
                    [
                        html.H1("Welcome"),
                        dcc.Link(
                            "Go to old Dashboard",
                            href="/dashboard",
                            id="dashboard-link",
                        ),
                        html.H2("Fabric Block Inventory"),
                        html.Button(
                            "Refresh Fabric Blocks",
                            id="refresh-fabric-blocks",
                            n_clicks=0,
                        ),
                        dash_table.DataTable(
                            id="fabric-blocks-table",
                            columns=[
                                {"name": "id", "id": "id"},
                                {"name": "type", "id": "type"},
                                {"name": "co2eq", "id": "co2eq"},
                                {"name": "garment_id", "id": "garment_id"},
                                {
                                    "name": "preparations necessary",
                                    "id": "preparations",
                                },
                            ],
                            data=[],  # populated via callback
                            style_table={"maxWidth": "800px"},
                            style_cell={"textAlign": "center"},
                            style_header={"fontWeight": "bold"},
                        ),
                    ],
                    className="wrapper",
                ),
            ]
        )
        # UI for adding fabric blocks and callbacks to update the fabric blocks table

        # Add a simple form to the index page for adding fabric blocks
        fabric_form = html.Div(
            [
                html.H2("Add Fabric Blocks"),
                html.Div(
                    [
                        html.Label("Type"),
                        dcc.Dropdown(
                            id="fabric-type",
                            options=[
                                {"label": "Fabric Block 1", "value": "1"},
                                {"label": "Fabric Block 2", "value": "2"},
                                # {"label": "Fabric Block 3", "value": "FB3"},
                                # {"label": "Fabric Block 4", "value": "FB4"},
                            ],
                            placeholder="Select a fabric type",
                        ),
                    ],
                    style={"marginBottom": "12px", "maxWidth": "400px"},
                ),
                html.H3("Preparations"),
                html.Div(id="preparations-container", children=[]),
                html.Div(
                    [
                        html.Button(
                            "Add Preparation", id="add-prep-button", n_clicks=0
                        ),
                        html.Button(
                            "Remove Last Preparation",
                            id="remove-prep-button",
                            n_clicks=0,
                        ),
                    ],
                    style={
                        "marginTop": "8px",
                        "marginBottom": "12px",
                        "display": "flex",
                        "gap": "8px",
                    },
                ),
                html.Button("Add Fabric Block", id="add-fabric-blocks", n_clicks=0),
                html.Div(
                    id="fabric-add-status", style={"marginTop": "8px", "color": "green"}
                ),
            ],
            className="fabric-add-form",
        )

        co2_form = html.Div(
            [
                html.H2("CO2 Assessment"),
                html.Div(id="co2-form-content"),
            ]
        )

        # Append form to the existing wrapper in the index layout
        try:
            # _index_layout structure: [Header, html.Div(wrapper...)]
            wrapper_div = self._index_layout.children[1]
            # append the form after existing fabric-blocks-table area
            wrapper_children = list(wrapper_div.children)
            wrapper_children.append(fabric_form)
            wrapper_children.append(co2_form)
            wrapper_div.children = wrapper_children
        except Exception:
            # If structure differs, append to top-level index layout as fallback
            index_children = list(self._index_layout.children)
            index_children.append(fabric_form)
            index_children.append(co2_form)
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
