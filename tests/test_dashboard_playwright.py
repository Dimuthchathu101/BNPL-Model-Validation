import pytest
from playwright.sync_api import Page

BASE_URL = "http://localhost:5000/"

def test_dashboard_loads(page: Page):
    page.goto(BASE_URL + "dashboard")
    assert page.locator("h1").inner_text().lower().find("dashboard") != -1
    # There should be a table with at least one user row (after registration test)
    rows = page.locator("table tbody tr")
    assert rows.count() > 0 