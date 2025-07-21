import pytest
from playwright.sync_api import Page
from datetime import datetime, timedelta

BASE_URL = "http://localhost:5000/"

def test_register_user(page: Page):
    page.goto(BASE_URL + "register")
    assert page.locator("h1, h2").inner_text().lower().find("register") != -1
    # Fill registration form
    name = f"TestUser_{datetime.now().strftime('%H%M%S')}"
    dob = (datetime.now() - timedelta(days=365*20)).strftime('%Y-%m-%d')  # 20 years old
    page.fill('input[name="name"]', name)
    page.fill('input[name="dob"]', dob)
    page.click('button[type="submit"]')
    # Should redirect to home and show success message
    page.wait_for_url(BASE_URL)
    assert page.locator('.toast-body, .alert-info').inner_text().lower().find("registration successful") != -1 