import pytest
from playwright.sync_api import Page
from datetime import datetime, timedelta

BASE_URL = "http://localhost:5000/"

@pytest.mark.parametrize("name, dob, expect_success, expect_error", [
    (lambda: f"TestUser_{datetime.now().strftime('%H%M%S')}", (datetime.now() - timedelta(days=365*20)).strftime('%Y-%m-%d'), True, None),
    (lambda: f"Underage_{datetime.now().strftime('%H%M%S')}", (datetime.now() - timedelta(days=365*16)).strftime('%Y-%m-%d'), False, "at least 18 years old"),
    (lambda: "", (datetime.now() - timedelta(days=365*20)).strftime('%Y-%m-%d'), False, None),
])
def test_register_user(page: Page, name, dob, expect_success, expect_error):
    page.goto(BASE_URL + "register")
    if callable(name):
        name = name()
    page.fill('input[name="name"]', name)
    page.fill('input[name="dob"]', dob)
    page.click('button[type="submit"]')
    if expect_success:
        page.wait_for_url(BASE_URL)
        assert page.locator('.toast-body, .alert-info').inner_text().lower().find("registration successful") != -1
        # Check user appears in dashboard
        page.goto(BASE_URL + "dashboard")
        assert page.locator(f"table tbody tr:has-text('{name}')").is_visible()
    else:
        # Should stay on register page or show error
        if expect_error:
            assert page.locator('.alert, .toast-body').inner_text().lower().find(expect_error) != -1
        else:
            # Required field error (browser validation)
            assert page.url.endswith("/register") 