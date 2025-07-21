import pytest
from playwright.sync_api import Page
from datetime import datetime

BASE_URL = "http://localhost:5000/"

def test_checkout_bnpl(page: Page):
    page.goto(BASE_URL + "checkout")
    h2_text = page.locator("h2").inner_text()
    if "checkout" not in h2_text.lower():
        print(page.content())  # Print the HTML for debugging
    assert "checkout" in h2_text.lower()
    # Fill checkout form
    name = f"TestUser_{datetime.now().strftime('%H%M%S')}"
    page.fill('input[name="user_name"]', name)
    page.select_option('select[name="region"]', 'US')
    page.select_option('select[name="product"]', value=page.locator('select[name="product"] option').first.get_attribute('value'))
    page.select_option('select[name="provider"]', value=page.locator('select[name="provider"] option').first.get_attribute('value'))
    page.check('input[name="consent"]')
    page.click('button[type="submit"]')
    # Should show activation or error
    page.wait_for_timeout(1000)
    assert page.locator('.alert-success, .alert-danger').is_visible() 