from dash import dcc, html


def page_home_link():
    return dcc.Link(
        "Home",
        href="/",
        className="page-home-link",
        title="Go to home page",
    )


def app_topbar():
    return html.Header(
        [
            html.Div("Circular Lab Cockpit", className="brand"),
            html.Nav(
                [
                    dcc.Link("Home", href="/", className="home-nav-link"),
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


def page_hero(kicker: str, title: str, intro: str, show_home: bool = False):
    children = [
        html.Div(
            [
                html.Div(kicker, className="page-kicker"),
                html.H1(title),
                html.P(intro, className="page-intro"),
            ],
            className="page-hero-copy",
        )
    ]
    if show_home:
        children.append(page_home_link())

    return html.Section(
        children,
        className="page-hero page-hero-with-action" if show_home else "page-hero",
    )
