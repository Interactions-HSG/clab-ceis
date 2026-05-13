from dash import dcc, html


def app_topbar():
    return html.Header(
        [
            html.Div("Circular Lab Cockpit", className="brand"),
            html.Nav(
                [
                    dcc.Link("Inventory", href="/"),
                    dcc.Link("Strategy", href="/dashboard"),
                    dcc.Link("Designer", href="/garment-designer"),
                    dcc.Link("Add Recipe", href="/add-recipe"),
                    dcc.Link("Scenario Planner", href="/designer-balance"),
                ],
                className="nav-links",
            ),
        ],
        className="app-topbar",
    )


def page_hero(kicker: str, title: str, intro: str):
    return html.Section(
        [
            html.Div(kicker, className="page-kicker"),
            html.H1(title),
            html.P(intro, className="page-intro"),
        ],
        className="page-hero",
    )
