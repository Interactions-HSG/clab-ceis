from dash import dcc, html


def get_recipe_layout():
    return html.Div(
        [
            html.Div(
                [
                    dcc.Link(
                        "Home",
                        href="/",
                        id="home-link",
                    ),
                    html.H1("Add Recipe"),
                ],
                className="wrapper",
            ),
        ]
    )
