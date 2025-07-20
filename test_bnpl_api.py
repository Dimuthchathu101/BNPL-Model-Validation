import requests
import json

BASE_URL = 'http://localhost:5000'
API_KEY = 'demo-api-key-123'
HEADERS = {'X-API-KEY': API_KEY}


def print_result(title, resp):
    print(f'\n=== {title} ===')
    print(f'Status: {resp.status_code}')
    try:
        print(json.dumps(resp.json(), indent=2))
    except Exception:
        print(resp.text)

# 1. Get products
r = requests.get(f'{BASE_URL}/api/products', headers=HEADERS)
print_result('GET /api/products', r)

# 2. Get users
r = requests.get(f'{BASE_URL}/api/users', headers=HEADERS)
print_result('GET /api/users', r)

# 3. Get providers
r = requests.get(f'{BASE_URL}/api/providers', headers=HEADERS)
print_result('GET /api/providers', r)

# 4. Get transactions (with filter)
r = requests.get(f'{BASE_URL}/api/transactions?user=User1', headers=HEADERS)
print_result('GET /api/transactions?user=User1', r)

# 5. Get repayments
r = requests.get(f'{BASE_URL}/api/repayments?user=User1', headers=HEADERS)
print_result('GET /api/repayments?user=User1', r)

# 6. KYC check
r = requests.post(f'{BASE_URL}/api/kyc-check', headers=HEADERS, json={'amount': 200})
print_result('POST /api/kyc-check', r)

# 7. Simulate checkout
checkout_payload = {
    'user': 'User1',
    'product': 'Wireless Headphones',
    'provider': 'Klarna',
    'region': 'US',
    'consent': True,
    'amount': 100
}
r = requests.post(f'{BASE_URL}/api/checkout', headers=HEADERS, json=checkout_payload)
print_result('POST /api/checkout', r)

# 8. Virtual card
r = requests.post(f'{BASE_URL}/api/virtual-card', headers=HEADERS)
print_result('POST /api/virtual-card', r)

# 9. AI underwriting
r = requests.post(f'{BASE_URL}/api/underwriting', headers=HEADERS, json={'utilization': 0.3, 'region': 'US', 'income_verified': True})
print_result('POST /api/underwriting', r)

# 10. Subscription
r = requests.post(f'{BASE_URL}/api/subscription', headers=HEADERS, json={'user': 'User1', 'product': 'Smart Watch', 'amount': 50, 'interval': 'monthly'})
print_result('POST /api/subscription', r)

# 11. Audit log
r = requests.get(f'{BASE_URL}/api/audit-log', headers=HEADERS)
print_result('GET /api/audit-log', r)

# 12. Download transactions CSV
r = requests.get(f'{BASE_URL}/api/transactions.csv', headers=HEADERS)
print(f'\n=== GET /api/transactions.csv ===')
print(f'Status: {r.status_code}, Content-Type: {r.headers.get("Content-Type")}, Bytes: {len(r.content)}')

# 13. Download audit log CSV
r = requests.get(f'{BASE_URL}/api/audit-log.csv', headers=HEADERS)
print(f'\n=== GET /api/audit-log.csv ===')
print(f'Status: {r.status_code}, Content-Type: {r.headers.get("Content-Type")}, Bytes: {len(r.content)}') 