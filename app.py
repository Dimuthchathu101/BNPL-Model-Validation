from flask import Flask, request, render_template, redirect, url_for, flash, jsonify
from datetime import datetime, timedelta
import json
import os

app = Flask(__name__)
app.secret_key = 'bnpl_secret_key'

DATA_DIR = 'data'
USERS_FILE = os.path.join(DATA_DIR, 'users.json')
TRANSACTIONS_FILE = os.path.join(DATA_DIR, 'transactions.json')
REPAYMENTS_FILE = os.path.join(DATA_DIR, 'repayments.json')
INCOME_VERIFICATIONS_FILE = os.path.join(DATA_DIR, 'income_verifications.json')

def load_json(filename):
    if not os.path.exists(filename):
        return []
    with open(filename, 'r') as f:
        return json.load(f)

def save_json(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f, default=str)

# Replace in-memory lists with file-backed storage

def get_all_users():
    users = load_json(USERS_FILE)
    # Convert timestamp strings to datetime objects
    for u in users:
        if isinstance(u['registered'], str):
            u['registered'] = datetime.fromisoformat(u['registered'])
    return users

def save_all_users(users):
    # Convert datetime to isoformat for JSON
    for u in users:
        if isinstance(u['registered'], datetime):
            u['registered'] = u['registered'].isoformat()
    save_json(USERS_FILE, users)

def get_all_transactions():
    txs = load_json(TRANSACTIONS_FILE)
    # Convert timestamp strings to datetime objects
    for t in txs:
        if isinstance(t['timestamp'], str):
            t['timestamp'] = datetime.fromisoformat(t['timestamp'])
    return txs

def save_all_transactions(transactions):
    # Convert datetime to isoformat for JSON
    for t in transactions:
        if isinstance(t['timestamp'], datetime):
            t['timestamp'] = t['timestamp'].isoformat()
    save_json(TRANSACTIONS_FILE, transactions)

def get_all_repayments():
    rps = load_json(REPAYMENTS_FILE)
    for r in rps:
        if isinstance(r['timestamp'], str):
            r['timestamp'] = datetime.fromisoformat(r['timestamp'])
    return rps

def save_all_repayments(repayments):
    for r in repayments:
        if isinstance(r['timestamp'], datetime):
            r['timestamp'] = r['timestamp'].isoformat()
    save_json(REPAYMENTS_FILE, repayments)

def get_all_income_verifications():
    ivs = load_json(INCOME_VERIFICATIONS_FILE)
    for v in ivs:
        if isinstance(v['timestamp'], str):
            v['timestamp'] = datetime.fromisoformat(v['timestamp'])
    return ivs

def save_all_income_verifications(ivs):
    for v in ivs:
        if isinstance(v['timestamp'], datetime):
            v['timestamp'] = v['timestamp'].isoformat()
    save_json(INCOME_VERIFICATIONS_FILE, ivs)

MIN_AGE = 18
DEFAULT_OVERDUE_DAYS = 60
DEFAULT_CREDIT_LIMIT = 1000.0

# --- Helper Functions ---
def get_user(name):
    users = get_all_users()
    for u in users:
        if u['name'] == name:
            return u
    return None

def get_user_transactions(name):
    transactions = get_all_transactions()
    return [t for t in transactions if t['user'] == name]

def get_user_repayments(name):
    repayments = get_all_repayments()
    return [r for r in repayments if r['user'] == name]

def get_income_verification_status(name):
    ivs = get_all_income_verifications()
    for v in ivs[::-1]:
        if v['user'] == name:
            return v['status']
    return 'Not Verified'

def calculate_utilization(name):
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
    now = datetime.now()
    recent = [t for t in get_user_transactions(name) if (now - t['timestamp']).days < days]
    return len(recent)

def is_user_in_default(name):
    # Overdue if any purchase is unpaid for 60+ days
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
    # Champion: base on utilization, overdue, income verification
    utilization = calculate_utilization(name)
    overdue = is_user_in_default(name)
    income_status = get_income_verification_status(name)
    velocity = calculate_transaction_velocity(name, 30)
    # Champion: 100 - 50*utilization - 30*overdue - 10*not_verified
    champion = 100 - 50*utilization - (30 if overdue else 0) - (10 if income_status != 'Verified' else 0)
    # Challenger: 100 - 40*utilization - 40*overdue - 10*not_verified - 10*velocity>5
    challenger = 100 - 40*utilization - (40 if overdue else 0) - (10 if income_status != 'Verified' else 0) - (10 if velocity > 5 else 0)
    return {'champion': round(champion, 2), 'challenger': round(challenger, 2)}

def check_compliance(name):
    user = get_user(name)
    if not user:
        return 'Not Registered'
    age = (datetime.now() - datetime.strptime(user['dob'], '%Y-%m-%d')).days // 365
    if age < MIN_AGE:
        return 'Underage'
    if get_income_verification_status(name) != 'Verified':
        # If any purchase > 500, require verification
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

@app.route('/api/users')
def api_users():
    result = []
    users = get_all_users()
    for user in users:
        name = user['name']
        risk_scores = calculate_risk_scores(name)
        utilization = calculate_utilization(name)
        default_status = is_user_in_default(name)
        compliance = check_compliance(name)
        result.append({
            'name': name,
            'risk_scores': risk_scores,
            'utilization': utilization,
            'default_status': default_status,
            'compliance': compliance
        })
    return jsonify(result)

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

if __name__ == '__main__':
    app.run(debug=True) 