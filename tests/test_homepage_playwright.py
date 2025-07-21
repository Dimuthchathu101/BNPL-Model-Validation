import pytest
from playwright.sync_api import Page

BASE_URL = "http://localhost:5000/"

def test_homepage_loads(page: Page):
    page.goto(BASE_URL)
    assert page.title() == "BNPL Demo Home"
    assert page.locator("h1").inner_text() == "BNPL Model Validation Demo"
    # Check navigation links
    nav_links = ["Dashboard", "Merchant", "Checkout", "Register"]
    for link in nav_links:
        assert page.locator(f"nav a:has-text('{link}')").is_visible() 