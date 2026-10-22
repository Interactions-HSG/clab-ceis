from __future__ import annotations

import plotly.graph_objects as go
from dash import dcc, html

from ceis_shop.layouts.ui import shop_home_link, shop_topbar


def scenarios_page():
    """Original end-of-cycle comparison page."""
    return html.Div(
        className="wrapper shop-page impact-page",
        children=[
            shop_topbar("impact"),
            html.Section(
                [
                    html.Div(
                        [
                            html.Div("Circular services", className="shop-kicker"),
                            html.H1("Understand the impact of what comes next", className="header-title"),
                            html.P(
                                "A simple comparison of repair and replacement routes for a Circular Lab garment.",
                                className="shop-intro",
                            ),
                        ],
                        className="shop-hero-copy",
                    ),
                    shop_home_link(),
                ],
                className="shop-hero shop-hero-with-action",
            ),
            html.Section(
                className="panel",
                children=[
                    html.Details(
                        [
                            html.Summary("Calculation route"),
                            html.P(
                                "Production in Bucharest, repair in St. Gallen, and customer location in Sigmaringen."
                            ),
                        ],
                        className="offer-details",
                    ),
                    dcc.Loading(
                        id="customer-repair-loading",
                        type="circle",
                        children=html.Div(id="customer-repair-content"),
                        color="green",
                    ),
                ],
            ),
        ],
    )


def repair_return_page():
    """Interactive sold-garment repair and return CO2 explorer."""
    return html.Div(
        className="wrapper shop-page circular-care-page",
        children=[
            shop_topbar("care"),
            html.Section(
                [
                    html.Div(
                        [
                            html.Div("Circular services", className="shop-kicker"),
                            html.H1(
                                "Find the best next step for your garment",
                                className="header-title",
                            ),
                            html.P(
                                "Tell us what happened and compare self-repair, professional repair, replacement, and return at a glance.",
                                className="shop-intro",
                            ),
                        ],
                        className="shop-hero-copy",
                    ),
                    shop_home_link(),
                ],
                className="shop-hero shop-hero-with-action",
            ),
            html.Section(
                className="panel",
                children=[
                    dcc.Loading(
                        id="customer-circular-loading",
                        type="circle",
                        children=html.Div(id="customer-circular-content"),
                        color="green",
                    ),
                ],
            ),
        ],
    )


def render_scenario_explorer(options_payload: dict) -> html.Div:
    garments = options_payload.get("garments", [])
    damages = options_payload.get("damages", [])
    if not garments:
        return html.P("No bought garments are available for comparison.")
    if not damages:
        return html.P("No damage types are configured.")

    garment_options = [
        {
            "label": _customer_garment_label(garment),
            "value": garment["id"],
        }
        for garment in garments
    ]
    damage_options = [
        {"label": damage["label"], "value": damage["code"]}
        for damage in damages
    ]

    return html.Div(
        [
            html.Div(
                [
                    html.Div(
                        [
                            html.Label("Your garment", htmlFor="circular-garment"),
                            dcc.Dropdown(
                                id="circular-garment",
                                options=garment_options,
                                value=garment_options[0]["value"],
                                clearable=False,
                            ),
                        ],
                        className="field-panel",
                    ),
                    html.Div(
                        [
                            html.Label(
                                "Distance to repair centre (km, one way)",
                                htmlFor="circular-distance",
                            ),
                            dcc.Input(
                                id="circular-distance",
                                type="number",
                                min=0,
                                step=10,
                                value=1000,
                            ),
                        ],
                        className="field-panel",
                    ),
                    html.Div(
                        [
                            html.Label("Damage", htmlFor="circular-damage"),
                            dcc.Dropdown(
                                id="circular-damage",
                                options=damage_options,
                                value="small_hole"
                                if any(
                                    option["value"] == "small_hole"
                                    for option in damage_options
                                )
                                else damage_options[0]["value"],
                                clearable=False,
                            ),
                        ],
                        className="field-panel",
                    ),
                    html.Div(
                        [
                            html.Div("Electricity factor", className="field-label"),
                            dcc.Checklist(
                                id="circular-use-higher-electricity-factor",
                                options=[
                                    {
                                        "label": "Use higher electricity emission factor",
                                        "value": "higher_factor",
                                    }
                                ],
                                value=[],
                                className="circular-factor-switch",
                            ),
                            html.P(
                                "Uses a higher electricity emissions factor for "
                                "calculations on this page only.",
                                className="field-help",
                            ),
                        ],
                        className="field-panel higher-electricity-factor-control",
                    ),
                ],
                className="form-grid scenario-controls",
            ),
            dcc.Loading(
                type="circle",
                color="green",
                children=html.Div(id="circular-scenario-results"),
            ),
            html.Div(
                id="circular-garment-return-result",
                className="repair-order-result",
                role="status",
            ),
        ]
    )


def _customer_garment_label(garment: dict) -> str:
    """Return a customer-friendly selector label without exposing database IDs."""
    name = garment.get("name")
    if name:
        return str(name)

    label = str(garment.get("label", "Your garment"))
    return label.split("· garment #", maxsplit=1)[0].strip()


def _format_number(value: float | int | None) -> str:
    return "—" if value is None else f"{float(value):.3f}"


def _scenario_card(
    title: str,
    scenario: dict,
    subtitle: str,
    show_saving_percent: bool = False,
    action_label: str | None = None,
    action_id: str | None = None,
) -> html.Div:
    if not scenario.get("available"):
        return html.Div(
            [
                html.Div(title, className="co2-metric-title"),
                html.Div("Not available", className="co2-metric-value"),
                html.Div(
                    scenario.get("reason", "This scenario cannot be calculated."),
                    className="co2-metric-subtitle",
                ),
            ],
            className="co2-metric-card",
        )

    saving = scenario.get("saving_co2eq")
    saving_text = f"{_format_number(saving)} kg CO2eq saved"
    saving_percent = scenario.get("saving_percent")
    if show_saving_percent and saving_percent is not None:
        saving_text += f" vs new garment ({float(saving_percent):.1f}%)"
    children = [
        html.Div(title, className="co2-metric-title"),
        html.Div(
            f"{_format_number(scenario.get('total_co2eq'))} kg CO2eq",
            className="co2-metric-value",
        ),
        html.Div(
            f"{subtitle} · {saving_text}",
            className="co2-metric-subtitle",
        ),
    ]
    if action_label and action_id:
        children.append(
            html.Button(
                action_label,
                id=action_id,
                n_clicks=0,
                className="repair-action-button",
            )
        )
    return html.Div(
        children,
        className=(
            "co2-metric-card repair-action-card"
            if action_label and action_id
            else "co2-metric-card"
        ),
    )


def _expected_return_saving_card(scenario: dict) -> html.Div:
    if not scenario.get("available"):
        return html.Div(
            [
                html.Div("Expected CO2 saving", className="co2-metric-title"),
                html.Div("Not available", className="co2-metric-value"),
                html.Div(
                    scenario.get(
                        "reason",
                        "Whole-garment reuse cannot be calculated.",
                    ),
                    className="co2-metric-subtitle",
                ),
            ],
            className="co2-metric-card",
        )

    return html.Div(
        [
            html.Div("Expected CO2 saving", className="co2-metric-title"),
            html.Div(
                f"{_format_number(scenario.get('saving_co2eq'))} kg CO2eq",
                className="co2-metric-value",
            ),
            html.Div(
                [
                    html.Strong(
                        "Reusing this garment saves "
                        f"{_format_number(scenario.get('saving_co2eq'))} kg CO2eq "
                        "compared with buying a new one."
                    ),
                    html.Span(
                        "Transport, repair, and preparation add "
                        f"{_format_number(scenario.get('total_co2eq'))} kg CO2eq."
                    ),
                ],
                className="co2-metric-subtitle return-saving-explanation",
            ),
        ],
        className="co2-metric-card",
    )


def _component_bar_chart(
    title: str,
    bars: list[tuple[str, list[dict]]],
    barmode: str = "stack",
) -> go.Figure:
    """Build a stacked bar chart directly from backend calculation components."""
    component_names: list[str] = []
    values_by_bar: list[dict[str, float]] = []
    for _, components in bars:
        values = {
            str(component["name"]): float(component.get("co2eq", 0))
            for component in components
        }
        values_by_bar.append(values)
        for name in values:
            if name not in component_names:
                component_names.append(name)

    labels = [label for label, _ in bars]
    figure = go.Figure()
    for component_name in component_names:
        values = [values.get(component_name, 0) for values in values_by_bar]
        figure.add_bar(
            name=component_name,
            x=labels,
            y=values,
            text=[f"{value:.3f}" if value else "" for value in values],
            textposition="inside",
            hovertemplate=(
                component_name + ": %{y:.3f} kg CO2eq<extra></extra>"
            ),
        )

    figure.update_layout(
        barmode=barmode,
        title={"text": title, "x": 0.02, "xanchor": "left"},
        xaxis_title=None,
        yaxis_title="kg CO2eq",
        legend_title_text="Calculation components",
        margin={"l": 55, "r": 20, "t": 60, "b": 55},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        hovermode="closest",
        uniformtext_minsize=9,
        uniformtext_mode="hide",
    )
    figure.update_yaxes(
        gridcolor="rgba(31, 46, 42, 0.12)",
        zeroline=True,
        zerolinecolor="rgba(31, 46, 42, 0.65)",
        zerolinewidth=2,
    )
    return figure


def _saved_components(components: list[dict]) -> list[dict]:
    return [
        {
            "name": f"Saved: {component['name']}",
            "co2eq": -float(component.get("co2eq", 0)),
        }
        for component in components
    ]


def render_scenario_results(payload: dict) -> html.Div:
    garment = payload.get("garment", {})
    damage = payload.get("damage", {})
    repair = payload.get("repair", {})
    return_scenarios = payload.get("return", {})
    process_names = [
        detail.get("process", "Unknown process")
        for detail in damage.get("processes", [])
    ]
    process_label = ", ".join(process_names) or "Manual assessment"
    self_repair = repair.get("self_repair", {})
    professional_repair = repair.get("professional_repair", {})
    new_garment = repair.get("new_garment", {})
    whole_garment = return_scenarios.get("whole_garment", {})

    repair_figure = _component_bar_chart(
        "Repair alternatives: emissions by component",
        [
            ("Self-repair", self_repair.get("components", [])),
            (
                "Professional repair",
                professional_repair.get("components", []),
            ),
            ("New garment", new_garment.get("components", [])),
        ],
    )
    return_figure = _component_bar_chart(
        "Return alternative: CO2 needed (+) and CO2 saved (-)",
        [
            (
                "Expected CO2 saving",
                [
                    *whole_garment.get("components", []),
                    *_saved_components(
                        whole_garment.get("reference_components", [])
                    ),
                ],
            ),
        ],
        barmode="relative",
    )
    return html.Div(
        [
            html.Div(
                [
                    html.Strong(garment.get("name", "Your garment")),
                    html.Span(f"Damage process: {process_label}"),
                    html.Span(
                        f"{garment.get('fabric_block_count', 0)} fabric pieces · "
                        f"{_format_number(garment.get('weight_kg'))} kg"
                    ),
                    html.Span(
                        "Pieces to replace: "
                        f"{damage.get('replacement_block_count', 0)}"
                    ),
                ],
                className="scenario-summary panel-muted",
            ),
            html.H2("Repair alternatives"),
            html.Div(
                [
                    _scenario_card(
                        "Self-repair",
                        self_repair,
                        "Same repair processes; kit or material transported once",
                        show_saving_percent=True,
                        action_label="Order self-repair kit",
                        action_id="order-self-repair-kit",
                    ),
                    _scenario_card(
                        "Professional repair",
                        professional_repair,
                        "Same repair processes; garment transported twice",
                        show_saving_percent=True,
                        action_label="Send for professional repair",
                        action_id="request-professional-repair",
                    ),
                    _scenario_card(
                        "New garment",
                        new_garment,
                        "Reference scenario",
                        show_saving_percent=True,
                    ),
                ],
                className="co2-metric-grid",
            ),
            html.Div(
                id="circular-repair-order-result",
                className="repair-order-result",
                role="status",
            ),
            html.H2("Return alternatives"),
            html.Div(
                [_expected_return_saving_card(whole_garment)],
                className="co2-metric-grid return-scenario-grid",
            ),
            html.Div(
                html.Button(
                    "Return garment",
                    id="return-garment-button",
                    n_clicks=0,
                ),
                className="scenario-chart-actions",
            ),
            html.Div(
                html.Button(
                    "View detailed bar charts",
                    id="toggle-circular-charts",
                    n_clicks=0,
                ),
                className="scenario-chart-actions",
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.P(
                                "Each stacked bar adds up to the total shown "
                                "in the repair summary.",
                            ),
                            dcc.Graph(
                                id="repair-component-chart",
                                figure=repair_figure,
                                config={"displayModeBar": False},
                            ),
                        ],
                        className="co2-detail-panel",
                    ),
                    html.Div(
                        [
                            html.P(
                                "Positive sections are the CO2 needed for return, "
                                "repair, and preparation. Negative sections are "
                                "the new-garment production CO2 saved.",
                            ),
                            dcc.Graph(
                                id="return-component-chart",
                                figure=return_figure,
                                config={"displayModeBar": False},
                            ),
                        ],
                        className="co2-detail-panel",
                    ),
                ],
                id="circular-detailed-charts",
                className="scenario-chart-grid",
                hidden=True,
            ),
            html.Details(
                [
                    html.Summary("Assumptions"),
                    html.Ul(
                        [html.Li(item) for item in payload.get("assumptions", [])]
                    ),
                ],
                className="scenario-assumptions",
            ),
        ],
        className="scenario-results",
    )
