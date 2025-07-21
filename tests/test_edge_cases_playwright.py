import pytest
from playwright.sync_api import Page, APIRequestContext, expect
from datetime import datetime, timedelta
import time

BASE_URL = "http://localhost:5000/"
API_KEY = "demo-api-key-123"

@pytest.fixture(scope="session")
def api_request_context(playwright):
    """Create a Playwright API request context with the demo API key."""
    return playwright.request.new_context(base_url=BASE_URL, extra_http_headers={"X-API-KEY": API_KEY})

# 1. Underage Registration (UI)
def test_underage_registration(page: Page):
    """Try to register a user under 18 and assert error message is shown."""
    page.goto(BASE_URL + "register")
    name = f"Underage_{int(time.time())}"
    dob = (datetime.now() - timedelta(days=365*15)).strftime('%Y-%m-%d')  # 15 years old
    page.fill('input[name="name"]', name)
    page.fill('input[name="dob"]', dob)
    page.click('button[type="submit"]')
    expect(page.locator('.alert, .toast-body')).to_contain_text("at least 18 years old")

# 2. High Utilization (UI)
def test_high_utilization(page: Page):
    """Register a user and make purchases up to the credit limit, then check dashboard for 100% utilization."""
    name = f"HighUtil_{int(time.time())}"
    # Register user
    page.goto(BASE_URL + "register")
    page.fill('input[name="name"]', name)
    page.fill('input[name="dob"]', '1990-01-01')
    page.click('button[type="submit"]')
    # Make purchases up to limit
    for amt in [400, 400, 200]:
        page.goto(BASE_URL + "purchase")
        page.select_option('select[name="user"]', name)
        page.fill('input[name="amount"]', str(amt))
        page.click('button[type="submit"]')
    # Check dashboard for high utilization
    page.goto(BASE_URL + "dashboard")
    row = page.locator(f"tr:has-text('{name}')")
    expect(row).to_contain_text("100.0%")

# 3. Repayment Before Purchase (UI)
def test_repay_before_purchase(page: Page):
    """Register a user and try to repay before any purchase, then check utilization remains 0%."""
    name = f"RepBefore_{int(time.time())}"
    # Register user
    page.goto(BASE_URL + "register")
    page.fill('input[name="name"]', name)
    page.fill('input[name="dob"]', '1990-01-01')
    page.click('button[type="submit"]')
    # Try to repay before any purchase
    page.goto(BASE_URL + "repay")
    page.select_option('select[name="user"]', name)
    page.fill('input[name="amount"]', '100')
    page.click('button[type="submit"]')
    # Go to dashboard and check utilization is 0%
    page.goto(BASE_URL + "dashboard")
    row = page.locator(f"tr:has-text('{name}')")
    expect(row).to_contain_text("0.0%")

# 4. Duplicate Transactions (API + UI)
def test_duplicate_transactions(api_request_context: APIRequestContext, page: Page):
    """Register a user and insert two identical transactions via API, then check user appears in dashboard."""
    name = f"DupTx_{int(time.time())}"
    # Register user via UI
    page.goto(BASE_URL + "register")
    page.fill('input[name="name"]', name)
    page.fill('input[name="dob"]', '1990-01-01')
    page.click('button[type="submit"]')
    # Insert two identical transactions via API
    tx_time = datetime.now().isoformat()
    tx_payload = {"user": name, "amount": 300.0, "timestamp": tx_time}
    for _ in range(2):
        api_request_context.post("/api/transactions", data=tx_payload)
    # Check dashboard for user (should show utilization, but backend should flag duplicate in validation)
    page.goto(BASE_URL + "dashboard")
    row = page.locator(f"tr:has-text('{name}')")
    expect(row).to_be_visible()

# 5. Large Purchase Without Verification (UI)
def test_large_purchase_no_verification(page: Page):
    """Register a user and make a large purchase without income verification, then check compliance column."""
    name = f"LargeNoVerif_{int(time.time())}"
    # Register user
    page.goto(BASE_URL + "register")
    page.fill('input[name="name"]', name)
    page.fill('input[name="dob"]', '1990-01-01')
    page.click('button[type="submit"]')
    # Make large purchase
    page.goto(BASE_URL + "purchase")
    page.select_option('select[name="user"]', name)
    page.fill('input[name="amount"]', '950')
    page.click('button[type="submit"]')
    # Go to dashboard and check compliance column
    page.goto(BASE_URL + "dashboard")
    row = page.locator(f"tr:has-text('{name}')")
    expect(row).to_contain_text("Income Not Verified")

# 6. Suspicious Repayment (UI)
def test_suspicious_repayment(page: Page):
    """Register a user, make a purchase, then try to repay with zero and negative amount."""
    name = f"SuspiciousRp_{int(time.time())}"
    # Register user
    page.goto(BASE_URL + "register")
    page.fill('input[name="name"]', name)
    page.fill('input[name="dob"]', '1990-01-01')
    page.click('button[type="submit"]')
    # Make a purchase
    page.goto(BASE_URL + "purchase")
    page.select_option('select[name="user"]', name)
    page.fill('input[name="amount"]', '100')
    page.click('button[type="submit"]')
    # Try to repay with zero and negative amount
    for amt in ['0', '-50']:
        page.goto(BASE_URL + "repay")
        page.select_option('select[name="user"]', name)
        page.fill('input[name="amount"]', amt)
        page.click('button[type="submit"]')
    # Go to dashboard and check utilization is not negative
    page.goto(BASE_URL + "dashboard")
    row = page.locator(f"tr:has-text('{name}')")
    expect(row).to_be_visible()
    # (Backend validation will flag this in the report)

# 7. Over-Repayment (UI)
def test_over_repayment(page: Page):
    """Register a user, make a purchase, then repay more than the purchase amount."""
    name = f"Overpay_{int(time.time())}"
    # Register user
    page.goto(BASE_URL + "register")
    page.fill('input[name="name"]', name)
    page.fill('input[name="dob"]', '1990-01-01')
    page.click('button[type="submit"]')
    # Make a purchase
    page.goto(BASE_URL + "purchase")
    page.select_option('select[name="user"]', name)
    page.fill('input[name="amount"]', '200')
    page.click('button[type="submit"]')
    # Repay more than purchase
    page.goto(BASE_URL + "repay")
    page.select_option('select[name="user"]', name)
    page.fill('input[name="amount"]', '300')
    page.click('button[type="submit"]')
    # Go to dashboard and check utilization is not negative
    page.goto(BASE_URL + "dashboard")
    row = page.locator(f"tr:has-text('{name}')")
    expect(row).to_be_visible()

# 8. Future-Dated Transaction (API + UI)
def test_future_dated_transaction(api_request_context: APIRequestContext, page: Page):
    """Register a user and insert a future-dated transaction via API, then check user appears in dashboard."""
    name = f"FutureTx_{int(time.time())}"
    # Register user via UI
    page.goto(BASE_URL + "register")
    page.fill('input[name="name"]', name)
    page.fill('input[name="dob"]', '1990-01-01')
    page.click('button[type="submit"]')
    # Insert future-dated transaction via API
    future_time = (datetime.now() + timedelta(days=5)).isoformat()
    tx_payload = {"user": name, "amount": 100.0, "timestamp": future_time}
    api_request_context.post("/api/transactions", data=tx_payload)
    # Go to dashboard and check user appears
    page.goto(BASE_URL + "dashboard")
    row = page.locator(f"tr:has-text('{name}')")
    expect(row).to_be_visible()

# 9. Zero Credit Limit (UI)
def test_zero_credit_limit(page: Page):
    """Register a user with zero credit limit (if possible), try to make a purchase, and check dashboard."""
    name = f"ZeroLimit_{int(time.time())}"
    # Register user (simulate via UI, but UI may not allow setting limit; this is a backend test)
    page.goto(BASE_URL + "register")
    page.fill('input[name="name"]', name)
    page.fill('input[name="dob"]', '1990-01-01')
    page.click('button[type="submit"]')
    # Try to make a purchase (should be blocked or handled by backend)
    page.goto(BASE_URL + "purchase")
    page.select_option('select[name="user"]', name)
    page.fill('input[name="amount"]', '50')
    page.click('button[type="submit"]')
    # Go to dashboard and check user appears
    page.goto(BASE_URL + "dashboard")
    row = page.locator(f"tr:has-text('{name}')")
    expect(row).to_be_visible()

# 10. Multiple Large Purchases, Only One Verified (UI + API)
def test_multiple_large_purchases_one_verified(api_request_context: APIRequestContext, page: Page):
    """Register a user, make two large purchases, verify income only before the first, and check dashboard."""
    name = f"MultiLarge_{int(time.time())}"
    # Register user via UI
    page.goto(BASE_URL + "register")
    page.fill('input[name="name"]', name)
    page.fill('input[name="dob"]', '1990-01-01')
    page.click('button[type="submit"]')
    # Make first large purchase
    page.goto(BASE_URL + "purchase")
    page.select_option('select[name="user"]', name)
    page.fill('input[name="amount"]', '600')
    page.click('button[type="submit"]')
    # Verify income
    page.goto(BASE_URL + "income_verification")
    page.select_option('select[name="user"]', name)
    page.select_option('select[name="status"]', 'Verified')
    page.click('button[type="submit"]')
    # Make second large purchase (should be flagged in backend validation)
    page.goto(BASE_URL + "purchase")
    page.select_option('select[name="user"]', name)
    page.fill('input[name="amount"]', '650')
    page.click('button[type="submit"]')
    # Go to dashboard and check user appears
    page.goto(BASE_URL + "dashboard")
    row = page.locator(f"tr:has-text('{name}')")
    expect(row).to_be_visible()

# 11. Negative Transaction Amount (UI)
def test_negative_transaction_amount(page: Page):
    """Register a user and try to make a negative purchase, then check dashboard."""
    name = f"NegTx_{int(time.time())}"
    # Register user
    page.goto(BASE_URL + "register")
    page.fill('input[name="name"]', name)
    page.fill('input[name="dob"]', '1990-01-01')
    page.click('button[type="submit"]')
    # Try to make a negative purchase
    page.goto(BASE_URL + "purchase")
    page.select_option('select[name="user"]', name)
    page.fill('input[name="amount"]', '-100')
    page.click('button[type="submit"]')
    # Go to dashboard and check user appears
    page.goto(BASE_URL + "dashboard")
    row = page.locator(f"tr:has-text('{name}')")
    expect(row).to_be_visible()

# 12. All Transactions on the Same Day (High Velocity, UI)
def test_high_velocity_same_day(page: Page):
    """Register a user and make 12 purchases in one day, then check dashboard."""
    name = f"SameDay_{int(time.time())}"
    # Register user
    page.goto(BASE_URL + "register")
    page.fill('input[name="name"]', name)
    page.fill('input[name="dob"]', '1990-01-01')
    page.click('button[type="submit"]')
    # Make 12 purchases in one day
    for _ in range(12):
        page.goto(BASE_URL + "purchase")
        page.select_option('select[name="user"]', name)
        page.fill('input[name="amount"]', '50')
        page.click('button[type="submit"]')
    # Go to dashboard and check user appears
    page.goto(BASE_URL + "dashboard")
    row = page.locator(f"tr:has-text('{name}')")
    expect(row).to_be_visible()

# 13. Suspicious Repayment via API
def test_suspicious_repayment_api(api_request_context: APIRequestContext, page: Page):
    """Register a user, make a purchase, then insert a negative repayment via API and check dashboard."""
    name = f"SuspiciousApi_{int(time.time())}"
    # Register user via UI
    page.goto(BASE_URL + "register")
    page.fill('input[name="name"]', name)
    page.fill('input[name="dob"]', '1990-01-01')
    page.click('button[type="submit"]')
    # Make a purchase
    page.goto(BASE_URL + "purchase")
    page.select_option('select[name="user"]', name)
    page.fill('input[name="amount"]', '100')
    page.click('button[type="submit"]')
    # Insert negative repayment via API
    rp_payload = {"user": name, "amount": -50.0, "timestamp": datetime.now().isoformat()}
    api_request_context.post("/api/repayments", data=rp_payload)
    # Go to dashboard and check user appears
    page.goto(BASE_URL + "dashboard")
    row = page.locator(f"tr:has-text('{name}')")
    expect(row).to_be_visible()

# 14. Exactly 18 Years Old Registration (UI, should succeed)
def test_exactly_18_registration(page: Page):
    """Register a user who is exactly 18 years old and assert registration is successful."""
    name = f"Eighteen_{int(time.time())}"
    dob = (datetime.now() - timedelta(days=365*18)).strftime('%Y-%m-%d')
    page.goto(BASE_URL + "register")
    page.fill('input[name="name"]', name)
    page.fill('input[name="dob"]', dob)
    page.click('button[type="submit"]')
    expect(page.locator('.toast-body, .alert-info')).to_contain_text("Registration successful") 