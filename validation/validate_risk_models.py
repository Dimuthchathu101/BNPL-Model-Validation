# Advanced BNPL Risk Model Validation Script
# This script loads user, transaction, repayment, and income verification data,
# performs advanced risk and compliance checks, and outputs a detailed report.

import json
import os
import argparse
from datetime import datetime, timedelta

# --- File paths and constants ---
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
USERS_FILE = os.path.join(DATA_DIR, 'users.json')
TRANSACTIONS_FILE = os.path.join(DATA_DIR, 'transactions.json')
REPAYMENTS_FILE = os.path.join(DATA_DIR, 'repayments.json')
INCOME_VERIFICATIONS_FILE = os.path.join(DATA_DIR, 'income_verifications.json')

DEFAULT_OVERDUE_DAYS = 60
DEFAULT_CREDIT_LIMIT = 1000.0
MIN_AGE = 18

# --- Data Loaders ---
def load_json(filename):
    """Load JSON data from a file, return empty list if file does not exist."""
    if not os.path.exists(filename):
        return []
    with open(filename, 'r') as f:
        return json.load(f)

def parse_datetime(dt):
    """Parse ISO format string to datetime object."""
    if isinstance(dt, str):
        return datetime.fromisoformat(dt)
    return dt

# Load all data files
users = load_json(USERS_FILE)
transactions = load_json(TRANSACTIONS_FILE)
repayments = load_json(REPAYMENTS_FILE)
income_verifications = load_json(INCOME_VERIFICATIONS_FILE)

# --- Helper Functions ---
def get_user_transactions(name):
    """Return all transactions for a given user."""
    return [t for t in transactions if t['user'] == name]

def get_user_repayments(name):
    """Return all repayments for a given user."""
    return [r for r in repayments if r['user'] == name]

def get_income_verification_status(name):
    """Return the latest income verification status for a user."""
    for v in reversed(income_verifications):
        if v['user'] == name:
            return v['status']
    return 'Not Verified'

def calculate_utilization(user):
    """Calculate credit utilization and outstanding balance for a user."""
    credit_limit = user.get('credit_limit', DEFAULT_CREDIT_LIMIT)
    total_purchases = sum(t['amount'] for t in get_user_transactions(user['name']))
    total_repaid = sum(r['amount'] for r in get_user_repayments(user['name']))
    outstanding = total_purchases - total_repaid
    utilization = outstanding / credit_limit if credit_limit else 0.0
    return max(0.0, min(utilization, 1.0)), outstanding

def is_user_in_default(user):
    """Determine if a user is in default (any purchase unpaid for 60+ days)."""
    user_tx = sorted(get_user_transactions(user['name']), key=lambda t: parse_datetime(t['timestamp']))
    user_rp = sorted(get_user_repayments(user['name']), key=lambda r: parse_datetime(r['timestamp']))
    repayments_by_time = user_rp.copy()
    outstanding = 0.0
    for tx in user_tx:
        outstanding += tx['amount']
        # Apply repayments in order
        while repayments_by_time and outstanding > 0:
            rp = repayments_by_time[0]
            if rp['amount'] <= outstanding:
                outstanding -= rp['amount']
                repayments_by_time.pop(0)
            else:
                rp['amount'] -= outstanding
                outstanding = 0
        # If outstanding for this tx > 0 and 60+ days old, default
        if outstanding > 0 and (datetime.now() - parse_datetime(tx['timestamp'])).days >= DEFAULT_OVERDUE_DAYS:
            return True
    return False

def calculate_risk_scores(user):
    """Calculate champion and challenger risk scores for a user."""
    utilization, _ = calculate_utilization(user)
    overdue = is_user_in_default(user)
    income_status = get_income_verification_status(user['name'])
    velocity = len([t for t in get_user_transactions(user['name']) if (datetime.now() - parse_datetime(t['timestamp'])).days < 30])
    champion = 100 - 50*utilization - (30 if overdue else 0) - (10 if income_status != 'Verified' else 0)
    challenger = 100 - 40*utilization - (40 if overdue else 0) - (10 if income_status != 'Verified' else 0) - (10 if velocity > 5 else 0)
    return {'champion': round(champion, 2), 'challenger': round(challenger, 2)}

def check_compliance(user):
    """Check compliance for age and income verification requirements."""
    age = (datetime.now() - datetime.strptime(user['dob'], '%Y-%m-%d')).days // 365
    if age < MIN_AGE:
        return 'Underage'
    if get_income_verification_status(user['name']) != 'Verified':
        for t in get_user_transactions(user['name']):
            if t['amount'] > 500:
                return 'Income Not Verified for Large Purchase'
    return 'Compliant'

# --- Custom Checks ---
# (Each function below implements a specific risk or compliance check)
def check_velocity(user, user_result):
    """Warn if user has >10 transactions in 7 days (high velocity)."""
    txs_7d = [t for t in get_user_transactions(user['name']) if (datetime.now() - parse_datetime(t['timestamp'])).days < 7]
    if len(txs_7d) > 10:
        user_result['warnings'].append(f"High transaction velocity: {len(txs_7d)} in 7 days")

def check_inactive(user, user_result):
    """Warn if user has no transactions in last 90 days (inactive)."""
    txs_90d = [t for t in get_user_transactions(user['name']) if (datetime.now() - parse_datetime(t['timestamp'])).days < 90]
    if not txs_90d:
        user_result['warnings'].append("Inactive user: no transactions in last 90 days")

def check_credit_limit(user, user_result):
    """Flag users with non-positive credit limit."""
    if user.get('credit_limit', DEFAULT_CREDIT_LIMIT) <= 0:
        user_result['issues'].append(f"Non-positive credit limit: {user.get('credit_limit')}")

def check_suspicious_repayments(user, user_result):
    """Flag repayments with zero or negative amount."""
    for r in get_user_repayments(user['name']):
        if r['amount'] <= 0:
            user_result['issues'].append(f"Suspicious repayment: {r['amount']} on {r['timestamp']}")

def check_multiple_large_purchases(user, user_result):
    """Flag multiple large purchases without income verification."""
    large_purchases = [t for t in get_user_transactions(user['name']) if t['amount'] > 500]
    if len(large_purchases) > 1 and get_income_verification_status(user['name']) != 'Verified':
        user_result['issues'].append(f"Multiple large purchases without income verification: {len(large_purchases)}")

def check_future_dated(user, user_result):
    """Flag future-dated transactions or repayments."""
    now = datetime.now()
    for t in get_user_transactions(user['name']):
        if parse_datetime(t['timestamp']) > now:
            user_result['issues'].append(f"Future-dated transaction: {t['timestamp']}")
    for r in get_user_repayments(user['name']):
        if parse_datetime(r['timestamp']) > now:
            user_result['issues'].append(f"Future-dated repayment: {r['timestamp']}")

def check_high_utilization(user, user_result):
    """Warn if credit utilization exceeds 80%."""
    util, _ = calculate_utilization(user)
    if util > 0.8:
        user_result['warnings'].append(f"High utilization: {util:.2f}")

def check_low_risk_score(user, user_result):
    """Flag risk scores below 30."""
    scores = calculate_risk_scores(user)
    for model, score in scores.items():
        if score < 30:
            user_result['issues'].append(f"Low risk score in {model}: {score}")

def check_repayment_before_purchase(user, user_result):
    """Detect repayments made before first purchase."""
    tx_times = [parse_datetime(t['timestamp']) for t in get_user_transactions(user['name'])]
    if not tx_times:
        return
    first_tx = min(tx_times)
    for r in get_user_repayments(user['name']):
        r_time = parse_datetime(r['timestamp'])
        if r_time < first_tx:
            user_result['issues'].append(f"Repayment before first purchase: {r['timestamp']}")

def check_duplicate_transactions(user, user_result):
    """Identify duplicate transactions (same amount + timestamp)."""
    seen = {}
    for t in get_user_transactions(user['name']):
        key = (t['amount'], t['timestamp'])
        if key in seen:
            seen[key].append(t)
        else:
            seen[key] = [t]
    for key, txs in seen.items():
        if len(txs) > 1:
            user_result['issues'].append(f"Duplicate transactions: amount {key[0]} at {key[1]} ({len(txs)} times)")

def check_high_relative_transaction(user, user_result):
    """Flag large purchases relative to credit limit without income verification."""
    credit_limit = user.get('credit_limit', DEFAULT_CREDIT_LIMIT)
    income_status = get_income_verification_status(user['name'])
    for t in get_user_transactions(user['name']):
        if t['amount'] > 0.9 * credit_limit and income_status != 'Verified':
            user_result['issues'].append(
                f"High relative transaction ({t['amount']} > 90% of {credit_limit}) without income verification"
            )

def check_large_purchase_verification(user, user_result):
    """Check both absolute ($500) and relative (90% of limit) large purchases."""
    credit_limit = user.get('credit_limit', DEFAULT_CREDIT_LIMIT)
    income_status = get_income_verification_status(user['name'])
    for t in get_user_transactions(user['name']):
        if (t['amount'] > 500 or t['amount'] > 0.9 * credit_limit) and income_status != 'Verified':
            user_result['issues'].append(f"Large purchase without income verification: {t['amount']}")

# --- Main Validation Logic ---
# ALL_CHECKS maps check names to their functions for modular CLI selection
ALL_CHECKS = {
    'utilization': lambda u, r: r['issues'].append(f"Utilization out of bounds: {calculate_utilization(u)[0]:.2f}") if not (0 <= calculate_utilization(u)[0] <= 1.0) else None,
    'outstanding': lambda u, r: r['issues'].append(f"Outstanding negative balance: {calculate_utilization(u)[1]:.2f}") if calculate_utilization(u)[1] < 0 else None,
    'risk_scores': lambda u, r: [r['issues'].append(f"Risk score {k} out of bounds: {v}") for k, v in calculate_risk_scores(u).items() if not (0 <= v <= 100)],
    'default_score': lambda u, r: r['warnings'].append(f"User in default but champion score high: {calculate_risk_scores(u)['champion']}") if is_user_in_default(u) and calculate_risk_scores(u)['champion'] > 70 else None,
    'compliance': lambda u, r: r['issues'].append(f"Non-compliance: {check_compliance(u)}") if check_compliance(u) != 'Compliant' else None,
    'over_repayment': lambda u, r: r['issues'].append(f"Over-repayment: repaid {sum(rp['amount'] for rp in get_user_repayments(u['name']))}, purchased {sum(t['amount'] for t in get_user_transactions(u['name']))}") if sum(rp['amount'] for rp in get_user_repayments(u['name'])) > sum(t['amount'] for t in get_user_transactions(u['name'])) else None,
    'large_purchase_verification': check_large_purchase_verification,
    'velocity': check_velocity,
    'inactive': check_inactive,
    'credit_limit': check_credit_limit,
    'suspicious_repayments': check_suspicious_repayments,
    'multiple_large_purchases': check_multiple_large_purchases,
    'future_dated': check_future_dated,
    'high_utilization': check_high_utilization,
    'low_risk_score': check_low_risk_score,
    'repayment_before_purchase': check_repayment_before_purchase,
    'duplicate_transactions': check_duplicate_transactions,
    'high_relative_transaction': check_high_relative_transaction,
}

# --- CLI Argument Parsing ---
parser = argparse.ArgumentParser(description="Advanced BNPL Risk Model Validation")
parser.add_argument('--checks', type=str, default=','.join(ALL_CHECKS.keys()), help='Comma-separated list of checks to run')
parser.add_argument('--output', type=str, default='risk_validation_report.json', help='Output file name (json or csv)')
parser.add_argument('--summary-only', action='store_true', help='Print only summary to console')
parser.add_argument('--user', type=str, default=None, help='Validate only a specific user (by name)')
args = parser.parse_args()

selected_checks = [c.strip() for c in args.checks.split(',') if c.strip() in ALL_CHECKS]
output_path = os.path.join(os.path.dirname(__file__), args.output)

# --- Run Validations ---
results = []
users_to_check = [u for u in users if (args.user is None or u['name'] == args.user)]
for user in users_to_check:
    user_result = {'name': user['name'], 'issues': [], 'warnings': [], 'scores': {}, 'compliance': None}
    # Run all selected checks
    for check in selected_checks:
        ALL_CHECKS[check](user, user_result)
    user_result['scores'] = calculate_risk_scores(user)
    user_result['compliance'] = check_compliance(user)
    results.append(user_result)

# --- Output Results ---
summary = {
    'total_users': len(users_to_check),
    'users_with_issues': sum(1 for r in results if r['issues']),
    'users_with_warnings': sum(1 for r in results if r['warnings']),
    'issues': sum(len(r['issues']) for r in results),
    'warnings': sum(len(r['warnings']) for r in results),
}

# Print results to console
if not args.summary_only:
    print("\n=== RISK MODEL VALIDATION REPORT ===")
    print(f"Total users: {summary['total_users']}")
    print(f"Users with issues: {summary['users_with_issues']}")
    print(f"Users with warnings: {summary['users_with_warnings']}")
    print(f"Total issues: {summary['issues']}")
    print(f"Total warnings: {summary['warnings']}")
    for r in results:
        if r['issues'] or r['warnings']:
            print(f"\nUser: {r['name']}")
            for i in r['issues']:
                print(f"  ISSUE: {i}")
            for w in r['warnings']:
                print(f"  WARNING: {w}")
            print(f"  Scores: {r['scores']}")
            print(f"  Compliance: {r['compliance']}")
else:
    print("\n=== RISK MODEL VALIDATION SUMMARY ===")
    print(f"Total users: {summary['total_users']}")
    print(f"Users with issues: {summary['users_with_issues']}")
    print(f"Users with warnings: {summary['users_with_warnings']}")
    print(f"Total issues: {summary['issues']}")
    print(f"Total warnings: {summary['warnings']}")

# Save results to file (JSON or CSV)
if args.output.endswith('.json'):
    with open(output_path, 'w') as f:
        json.dump({'summary': summary, 'results': results}, f, indent=2, default=str)
    print(f"\nDetailed report saved to {output_path}")
elif args.output.endswith('.csv'):
    import csv
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['name', 'issues', 'warnings', 'scores', 'compliance'])
        for r in results:
            writer.writerow([r['name'], '; '.join(r['issues']), '; '.join(r['warnings']), json.dumps(r['scores']), r['compliance']])
    print(f"\nDetailed report saved to {output_path}") 