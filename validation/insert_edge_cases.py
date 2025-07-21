# Edge Case Data Inserter for BNPL Risk Model Validation
# This script adds a variety of edge case users and transactions to the data files
# to test the robustness of the risk model validation logic.

import json
import os
from datetime import datetime, timedelta

# --- File paths ---
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
USERS_FILE = os.path.join(DATA_DIR, 'users.json')
TRANSACTIONS_FILE = os.path.join(DATA_DIR, 'transactions.json')
REPAYMENTS_FILE = os.path.join(DATA_DIR, 'repayments.json')
INCOME_VERIFICATIONS_FILE = os.path.join(DATA_DIR, 'income_verifications.json')

now = datetime.now()

# --- Load data files ---
with open(USERS_FILE) as f:
    users = json.load(f)
with open(TRANSACTIONS_FILE) as f:
    transactions = json.load(f)
with open(REPAYMENTS_FILE) as f:
    repayments = json.load(f)
with open(INCOME_VERIFICATIONS_FILE) as f:
    income_verifications = json.load(f)

# --- Helper functions to add data ---
def add_user(user):
    """Add a user to the users list."""
    users.append(user)

def add_transaction(tx):
    """Add a transaction to the transactions list."""
    transactions.append(tx)

def add_repayment(rp):
    """Add a repayment to the repayments list."""
    repayments.append(rp)

def add_income_verification(iv):
    """Add an income verification record to the list."""
    income_verifications.append(iv)

# --- Edge Case Insertions ---
# 1. Active user with recent transactions
active_user = {
    'name': 'ActiveUser',
    'dob': '1995-01-01',
    'registered': now.isoformat(),
    'credit_limit': 2000.0
}
add_user(active_user)
add_transaction({'user': 'ActiveUser', 'amount': 150.0, 'timestamp': (now - timedelta(days=2)).isoformat()})
add_transaction({'user': 'ActiveUser', 'amount': 200.0, 'timestamp': (now - timedelta(days=1)).isoformat()})
add_repayment({'user': 'ActiveUser', 'amount': 100.0, 'timestamp': (now - timedelta(days=1)).isoformat()})
add_income_verification({'user': 'ActiveUser', 'status': 'Verified', 'timestamp': (now - timedelta(days=1)).isoformat()})

# 2. High utilization (outstanding close to credit limit)
high_util_user = {
    'name': 'HighUtilUser',
    'dob': '1990-05-05',
    'registered': now.isoformat(),
    'credit_limit': 1000.0
}
add_user(high_util_user)
add_transaction({'user': 'HighUtilUser', 'amount': 950.0, 'timestamp': (now - timedelta(days=5)).isoformat()})
add_repayment({'user': 'HighUtilUser', 'amount': 50.0, 'timestamp': (now - timedelta(days=4)).isoformat()})
add_income_verification({'user': 'HighUtilUser', 'status': 'Not Verified', 'timestamp': (now - timedelta(days=4)).isoformat()})

# 3. Low risk score (default, high utilization, no income verification)
low_risk_user = {
    'name': 'LowRiskUser',
    'dob': '1985-07-07',
    'registered': now.isoformat(),
    'credit_limit': 1000.0
}
add_user(low_risk_user)
add_transaction({'user': 'LowRiskUser', 'amount': 800.0, 'timestamp': (now - timedelta(days=70)).isoformat()})
add_income_verification({'user': 'LowRiskUser', 'status': 'Not Verified', 'timestamp': (now - timedelta(days=70)).isoformat()})
# No repayment, so default

# 4. Repayment before purchase
rep_before_purchase_user = {
    'name': 'RepBeforePurchase',
    'dob': '1992-03-03',
    'registered': now.isoformat(),
    'credit_limit': 1000.0
}
add_user(rep_before_purchase_user)
add_repayment({'user': 'RepBeforePurchase', 'amount': 100.0, 'timestamp': (now - timedelta(days=10)).isoformat()})
add_transaction({'user': 'RepBeforePurchase', 'amount': 100.0, 'timestamp': (now - timedelta(days=5)).isoformat()})
add_income_verification({'user': 'RepBeforePurchase', 'status': 'Verified', 'timestamp': (now - timedelta(days=5)).isoformat()})

# 5. Duplicate transactions
dup_tx_user = {
    'name': 'DupTxUser',
    'dob': '1993-04-04',
    'registered': now.isoformat(),
    'credit_limit': 1000.0
}
add_user(dup_tx_user)
dup_time = (now - timedelta(days=3)).isoformat()
add_transaction({'user': 'DupTxUser', 'amount': 300.0, 'timestamp': dup_time})
add_transaction({'user': 'DupTxUser', 'amount': 300.0, 'timestamp': dup_time})
add_income_verification({'user': 'DupTxUser', 'status': 'Verified', 'timestamp': dup_time})

# 6. Large purchase without income verification
large_no_verif_user = {
    'name': 'LargeNoVerif',
    'dob': '1994-06-06',
    'registered': now.isoformat(),
    'credit_limit': 1000.0
}
add_user(large_no_verif_user)
add_transaction({'user': 'LargeNoVerif', 'amount': 950.0, 'timestamp': (now - timedelta(days=2)).isoformat()})
# No income verification

# 7. Negative transaction amount (refund or error)
neg_tx_user = {
    'name': 'NegTxUser',
    'dob': '1991-08-08',
    'registered': now.isoformat(),
    'credit_limit': 1000.0
}
add_user(neg_tx_user)
add_transaction({'user': 'NegTxUser', 'amount': -100.0, 'timestamp': (now - timedelta(days=2)).isoformat()})
add_income_verification({'user': 'NegTxUser', 'status': 'Verified', 'timestamp': (now - timedelta(days=2)).isoformat()})

# 8. Over-repayment (repayments > purchases)
overpay_user = {
    'name': 'OverpayUser',
    'dob': '1988-09-09',
    'registered': now.isoformat(),
    'credit_limit': 1000.0
}
add_user(overpay_user)
add_transaction({'user': 'OverpayUser', 'amount': 200.0, 'timestamp': (now - timedelta(days=10)).isoformat()})
add_repayment({'user': 'OverpayUser', 'amount': 300.0, 'timestamp': (now - timedelta(days=9)).isoformat()})
add_income_verification({'user': 'OverpayUser', 'status': 'Verified', 'timestamp': (now - timedelta(days=9)).isoformat()})

# 9. Future-dated transaction
future_tx_user = {
    'name': 'FutureTxUser',
    'dob': '1997-10-10',
    'registered': now.isoformat(),
    'credit_limit': 1000.0
}
add_user(future_tx_user)
add_transaction({'user': 'FutureTxUser', 'amount': 100.0, 'timestamp': (now + timedelta(days=5)).isoformat()})
add_income_verification({'user': 'FutureTxUser', 'status': 'Verified', 'timestamp': now.isoformat()})

# 10. Zero credit limit
zero_limit_user = {
    'name': 'ZeroLimitUser',
    'dob': '1996-11-11',
    'registered': now.isoformat(),
    'credit_limit': 0.0
}
add_user(zero_limit_user)
add_transaction({'user': 'ZeroLimitUser', 'amount': 50.0, 'timestamp': (now - timedelta(days=2)).isoformat()})
add_income_verification({'user': 'ZeroLimitUser', 'status': 'Verified', 'timestamp': (now - timedelta(days=2)).isoformat()})

# 11. Multiple large purchases, only one verified
multi_large_user = {
    'name': 'MultiLargeUser',
    'dob': '1987-12-12',
    'registered': now.isoformat(),
    'credit_limit': 1000.0
}
add_user(multi_large_user)
add_transaction({'user': 'MultiLargeUser', 'amount': 600.0, 'timestamp': (now - timedelta(days=20)).isoformat()})
add_income_verification({'user': 'MultiLargeUser', 'status': 'Verified', 'timestamp': (now - timedelta(days=19)).isoformat()})
add_transaction({'user': 'MultiLargeUser', 'amount': 650.0, 'timestamp': (now - timedelta(days=5)).isoformat()})
# No new verification for second large purchase

# 12. Suspicious repayment (zero or negative)
suspicious_rp_user = {
    'name': 'SuspiciousRpUser',
    'dob': '1998-01-13',
    'registered': now.isoformat(),
    'credit_limit': 1000.0
}
add_user(suspicious_rp_user)
add_transaction({'user': 'SuspiciousRpUser', 'amount': 100.0, 'timestamp': (now - timedelta(days=3)).isoformat()})
add_repayment({'user': 'SuspiciousRpUser', 'amount': 0.0, 'timestamp': (now - timedelta(days=2)).isoformat()})
add_repayment({'user': 'SuspiciousRpUser', 'amount': -50.0, 'timestamp': (now - timedelta(days=1)).isoformat()})
add_income_verification({'user': 'SuspiciousRpUser', 'status': 'Verified', 'timestamp': (now - timedelta(days=3)).isoformat()})

# 13. All transactions on the same day (high velocity)
same_day_user = {
    'name': 'SameDayUser',
    'dob': '1999-02-14',
    'registered': now.isoformat(),
    'credit_limit': 1000.0
}
add_user(same_day_user)
same_day = (now - timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
for i in range(12):
    add_transaction({'user': 'SameDayUser', 'amount': 50.0, 'timestamp': (same_day + timedelta(minutes=i)).isoformat()})
add_income_verification({'user': 'SameDayUser', 'status': 'Verified', 'timestamp': same_day.isoformat()})

# 14. Underage user
young_user = {
    'name': 'UnderageUser',
    'dob': (now - timedelta(days=365*15)).strftime('%Y-%m-%d'),  # 15 years old
    'registered': now.isoformat(),
    'credit_limit': 1000.0
}
add_user(young_user)
add_transaction({'user': 'UnderageUser', 'amount': 100.0, 'timestamp': (now - timedelta(days=2)).isoformat()})
add_income_verification({'user': 'UnderageUser', 'status': 'Verified', 'timestamp': (now - timedelta(days=2)).isoformat()})

# --- Save all data files ---
with open(USERS_FILE, 'w') as f:
    json.dump(users, f, indent=2, default=str)
with open(TRANSACTIONS_FILE, 'w') as f:
    json.dump(transactions, f, indent=2, default=str)
with open(REPAYMENTS_FILE, 'w') as f:
    json.dump(repayments, f, indent=2, default=str)
with open(INCOME_VERIFICATIONS_FILE, 'w') as f:
    json.dump(income_verifications, f, indent=2, default=str)

print("Edge case users and transactions inserted.") 