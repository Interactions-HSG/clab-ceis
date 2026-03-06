from __future__ import annotations

from layouts.home import home_page
from layouts.skirt import skirt_page
from layouts.top import top_page


def test_home_page_contains_expected_links():
    layout = home_page()
    text = str(layout)

    assert "Welcome to Our Clothing Order Website" in text
    assert "/skirt" in text
    assert "/top" in text


def test_product_pages_have_back_link():
    assert "Back to Home" in str(top_page())
    assert "Back to Home" in str(skirt_page())
