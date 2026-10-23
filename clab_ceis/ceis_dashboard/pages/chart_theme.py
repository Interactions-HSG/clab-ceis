from __future__ import annotations

import plotly.graph_objects as go


CHART_PALETTE = (
    "#1f6a52",  # forest green
    "#e3a928",  # warm gold
    "#d45d3a",  # terracotta
    "#3f78b5",  # slate blue
    "#8a5fa8",  # muted purple
    "#159a9c",  # teal
    "#c85477",  # berry
    "#7a8b3a",  # olive
)


def component_marker(component_name: str, index: int) -> dict:
    """Return a distinct, semantically stable marker for a chart component."""
    name = component_name.lower()
    saved = name.startswith("saved:")
    semantic_colors = (
        ("transport", "#d45d3a"),
        ("repair", "#1f6a52"),
        ("preparation", "#159a9c"),
        ("new material", "#e3a928"),
        ("material production", "#e3a928"),
        ("fabric-block", "#3f78b5"),
        ("garment assembly", "#8a5fa8"),
    )
    color = next(
        (
            semantic_color
            for keyword, semantic_color in semantic_colors
            if keyword in name
        ),
        CHART_PALETTE[index % len(CHART_PALETTE)],
    )
    marker = {
        "color": color,
        "line": {"color": "rgba(24, 53, 45, 0.25)", "width": 0.7},
    }
    if saved:
        marker["pattern"] = {
            "shape": "/",
            "fgcolor": "rgba(255, 255, 255, 0.72)",
            "size": 7,
            "solidity": 0.22,
        }
    return marker


def apply_bar_chart_theme(figure: go.Figure) -> go.Figure:
    """Apply the shared Refashion visual language to a Plotly bar chart."""
    figure.update_layout(
        colorway=CHART_PALETTE,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        hovermode="closest",
        bargap=0.3,
        barcornerradius=6,
        font={
            "family": "Inter, ui-sans-serif, system-ui, sans-serif",
            "color": "#18352d",
            "size": 12,
        },
        hoverlabel={
            "bgcolor": "#18352d",
            "bordercolor": "#18352d",
            "font": {"color": "#fbf7ed"},
        },
        legend={
            "bgcolor": "rgba(251, 247, 237, 0.78)",
            "bordercolor": "rgba(24, 53, 45, 0.14)",
            "borderwidth": 1,
        },
        uniformtext_minsize=9,
        uniformtext_mode="hide",
    )
    figure.update_xaxes(
        showgrid=False,
        linecolor="rgba(24, 53, 45, 0.20)",
        tickfont={"color": "#18352d"},
    )
    figure.update_yaxes(
        gridcolor="rgba(24, 53, 45, 0.10)",
        zeroline=True,
        zerolinecolor="rgba(24, 53, 45, 0.55)",
        zerolinewidth=2,
        tickfont={"color": "#68716b"},
    )
    return figure
