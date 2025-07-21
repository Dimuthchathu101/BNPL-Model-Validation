import pytest
from playwright.sync_api import Page, expect
from datetime import datetime
import os

BASE_URL = "http://localhost:5000/"

@pytest.mark.parametrize("consent, product_index, expect_success, expect_kyc", [
    (True, 0, True, False),   # Normal product, consent given
    (False, 0, False, False), # Normal product, no consent
    (True, 1, True, True),   # High-value product (Smart Watch, price > 150), consent given
])
def test_checkout_bnpl(page: Page, consent, product_index, expect_success, expect_kyc):
    page.goto(BASE_URL + "checkout")
    name = f"TestUser_{datetime.now().strftime('%H%M%S')}"
    page.fill('input[name="user_name"]', name)
    page.select_option('select[name="region"]', 'US')
    # Select product by index
    product_options = page.locator('select[name="product"] option')
    value = product_options.nth(product_index).get_attribute('value')
    page.select_option('select[name="product"]', value=value)
    page.select_option('select[name="provider"]', value=page.locator('select[name="provider"] option').first.get_attribute('value'))
    if consent:
        page.check('input[name="consent"]')
    page.click('button[type="submit"]')
    page.wait_for_timeout(1000)
    if expect_kyc:
        assert page.locator('.alert-danger:has-text("KYC")').is_visible()
    if expect_success:
        assert page.locator('.alert-success').is_visible()
    else:
        # Form should not submit, still on /checkout
        assert page.url.endswith("/checkout")

# Screenshot on failure utility
def pytest_exception_interact(node, call, report):
    if report.failed:
        page = node.funcargs.get('page')
        if page:
            screenshot_path = f"screenshots/{node.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
            page.screenshot(path=screenshot_path)
            print(f"Screenshot saved to {screenshot_path}") 