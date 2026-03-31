from __future__ import annotations
import requests
from dash import Dash, Input, Output, State, callback_context, dcc, html
from dash.dependencies import ALL

import config
import ceis_data


def register_recipe_type_callbacks(app: Dash, data: ceis_data.CeisData) -> None:
    @app.callback(
        Output("delete-garment-recipe-type", "options"),
        Output("delete-fabric-block-type", "options"),
        Output("delete-process-type", "options"),
        Input("url", "pathname"),
        Input("add-garment-recipe", "n_clicks"),
        Input("delete-garment-recipe", "n_clicks"),
        Input("add-fabric-block-type", "n_clicks"),
        Input("delete-fabric-block-type-button", "n_clicks"),
        Input("add-process-type", "n_clicks"),
        Input("delete-process-type-button", "n_clicks"),
    )
    def load_delete_options(
        pathname,
        add_recipe_clicks,
        delete_recipe_clicks,
        add_fabric_clicks,
        delete_fabric_clicks,
        add_process_clicks,
        delete_process_clicks,
    ):
        garment_options = []
        fabric_options = []
        process_options = []

        try:
            resp = requests.get(f"{config.BACKEND_API_URL}/garment-types")
            if resp.status_code == 200:
                garment_options = [
                    {"label": gt["name"], "value": gt["id"]} for gt in resp.json()
                ]
        except Exception:
            pass

        try:
            resp = requests.get(f"{config.BACKEND_API_URL}/fabric-block-types")
            if resp.status_code == 200:
                fabric_options = [
                    {"label": fb["name"], "value": fb["id"]} for fb in resp.json()
                ]
        except Exception:
            pass

        try:
            resp = requests.get(f"{config.BACKEND_API_URL}/process-types")
            if resp.status_code == 200:
                process_options = [
                    {"label": proc["name"], "value": proc["id"]} for proc in resp.json()
                ]
        except Exception:
            pass

        return garment_options, fabric_options, process_options

    @app.callback(
        Output("fabric-block-type-processes-container", "children"),
        [
            Input("add-fabric-block-type-process", "n_clicks"),
            Input("remove-fabric-block-type-process", "n_clicks"),
        ],
        [State("fabric-block-type-processes-container", "children")],
    )
    def update_fabric_block_type_process_fields(add_clicks, remove_clicks, children):
        ctx = callback_context
        triggered = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None

        if children is None:
            children = []

        if triggered == "add-fabric-block-type-process":
            options = []
            try:
                resp = requests.get(f"{config.BACKEND_API_URL}/process-types")
                if resp.status_code == 200:
                    data = resp.json()
                    options = [
                        {"label": proc["name"], "value": proc["id"]} for proc in data
                    ]
            except Exception:
                pass

            new_id = len(children)
            children.append(
                html.Div(
                    [
                        html.Div(
                            [
                                dcc.Dropdown(
                                    id={
                                        "type": "fabric-block-type-process",
                                        "index": new_id,
                                    },
                                    options=options,
                                    placeholder="Select process",
                                    clearable=False,
                                    style={"width": "240px"},
                                ),
                            ],
                            style={"flex": "1"},
                        ),
                        html.Div(
                            [
                                dcc.Input(
                                    id={
                                        "type": "fabric-block-type-process-amount",
                                        "index": new_id,
                                    },
                                    placeholder="Amount",
                                    type="number",
                                    min=0,
                                    step=0.5,
                                    value=1,
                                    style={"width": "120px"},
                                ),
                            ],
                            style={"marginLeft": "12px"},
                        ),
                    ],
                    style={
                        "display": "flex",
                        "alignItems": "center",
                        "gap": "8px",
                        "marginBottom": "8px",
                    },
                )
            )

        elif triggered == "remove-fabric-block-type-process" and len(children) > 0:
            children = children[:-1]

        return children

    @app.callback(
        Output("fabric-block-type-status", "children"),
        Input("add-fabric-block-type", "n_clicks"),
        State("fabric-block-type-name", "value"),
        State("fabric-block-type-sqm", "value"),
        State({"type": "fabric-block-type-process", "index": ALL}, "value"),
        State({"type": "fabric-block-type-process-amount", "index": ALL}, "value"),
        prevent_initial_call=True,
    )
    def add_fabric_block_type(n_clicks, name, sqm, process_ids, process_amounts):
        if not name:
            return "Please enter a fabric block type name."
        if sqm is None or sqm <= 0:
            return "Please enter a valid sqm value greater than 0."

        processes = []
        for proc_id, amount in zip(process_ids, process_amounts):
            if proc_id is None:
                continue
            if amount is None:
                return "Please provide an amount for each selected process step."
            try:
                proc_amount = float(amount)
            except (TypeError, ValueError):
                return "Process step amount must be a valid number."
            if proc_amount <= 0:
                return "Process step amount must be greater than 0."
            processes.append({"process_id": proc_id, "amount": proc_amount})

        payload = {
            "name": name,
            "sqm": sqm,
            "processes": processes,
        }

        try:
            resp = requests.post(
                f"{config.BACKEND_API_URL}/fabric-block-types", json=payload
            )
            if resp.status_code in (200, 201):
                return f"Fabric block type '{name}' added."
            if resp.status_code == 409:
                return f"Fabric block type '{name}' already exists."
            return f"Error adding fabric block type: {resp.status_code}"
        except Exception as e:
            return f"Error connecting to backend: {str(e)}"

    @app.callback(
        Output("process-type-status", "children"),
        Input("add-process-type", "n_clicks"),
        State("process-type-name", "value"),
        State("process-type-unit", "value"),
        State("process-type-activity-id", "value"),
        prevent_initial_call=True,
    )
    def add_process_type(n_clicks, name, unit, activity_id):
        if not name:
            return "Please enter a process type name."
        if activity_id is None:
            return "Please enter an activity id."

        payload = {"name": name, "unit": unit, "activity_id": activity_id}

        try:
            resp = requests.post(
                f"{config.BACKEND_API_URL}/process-types",
                json=payload,
            )
            if resp.status_code in (200, 201):
                return f"Process type '{name}' added."
            if resp.status_code == 409:
                return f"Process type '{name}' already exists."
            return f"Error adding process type: {resp.status_code}"
        except Exception as e:
            return f"Error connecting to backend: {str(e)}"

    @app.callback(
        Output("material-status", "children"),
        Input("add-material", "n_clicks"),
        State("material-name", "value"),
        State("material-kg-per-sqm", "value"),
        State("material-activity-id", "value"),
        prevent_initial_call=True,
    )
    def add_or_update_material(n_clicks, name, kg_per_sqm, activity_id):
        if not name:
            return "Please enter a material name."
        if kg_per_sqm is None:
            return "Please enter kg per sqm."
        if activity_id is None:
            return "Please enter an activity id."
        try:
            kg_per_sqm_value = float(kg_per_sqm)
        except (TypeError, ValueError):
            return "kg per sqm must be a valid number."
        try:
            activity_id_value = int(activity_id)
        except (TypeError, ValueError):
            return "activity id must be a valid integer."
        if kg_per_sqm_value <= 0:
            return "kg per sqm must be greater than 0."
        if activity_id_value <= 0:
            return "activity id must be greater than 0."

        payload = {
            "name": name,
            "kg_per_sqm": kg_per_sqm_value,
            "activity_id": activity_id_value,
        }
        try:
            resp = requests.post(f"{config.BACKEND_API_URL}/materials", json=payload)
            if resp.status_code in (200, 201):
                data = resp.json()
                action = data.get("action", "saved")
                return (
                    f"Material '{data.get('name', name)}' {action} "
                    f"({data.get('kg_per_sqm', kg_per_sqm_value)} kg/sqm, "
                    f"activity {data.get('activity_id', activity_id_value)})."
                )
            return f"Error saving material: {resp.status_code}"
        except Exception as e:
            return f"Error connecting to backend: {str(e)}"

    @app.callback(
        Output("delete-garment-recipe-status", "children"),
        Output("delete-garment-recipe-type", "value"),
        Input("delete-garment-recipe", "n_clicks"),
        State("delete-garment-recipe-type", "value"),
        prevent_initial_call=True,
    )
    def delete_garment_recipe(n_clicks, garment_type_id):
        if garment_type_id is None:
            return "Please select a garment type.", garment_type_id

        try:
            resp = requests.delete(
                f"{config.BACKEND_API_URL}/garment-recipes/{garment_type_id}"
            )
            if resp.status_code in (200, 204):
                return "Garment recipe deleted.", None
            if resp.status_code == 404:
                return "Garment recipe not found.", garment_type_id
            return (
                f"Error deleting garment recipe: {resp.status_code}",
                garment_type_id,
            )
        except Exception as e:
            return f"Error connecting to backend: {str(e)}", garment_type_id

    @app.callback(
        Output("delete-fabric-block-type-status", "children"),
        Output("delete-fabric-block-type", "value"),
        Input("delete-fabric-block-type-button", "n_clicks"),
        State("delete-fabric-block-type", "value"),
        prevent_initial_call=True,
    )
    def delete_fabric_block_type(n_clicks, type_id):
        if type_id is None:
            return "Please select a fabric block type.", type_id

        try:
            resp = requests.delete(
                f"{config.BACKEND_API_URL}/fabric-block-types/{type_id}"
            )
            if resp.status_code in (200, 204):
                return "Fabric block type deleted.", None
            if resp.status_code == 404:
                return "Fabric block type not found.", type_id
            return (
                f"Error deleting fabric block type: {resp.status_code}",
                type_id,
            )
        except Exception as e:
            return f"Error connecting to backend: {str(e)}", type_id

    @app.callback(
        Output("delete-process-type-status", "children"),
        Output("delete-process-type", "value"),
        Input("delete-process-type-button", "n_clicks"),
        State("delete-process-type", "value"),
        prevent_initial_call=True,
    )
    def delete_process_type(n_clicks, type_id):
        if type_id is None:
            return "Please select a process type.", type_id

        try:
            resp = requests.delete(f"{config.BACKEND_API_URL}/process-types/{type_id}")
            if resp.status_code in (200, 204):
                return "Process type deleted.", None
            if resp.status_code == 404:
                return "Process type not found.", type_id
            return f"Error deleting process type: {resp.status_code}", type_id
        except Exception as e:
            return f"Error connecting to backend: {str(e)}", type_id

    @app.callback(
        Output("recipe-fabric-blocks-container", "children"),
        [
            Input("add-recipe-fabric-block", "n_clicks"),
            Input("remove-recipe-fabric-block", "n_clicks"),
        ],
        [State("recipe-fabric-blocks-container", "children")],
    )
    def update_recipe_fabric_block_fields(add_clicks, remove_clicks, children):
        ctx = callback_context
        triggered = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None

        if children is None:
            children = []

        if triggered == "add-recipe-fabric-block":
            fabric_block_options = []
            material_options = []
            try:
                resp = requests.get(f"{config.BACKEND_API_URL}/fabric-block-types")
                if resp.status_code == 200:
                    data = resp.json()
                    fabric_block_options = [
                        {"label": fb["name"], "value": fb["id"]} for fb in data
                    ]
            except Exception:
                pass

            try:
                resp = requests.get(f"{config.BACKEND_API_URL}/materials")
                if resp.status_code == 200:
                    data = resp.json()
                    material_options = [
                        {
                            "label": f"{m['name']} ({m['kg_per_sqm']} kg/sqm)",
                            "value": m["id"],
                        }
                        for m in data
                    ]
            except Exception:
                pass

            new_id = len(children)
            children.append(
                html.Div(
                    [
                        html.Div(
                            [
                                dcc.Dropdown(
                                    id={
                                        "type": "recipe-fabric-block",
                                        "index": new_id,
                                    },
                                    options=fabric_block_options,
                                    placeholder="Select fabric block type",
                                    clearable=False,
                                    style={"width": "240px"},
                                ),
                                dcc.Dropdown(
                                    id={
                                        "type": "recipe-fabric-block-material",
                                        "index": new_id,
                                    },
                                    options=material_options,
                                    placeholder="Select material",
                                    clearable=False,
                                    style={"width": "240px", "marginTop": "6px"},
                                ),
                            ],
                            style={"flex": "1"},
                        ),
                        html.Div(
                            [
                                dcc.Input(
                                    id={
                                        "type": "recipe-fabric-block-amount",
                                        "index": new_id,
                                    },
                                    placeholder="Amount",
                                    type="number",
                                    min=1,
                                    step=1,
                                    value=1,
                                    style={"width": "120px"},
                                ),
                            ],
                            style={"marginLeft": "12px"},
                        ),
                    ],
                    style={
                        "display": "flex",
                        "alignItems": "center",
                        "gap": "8px",
                        "marginBottom": "8px",
                    },
                )
            )

        elif triggered == "remove-recipe-fabric-block" and len(children) > 0:
            children = children[:-1]

        return children

    @app.callback(
        Output("recipe-processes-container", "children"),
        [
            Input("add-recipe-process", "n_clicks"),
            Input("remove-recipe-process", "n_clicks"),
        ],
        [State("recipe-processes-container", "children")],
    )
    def update_recipe_process_fields(add_clicks, remove_clicks, children):
        ctx = callback_context
        triggered = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None

        if children is None:
            children = []

        if triggered == "add-recipe-process":
            options = []
            try:
                resp = requests.get(f"{config.BACKEND_API_URL}/process-types")
                if resp.status_code == 200:
                    data = resp.json()
                    options = [
                        {"label": proc["name"], "value": proc["id"]} for proc in data
                    ]
            except Exception:
                pass

            new_id = len(children)
            children.append(
                html.Div(
                    [
                        html.Div(
                            [
                                dcc.Dropdown(
                                    id={"type": "recipe-process", "index": new_id},
                                    options=options,
                                    placeholder="Select process",
                                    clearable=False,
                                    style={"width": "240px"},
                                ),
                            ],
                            style={"flex": "1"},
                        ),
                        html.Div(
                            [
                                dcc.Input(
                                    id={
                                        "type": "recipe-process-amount",
                                        "index": new_id,
                                    },
                                    placeholder="Amount",
                                    type="number",
                                    min=0,
                                    step=0.5,
                                    value=1,
                                    style={"width": "120px"},
                                ),
                            ],
                            style={"marginLeft": "12px"},
                        ),
                    ],
                    style={
                        "display": "flex",
                        "alignItems": "center",
                        "gap": "8px",
                        "marginBottom": "8px",
                    },
                )
            )

        elif triggered == "remove-recipe-process" and len(children) > 0:
            children = children[:-1]

        return children

    @app.callback(
        Output("garment-recipe-status", "children"),
        Input("add-garment-recipe", "n_clicks"),
        State("recipe-garment-type-name", "value"),
        State({"type": "recipe-fabric-block", "index": ALL}, "value"),
        State({"type": "recipe-fabric-block-material", "index": ALL}, "value"),
        State({"type": "recipe-fabric-block-amount", "index": ALL}, "value"),
        State({"type": "recipe-process", "index": ALL}, "value"),
        State({"type": "recipe-process-amount", "index": ALL}, "value"),
        prevent_initial_call=True,
    )
    def add_garment_recipe(
        n_clicks,
        garment_type_name,
        fabric_block_ids,
        fabric_material_ids,
        fabric_block_amounts,
        process_ids,
        process_amounts,
    ):
        if not garment_type_name:
            return "Please enter a garment type name."

        fabric_blocks = []
        material_ids = set()
        for fb_id, material_id, amount in zip(
            fabric_block_ids, fabric_material_ids, fabric_block_amounts
        ):
            if fb_id is None:
                continue
            if material_id is None:
                return "Please select a material for each fabric block."
            material_ids.add(material_id)
            try:
                fb_amount = int(amount) if amount is not None else 1
            except (TypeError, ValueError):
                fb_amount = 1
            if fb_amount <= 0:
                return "Fabric block amounts must be greater than 0."
            fabric_blocks.append(
                {
                    "type_id": fb_id,
                    "amount": fb_amount,
                }
            )

        if not fabric_blocks:
            return "Please add at least one fabric block."

        processes = []
        for proc_id, amount in zip(process_ids, process_amounts):
            if proc_id is None:
                continue
            if amount is None:
                return "Please provide an amount for each selected process."
            try:
                proc_amount = float(amount)
            except (TypeError, ValueError):
                return "Process amount must be a valid number."
            if proc_amount <= 0:
                return "Process amount must be greater than 0."
            processes.append({"process_id": proc_id, "amount": proc_amount})

        try:
            resp = requests.post(
                f"{config.BACKEND_API_URL}/garment-types",
                json={"name": garment_type_name},
            )
            if resp.status_code in (200, 201):
                garment_type_id = resp.json().get("id")
            elif resp.status_code == 409:
                existing = requests.get(f"{config.BACKEND_API_URL}/garment-types")
                if existing.status_code != 200:
                    return "Garment type already exists, but lookup failed."
                garment_type_id = next(
                    (
                        gt["id"]
                        for gt in existing.json()
                        if gt["name"] == garment_type_name
                    ),
                    None,
                )
                if garment_type_id is None:
                    return "Garment type already exists, but could not be found."
            else:
                return f"Error creating garment type: {resp.status_code}"

            payload = {
                "garment_type_name": garment_type_name,
                "fabric_blocks": fabric_blocks,
                "materials": [
                    {"material_id": material_id}
                    for material_id in sorted(material_ids)
                ],
                "processes": processes,
            }

            resp = requests.post(
                f"{config.BACKEND_API_URL}/garment-recipes", json=payload
            )
            if resp.status_code in (200, 201):
                return "Garment recipe saved."
            return f"Error saving garment recipe: {resp.status_code}"
        except Exception as e:
            return f"Error connecting to backend: {str(e)}"

    @app.callback(
        Output("activity-search-status", "children"),
        Output("activity-search-results", "children"),
        Input("activity-search-button", "n_clicks"),
        State("activity-search-query", "value"),
        prevent_initial_call=True,
    )
    def search_activities(n_clicks, query):
        if not query:
            return "Please enter a search term.", []

        try:
            resp = requests.post(
                f"{config.BACKEND_API_URL}/activity-search", json={"query": query}
            )
            if resp.status_code != 200:
                return f"Search failed: {resp.status_code}", []

            results = resp.json().get("results", [])
            if not results:
                return "No results found.", []

            header = html.Thead(
                html.Tr(
                    [
                        html.Th("Activity ID"),
                        html.Th("Location"),
                        html.Th("Name"),
                        html.Th("Reference Product"),
                    ]
                )
            )
            rows = [
                html.Tr(
                    [
                        html.Td(item.get("id")),
                        html.Td(item.get("location")),
                        html.Td(item.get("name")),
                        html.Td(item.get("reference_product")),
                    ]
                )
                for item in results
            ]
            table = html.Table([header, html.Tbody(rows)])
            return f"Found {len(results)} result(s).", table
        except Exception as e:
            return f"Error connecting to backend: {str(e)}", []
