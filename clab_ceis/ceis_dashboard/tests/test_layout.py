from unittest.mock import patch

from dash import Dash

from main import CeisMonitor
from pages.ui import page_hero


def test_app_shell_does_not_render_global_home_link():
    with (
        patch("pages.home.fetch_garment_types", return_value=[]),
        patch("ceis_callbacks.get_callbacks"),
    ):
        monitor = CeisMonitor(Dash(__name__))

    children = list(monitor.layout.children)

    assert children[1].id == "page-content"
    assert "page-home-link" not in str(monitor.layout)


def test_page_hero_home_link_is_opt_in_for_subpages():
    home_hero = page_hero("Operations", "Welcome", "Intro")
    subpage_hero = page_hero("Strategy", "Board", "Intro", show_home=True)

    assert "page-home-link" not in str(home_hero)
    assert "page-home-link" in str(subpage_hero)
    assert "page-hero-with-action" in str(subpage_hero)
