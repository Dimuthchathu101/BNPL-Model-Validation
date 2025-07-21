from flask import Flask, request, render_template, redirect, url_for, flash, jsonify
from datetime import datetime, timedelta
import json
import os
from collections import Counter, defaultdict
import csv

app = Flask(__name__)
app.secret_key = 'bnpl_secret_key'

DATA_DIR = 'data'
USERS_FILE = os.path.join(DATA_DIR, 'users.json')
TRANSACTIONS_FILE = os.path.join(DATA_DIR, 'transactions.json')
REPAYMENTS_FILE = os.path.join(DATA_DIR, 'repayments.json')
INCOME_VERIFICATIONS_FILE = os.path.join(DATA_DIR, 'income_verifications.json')
AUDIT_LOG_FILE = os.path.join(DATA_DIR, 'audit_log.json')

# --- Data Loaders ---
def load_json(filename):
    """Load JSON data from a file. Returns an empty list if the file does not exist."""
    if not os.path.exists(filename):
        return []
    with open(filename, 'r') as f:
        return json.load(f)

def save_json(filename, data):
    """Save data as JSON to a file, using default=str for datetime serialization."""
    with open(filename, 'w') as f:
        json.dump(data, f, default=str)

# --- User Data Functions ---
def get_all_users():
    """Load all users from the users file, converting registration timestamps to datetime objects."""
    users = load_json(USERS_FILE)
    for u in users:
        if isinstance(u['registered'], str):
            u['registered'] = datetime.fromisoformat(u['registered'])
    return users

def save_all_users(users):
    """Save all users to the users file, converting registration datetimes to ISO format."""
    for u in users:
        if isinstance(u['registered'], datetime):
            u['registered'] = u['registered'].isoformat()
    save_json(USERS_FILE, users)

# --- Transaction Data Functions ---
def get_all_transactions():
    """Load all transactions, converting timestamps to datetime objects."""
    txs = load_json(TRANSACTIONS_FILE)
    for t in txs:
        if isinstance(t['timestamp'], str):
            t['timestamp'] = datetime.fromisoformat(t['timestamp'])
    return txs

def save_all_transactions(transactions):
    """Save all transactions, converting timestamps to ISO format."""
    for t in transactions:
        if isinstance(t['timestamp'], datetime):
            t['timestamp'] = t['timestamp'].isoformat()
    save_json(TRANSACTIONS_FILE, transactions)

# --- Repayment Data Functions ---
def get_all_repayments():
    """Load all repayments, converting timestamps to datetime objects."""
    rps = load_json(REPAYMENTS_FILE)
    for r in rps:
        if isinstance(r['timestamp'], str):
            r['timestamp'] = datetime.fromisoformat(r['timestamp'])
    return rps

def save_all_repayments(repayments):
    """Save all repayments, converting timestamps to ISO format."""
    for r in repayments:
        if isinstance(r['timestamp'], datetime):
            r['timestamp'] = r['timestamp'].isoformat()
    save_json(REPAYMENTS_FILE, repayments)

# --- Income Verification Data Functions ---
def get_all_income_verifications():
    """Load all income verifications, converting timestamps to datetime objects."""
    ivs = load_json(INCOME_VERIFICATIONS_FILE)
    for v in ivs:
        if isinstance(v['timestamp'], str):
            v['timestamp'] = datetime.fromisoformat(v['timestamp'])
    return ivs

def save_all_income_verifications(ivs):
    """Save all income verifications, converting timestamps to ISO format."""
    for v in ivs:
        if isinstance(v['timestamp'], datetime):
            v['timestamp'] = v['timestamp'].isoformat()
    save_json(INCOME_VERIFICATIONS_FILE, ivs)

def load_audit_log():
    """Load the audit log from file."""
    return load_json(AUDIT_LOG_FILE)

def save_audit_log(log):
    """Save the audit log to file."""
    save_json(AUDIT_LOG_FILE, log)

MIN_AGE = 18
DEFAULT_OVERDUE_DAYS = 60
DEFAULT_CREDIT_LIMIT = 1000.0

# --- Helper Functions for Business Logic ---
def get_user(name):
    """Return the user dict for a given name, or None if not found."""
    users = get_all_users()
    for u in users:
        if u['name'] == name:
            return u
    return None

def get_user_transactions(name):
    """Return all transactions for a given user name."""
    transactions = get_all_transactions()
    return [t for t in transactions if t['user'] == name]

def get_user_repayments(name):
    """Return all repayments for a given user name."""
    repayments = get_all_repayments()
    return [r for r in repayments if r['user'] == name]

def get_income_verification_status(name):
    """Return the latest income verification status for a user, or 'Not Verified' if none found."""
    ivs = get_all_income_verifications()
    for v in ivs[::-1]:
        if v['user'] == name:
            return v['status']
    return 'Not Verified'

def calculate_utilization(name):
    """Calculate the credit utilization for a user as outstanding/credit_limit, clamped to [0, 1]."""
    user = get_user(name)
    if not user:
        return 0.0
    credit_limit = user.get('credit_limit', DEFAULT_CREDIT_LIMIT)
    total_purchases = sum(t['amount'] for t in get_user_transactions(name))
    total_repaid = sum(r['amount'] for r in get_user_repayments(name))
    outstanding = total_purchases - total_repaid
    utilization = outstanding / credit_limit if credit_limit else 0.0
    return max(0.0, min(utilization, 1.0))

def calculate_transaction_velocity(name, days=30):
    """Return the number of transactions for a user in the last 'days' days."""
    now = datetime.now()
    recent = [t for t in get_user_transactions(name) if (now - t['timestamp']).days < days]
    return len(recent)

def is_user_in_default(name):
    """Return True if any purchase is unpaid for 60+ days, else False."""
    user_tx = get_user_transactions(name)
    user_rp = get_user_repayments(name)
    repayments_by_time = sorted(user_rp, key=lambda r: r['timestamp'])
    outstanding = 0.0
    for tx in sorted(user_tx, key=lambda t: t['timestamp']):
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
        if outstanding > 0 and (datetime.now() - tx['timestamp']).days >= DEFAULT_OVERDUE_DAYS:
            return True
    return False

def calculate_risk_scores(name):
    """Calculate champion and challenger risk scores for a user based on utilization, overdue, income verification, and velocity."""
    utilization = calculate_utilization(name)
    overdue = is_user_in_default(name)
    income_status = get_income_verification_status(name)
    velocity = calculate_transaction_velocity(name, 30)
    champion = 100 - 50*utilization - (30 if overdue else 0) - (10 if income_status != 'Verified' else 0)
    challenger = 100 - 40*utilization - (40 if overdue else 0) - (10 if income_status != 'Verified' else 0) - (10 if velocity > 5 else 0)
    return {'champion': round(champion, 2), 'challenger': round(challenger, 2)}

def check_compliance(name):
    """Check compliance for a user: age, income verification for large purchases, etc."""
    user = get_user(name)
    if not user:
        return 'Not Registered'
    age = (datetime.now() - datetime.strptime(user['dob'], '%Y-%m-%d')).days // 365
    if age < MIN_AGE:
        return 'Underage'
    if get_income_verification_status(name) != 'Verified':
        for t in get_user_transactions(name):
            if t['amount'] > 500:
                return 'Income Not Verified for Large Purchase'
    return 'Compliant'

# --- API Endpoints ---
@app.route('/api/user/<name>')
def api_user(name):
    user = get_user(name)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    risk_scores = calculate_risk_scores(name)
    utilization = calculate_utilization(name)
    velocity_7 = calculate_transaction_velocity(name, 7)
    velocity_30 = calculate_transaction_velocity(name, 30)
    default_status = is_user_in_default(name)
    compliance = check_compliance(name)
    return jsonify({
        'name': name,
        'risk_scores': risk_scores,
        'utilization': utilization,
        'transaction_velocity_7d': velocity_7,
        'transaction_velocity_30d': velocity_30,
        'default_status': default_status,
        'compliance': compliance
    })

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        dob = request.form['dob']
        age = (datetime.now() - datetime.strptime(dob, '%Y-%m-%d')).days // 365
        if age < MIN_AGE:
            flash('User must be at least 18 years old.')
            return redirect(url_for('register'))
        users = get_all_users()
        users.append({'name': name, 'dob': dob, 'registered': datetime.now().isoformat(), 'credit_limit': DEFAULT_CREDIT_LIMIT})
        save_all_users(users)
        flash('Registration successful!')
        return redirect(url_for('home'))
    return render_template('register.html')

@app.route('/purchase', methods=['GET', 'POST'])
def purchase():
    if request.method == 'POST':
        user = request.form['user']
        amount = float(request.form['amount'])
        transactions = get_all_transactions()
        transactions.append({'user': user, 'amount': amount, 'timestamp': datetime.now().isoformat()})
        save_all_transactions(transactions)
        flash('Purchase successful!')
        return redirect(url_for('home'))
    return render_template('purchase.html', users=[u['name'] for u in get_all_users()])

@app.route('/repay', methods=['GET', 'POST'])
def repay():
    if request.method == 'POST':
        user = request.form['user']
        amount = float(request.form['amount'])
        repayments = get_all_repayments()
        repayments.append({'user': user, 'amount': amount, 'timestamp': datetime.now().isoformat()})
        save_all_repayments(repayments)
        flash('Repayment successful!')
        return redirect(url_for('home'))
    return render_template('repay.html', users=[u['name'] for u in get_all_users()])

@app.route('/income_verification', methods=['GET', 'POST'])
def income_verification():
    if request.method == 'POST':
        user = request.form['user']
        status = request.form['status']
        ivs = get_all_income_verifications()
        ivs.append({'user': user, 'status': status, 'timestamp': datetime.now().isoformat()})
        save_all_income_verifications(ivs)
        flash('Income verification updated!')
        return redirect(url_for('home'))
    return render_template('income_verification.html', users=[u['name'] for u in get_all_users()])

@app.route('/dashboard')
def dashboard():
    user_infos = []
    users = get_all_users()
    for user in users:
        name = user['name']
        risk_scores = calculate_risk_scores(name)
        utilization = calculate_utilization(name)
        default_status = is_user_in_default(name)
        compliance = check_compliance(name)
        user_infos.append({
            'name': name,
            'risk_scores': risk_scores,
            'utilization': utilization,
            'default_status': default_status,
            'compliance': compliance
        })
    return render_template('dashboard.html', users=user_infos)

@app.route('/dashboard/user/<name>')
def dashboard_user(name):
    user = get_user(name)
    if not user:
        flash('User not found')
        return redirect(url_for('dashboard'))
    risk_scores = calculate_risk_scores(name)
    utilization = calculate_utilization(name)
    velocity_7 = calculate_transaction_velocity(name, 7)
    velocity_30 = calculate_transaction_velocity(name, 30)
    default_status = is_user_in_default(name)
    compliance = check_compliance(name)
    txs = get_user_transactions(name)
    rps = get_user_repayments(name)
    return render_template('user_detail.html',
        name=name,
        risk_scores=risk_scores,
        utilization=utilization,
        velocity_7=velocity_7,
        velocity_30=velocity_30,
        default_status=default_status,
        compliance=compliance,
        transactions=txs,
        repayments=rps
    )

PRODUCTS = [
    {'id': 1, 'name': 'Wireless Headphones', 'price': 100.0, 'currency': 'USD', 'region': 'US'},
    {'id': 2, 'name': 'Smart Watch', 'price': 180.0, 'currency': 'USD', 'region': 'US'},
    {'id': 3, 'name': 'Bluetooth Speaker', 'price': 60.0, 'currency': 'USD', 'region': 'US'},
    {'id': 4, 'name': 'E-Reader', 'price': 120.0, 'currency': 'USD', 'region': 'US'}
]
BNPL_PROVIDERS = [
    {'name': 'Klarna', 'apr': 0.0, 'fee': 0.0},
    {'name': 'Affirm', 'apr': 15.0, 'fee': 2.0},
    {'name': 'Afterpay', 'apr': 0.0, 'fee': 0.0}
]

# Always define enabled_providers at startup
enabled_providers = set([p['name'] for p in BNPL_PROVIDERS])

promotions = [
    {'title': 'Summer Sale: 10% off with BNPL!', 'desc': 'Boost your sales with our summer BNPL promo.'},
    {'title': 'Free Shipping for BNPL Orders', 'desc': 'Encourage larger carts with free shipping.'}
]

def simulate_soft_credit_check(user_name):
    # For demo, randomly approve 90% of users
    import random
    return random.random() < 0.9

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    import random
    regions = ['US', 'EU', 'CA', 'UAE']
    selected_region = request.form.get('region', 'US')
    selected_product = PRODUCTS[0]
    enabled = [p for p in BNPL_PROVIDERS if p['name'] in enabled_providers]
    selected_provider = enabled[0] if enabled else BNPL_PROVIDERS[0]
    user_name = None
    credit_check_passed = True
    error = None
    activated = False
    kyc_required = False
    if request.method == 'POST':
        product_id = int(request.form['product'])
        provider_name = request.form['provider']
        user_name = request.form.get('user_name', 'DemoUser')
        selected_region = request.form.get('region', 'US')
        selected_product = next((p for p in PRODUCTS if p['id'] == product_id), PRODUCTS[0])
        enabled = [p for p in BNPL_PROVIDERS if p['name'] in enabled_providers]
        selected_provider = next((p for p in enabled if p['name'] == provider_name), enabled[0] if enabled else BNPL_PROVIDERS[0])
        # Simulate KYC/AML for high-value
        kyc_required = selected_product['price'] > 150
        # Simulate soft credit check
        credit_check_passed = simulate_soft_credit_check(user_name)
        if not credit_check_passed:
            error = 'Soft credit check failed. Please try another provider or payment method.'
        elif 'consent' not in request.form:
            error = 'Consent is required.'
        else:
            activated = True
            flash(f"BNPL activated with {selected_provider['name']}: 4 payments of ${selected_product['price']/4:.2f}" + (f" (APR: {selected_provider['apr']}%, Fee: ${selected_provider['fee']})" if selected_provider['apr'] or selected_provider['fee'] else ""))
        # Log audit
        audit_log = load_audit_log()
        audit_log.append({
            'user': user_name,
            'region': selected_region,
            'product': selected_product['name'],
            'provider': selected_provider['name'],
            'consent': 'consent' in request.form,
            'kyc_required': kyc_required,
            'credit_check_passed': credit_check_passed,
            'timestamp': datetime.now().isoformat()
        })
        save_audit_log(audit_log)
    enabled = [p for p in BNPL_PROVIDERS if p['name'] in enabled_providers]
    return render_template('checkout.html',
        products=PRODUCTS,
        providers=enabled,
        selected_product=selected_product,
        selected_provider=selected_provider,
        activated=activated,
        credit_check_passed=credit_check_passed,
        error=error,
        regions=regions,
        selected_region=selected_region,
        kyc_required=kyc_required
    )

@app.route('/api/products')
def api_products():
    return jsonify(PRODUCTS)

@app.route('/api/merchant/analytics')
def api_merchant_analytics():
    transactions = get_all_transactions()
    total_sales = sum(t['amount'] for t in transactions)
    order_count = len(transactions)
    aov = (total_sales / order_count) if order_count else 0
    return jsonify({'total_sales': total_sales, 'order_count': order_count, 'aov': aov})

@app.route('/api/audit-log')
def api_audit_log():
    return jsonify(load_audit_log())

@app.route('/api-docs')
def api_docs():
    return render_template('api_docs.html')

@app.route('/merchant', methods=['GET', 'POST'])
def merchant_dashboard():
    transactions = get_all_transactions()
    users = get_all_users()
    # --- Advanced Analytics ---
    # Sales by day/week/month
    sales_by_day = defaultdict(float)
    sales_by_week = defaultdict(float)
    sales_by_month = defaultdict(float)
    for t in transactions:
        if hasattr(t['timestamp'], 'date'):
            day = t['timestamp'].date()
            week = t['timestamp'].isocalendar()[1]
            month = t['timestamp'].strftime('%Y-%m')
        else:
            from datetime import datetime
            dt = datetime.fromisoformat(t['timestamp'])
            day = dt.date()
            week = dt.isocalendar()[1]
            month = dt.strftime('%Y-%m')
        sales_by_day[day] += t['amount']
        sales_by_week[week] += t['amount']
        sales_by_month[month] += t['amount']
    # BNPL provider breakdown (simulate random provider for demo)
    import random
    provider_names = ['Klarna', 'Affirm', 'Afterpay']
    provider_sales = {name: 0.0 for name in provider_names}
    for t in transactions:
        provider = random.choice(provider_names)
        provider_sales[provider] += t['amount']
    # Top products sold (simulate random product for demo)
    product_names = [p['name'] for p in PRODUCTS]
    product_sales = Counter()
    for t in transactions:
        product = random.choice(product_names)
        product_sales[product] += 1
    # Customer segmentation (repeat vs new)
    user_tx_count = Counter([t['user'] for t in transactions])
    repeat_customers = sum(1 for c in user_tx_count.values() if c > 1)
    new_customers = sum(1 for c in user_tx_count.values() if c == 1)
    # Default/loss rates (simulated)
    default_rate = 0.04  # 4% (simulated)
    loss_rate = 0.01     # 1% (simulated)
    # --- Merchant Controls ---
    # Provider toggling (simulate with session or in-memory for demo)
    if 'enabled_providers' not in globals():
        global enabled_providers
        enabled_providers = set(provider_names)
    if request.method == 'POST':
        if 'toggle_provider' in request.form:
            prov = request.form['toggle_provider']
            if prov in enabled_providers:
                enabled_providers.remove(prov)
            else:
                enabled_providers.add(prov)
        if 'add_promo' in request.form:
            title = request.form['promo_title']
            desc = request.form['promo_desc']
            promotions.append({'title': title, 'desc': desc})
        if 'remove_promo' in request.form:
            idx = int(request.form['remove_promo'])
            if 0 <= idx < len(promotions):
                promotions.pop(idx)
    # Promotions/shoppable content
    return render_template('merchant.html',
        total_sales=total_sales,
        bnpl_sales=bnpl_sales,
        aov=aov,
        cart_abandonment_rate=cart_abandonment_rate,
        conversion_rate=conversion_rate,
        recent_tx=recent_tx,
        risk_mitigation=risk_mitigation,
        promotions=promotions,
        sales_by_day=sales_by_day,
        sales_by_week=sales_by_week,
        sales_by_month=sales_by_month,
        provider_sales=provider_sales,
        product_sales=product_sales,
        repeat_customers=repeat_customers,
        new_customers=new_customers,
        default_rate=default_rate,
        loss_rate=loss_rate,
        enabled_providers=enabled_providers,
        provider_names=provider_names,
        payout_status=payout_status,
        payout_timing=payout_timing,
        audit_log=audit_log
    )

API_KEY = 'demo-api-key-123'
def require_api_key():
    from flask import request
    key = request.headers.get('X-API-KEY')
    if key != API_KEY:
        from flask import abort
        abort(401, 'Invalid or missing API key')

from flask import Response
import io

@app.route('/api/transactions')
def api_transactions():
    require_api_key()
    txs = get_all_transactions()
    user = request.args.get('user')
    provider = request.args.get('provider')
    product = request.args.get('product')
    region = request.args.get('region')
    filtered = []
    for t in txs:
        if user and t['user'] != user:
            continue
        # Simulate provider/product/region for demo
        if provider and provider not in ['Klarna', 'Affirm', 'Afterpay']:
            continue
        if product and product not in [p['name'] for p in PRODUCTS]:
            continue
        if region and region not in ['US', 'EU', 'CA', 'UAE']:
            continue
        filtered.append(t)
    return jsonify(filtered)

@app.route('/api/transactions.csv')
def api_transactions_csv():
    require_api_key()
    txs = get_all_transactions()
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=txs[0].keys())
    writer.writeheader()
    writer.writerows(txs)
    return Response(output.getvalue(), mimetype='text/csv', headers={'Content-Disposition': 'attachment;filename=transactions.csv'})

@app.route('/api/repayments')
def api_repayments():
    require_api_key()
    rps = get_all_repayments()
    user = request.args.get('user')
    filtered = [r for r in rps if not user or r['user'] == user]
    return jsonify(filtered)

@app.route('/api/repayments.csv')
def api_repayments_csv():
    require_api_key()
    rps = get_all_repayments()
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=rps[0].keys())
    writer.writeheader()
    writer.writerows(rps)
    return Response(output.getvalue(), mimetype='text/csv', headers={'Content-Disposition': 'attachment;filename=repayments.csv'})

@app.route('/api/audit-log.csv')
def api_audit_log_csv():
    require_api_key()
    log = load_audit_log()
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=log[0].keys())
    writer.writeheader()
    writer.writerows(log)
    return Response(output.getvalue(), mimetype='text/csv', headers={'Content-Disposition': 'attachment;filename=audit_log.csv'})

@app.route('/api/users')
def api_users():
    require_api_key()
    return jsonify(get_all_users())

@app.route('/api/providers')
def api_providers():
    require_api_key()
    return jsonify(list(enabled_providers))

@app.route('/api/kyc-check', methods=['POST'])
def api_kyc_check():
    require_api_key()
    data = request.json
    # Simulate KYC/AML: pass if amount <= 150, else random
    import random
    amount = data.get('amount', 0)
    if amount <= 150:
        return jsonify({'kyc_passed': True})
    return jsonify({'kyc_passed': random.random() > 0.1})

@app.route('/api/checkout', methods=['POST'])
def api_checkout():
    require_api_key()
    data = request.json
    user = data.get('user')
    product = data.get('product')
    provider = data.get('provider')
    region = data.get('region', 'US')
    consent = data.get('consent', False)
    amount = data.get('amount', 0)
    # Simulate credit check
    import random
    credit_check_passed = random.random() < 0.9
    kyc_required = amount > 150
    approved = consent and credit_check_passed and (not kyc_required or random.random() > 0.1)
    # Log audit
    audit_log = load_audit_log()
    audit_log.append({
        'user': user,
        'region': region,
        'product': product,
        'provider': provider,
        'consent': consent,
        'kyc_required': kyc_required,
        'credit_check_passed': credit_check_passed,
        'timestamp': datetime.now().isoformat()
    })
    save_audit_log(audit_log)
    return jsonify({'approved': approved, 'credit_check_passed': credit_check_passed, 'kyc_required': kyc_required})

@app.route('/api/virtual-card', methods=['POST'])
def api_virtual_card():
    require_api_key()
    import random, string
    card_number = ''.join(random.choices(string.digits, k=16))
    expiry = '12/28'
    cvv = ''.join(random.choices(string.digits, k=3))
    return jsonify({'card_number': card_number, 'expiry': expiry, 'cvv': cvv})

@app.route('/api/underwriting', methods=['POST'])
def api_underwriting():
    require_api_key()
    data = request.json
    # Simulate AI underwriting: risk score based on utilization, region, income_verified
    utilization = data.get('utilization', 0.3)
    region = data.get('region', 'US')
    income_verified = data.get('income_verified', True)
    score = 100 - 50*utilization - (10 if not income_verified else 0)
    if region == 'EU':
        score -= 5
    elif region == 'UAE':
        score -= 3
    return jsonify({'risk_score': round(score, 2)})

@app.route('/api/subscription', methods=['POST'])
def api_subscription():
    require_api_key()
    data = request.json
    # Simulate subscription creation
    user = data.get('user')
    product = data.get('product')
    amount = data.get('amount')
    interval = data.get('interval', 'monthly')
    return jsonify({'status': 'created', 'user': user, 'product': product, 'amount': amount, 'interval': interval})

if __name__ == '__main__':
    app.run(debug=True) 