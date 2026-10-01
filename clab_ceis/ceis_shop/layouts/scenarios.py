from __future__ import annotations

import plotly.graph_objects as go
from dash import dcc, html

from ceis_shop.layouts.ui import shop_home_link


def scenarios_page():
    """Original end-of-life comparison page."""
    return html.Div(
        className="wrapper",
        children=[
            html.Header(
                [
                    html.Div("Circular Lab Shop", className="brand"),
                    html.Nav(
                        [
                            dcc.Link("Home", href="/", className="home-nav-link"),
                            dcc.Link("End of life", href="/scenarios"),
                        ],
                        className="shop-actions",
                    ),
                ],
                className="shop-topbar",
            ),
            html.Section(
                [
                    html.Div(
                        [
                            html.Div("Circular services", className="shop-kicker"),
                            html.H1("End of Life Options", className="header-title"),
                            html.P(
                                "Compare practical return, repair, and replacement "
                                "scenarios for the current garment journey.",
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
                    html.P(
                        "Manufacturer: Bucharest, Repair Center: St. Gallen, "
                        "Consumer: Sigmaringen."
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
        className="wrapper",
        children=[
            html.Header(
                [
                    html.Div("Circular Lab Shop", className="brand"),
                    html.Nav(
                        [
                            dcc.Link("Home", href="/", className="home-nav-link"),
                            dcc.Link("End of life", href="/scenarios"),
                            dcc.Link("Repair and return", href="/repair-return"),
                        ],
                        className="shop-actions",
                    ),
                ],
                className="shop-topbar",
            ),
            html.Section(
                [
                    html.Div(
                        [
                            html.Div("Circular services", className="shop-kicker"),
                            html.H1(
                                "Repair and return scenarios",
                                className="header-title",
                            ),
                            html.P(
                                "Compare the CO2 impact of repair, whole-garment "
                                "reuse, and fabric-block recovery without selecting "
                                "a winner.",
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
        return html.P("No sold garments are available for comparison.")
    if not damages:
        return html.P("No damage types are configured.")

    garment_options = [
        {"label": garment["label"], "value": garment["id"]}
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
                            html.Label("Sold garment", htmlFor="circular-garment"),
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
                                "Transport distance (km, one way)",
                                htmlFor="circular-distance",
                            ),
                            dcc.Input(
                                id="circular-distance",
                                type="number",
                                min=0,
                                step=10,
                                value=100,
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
                                "1.2525767471944982 kg CO2eq/kWh (activity 6566). "
                                "Applies only to calculations on this page.",
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
        ]
    )


def _format_number(value: float | int | None) -> str:
    return "—" if value is None else f"{float(value):.3f}"


def _scenario_card(
    title: str,
    scenario: dict,
    subtitle: str,
    show_saving_percent: bool = False,
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
    return html.Div(
        [
            html.Div(title, className="co2-metric-title"),
            html.Div(
                f"{_format_number(scenario.get('total_co2eq'))} kg CO2eq",
                className="co2-metric-value",
            ),
            html.Div(
                f"{subtitle} · {saving_text}",
                className="co2-metric-subtitle",
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
    fabric_blocks = return_scenarios.get("fabric_blocks", {})

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
        "Return alternatives: impact (+) and CO2 saved (-)",
        [
            (
                "Reuse whole garment",
                [
                    *whole_garment.get("components", []),
                    *_saved_components(
                        whole_garment.get("reference_components", [])
                    ),
                ],
            ),
            (
                "Recover fabric blocks",
                [
                    *fabric_blocks.get("components", []),
                    *_saved_components(
                        fabric_blocks.get("reference_components", [])
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
                    html.Strong(
                        f"{garment.get('name', 'Garment')} "
                        f"#{garment.get('id', '')}"
                    ),
                    html.Span(f"Damage process: {process_label}"),
                    html.Span(
                        f"{garment.get('fabric_block_count', 0)} blocks · "
                        f"{_format_number(garment.get('weight_kg'))} kg"
                    ),
                    html.Span(
                        "Blocks to replace: "
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
                    ),
                    _scenario_card(
                        "Professional repair",
                        professional_repair,
                        "Same repair processes; garment transported twice",
                        show_saving_percent=True,
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
            html.H2("Return alternatives"),
            html.Div(
                [
                    _scenario_card(
                        "Reuse whole garment",
                        whole_garment,
                        "Transport, repair, and preparation",
                    ),
                    _scenario_card(
                        "Recover fabric blocks",
                        fabric_blocks,
                        "Transport and recovery preparation",
                    ),
                ],
                className="co2-metric-grid return-scenario-grid",
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
                                "Positive sections are return emissions; negative "
                                "sections are the new-production CO2 saved.",
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
