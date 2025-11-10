# app.py
from flask import Flask, request, redirect, url_for, render_template_string, session, flash
import mysql.connector
from mysql.connector import Error
from datetime import datetime, date
import random, os, requests, time

# ------------------------------
# Configuration (use env vars to override)
# ------------------------------
DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASS", "Aathi2004@#"),
    "database": os.environ.get("DB_NAME", "aathi_bank"),
    "port": int(os.environ.get("DB_PORT", 3306))
}

FAST2SMS_FILE = "fast2sms_key.txt"
FAST2SMS_ENDPOINT = "https://www.fast2sms.com/dev/bulkV2"

SECRET_KEY = os.environ.get("FLASK_SECRET", "dev-secret-change-me")

# ------------------------------
# App init
# ------------------------------
app = Flask(__name__)
app.secret_key = SECRET_KEY
app.permanent_session_lifetime = 3600

# ------------------------------
# DB helpers
# ------------------------------
def get_db_conn():
    return mysql.connector.connect(**DB_CONFIG)

def init_schema():
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS accounts (
        account_number BIGINT PRIMARY KEY,
        name VARCHAR(80) NOT NULL,
        dob DATE NOT NULL,
        phone VARCHAR(15) NOT NULL,
        aadhar VARCHAR(12) NOT NULL UNIQUE,
        pan VARCHAR(10) NOT NULL UNIQUE,
        pin VARCHAR(6) NOT NULL,
        balance DOUBLE NOT NULL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        account_number BIGINT NOT NULL,
        txn_type ENUM('DEPOSIT','WITHDRAW','TRANSFER_OUT','TRANSFER_IN','ACCOUNT_CREATE','PIN_CHANGE','ACCOUNT_DELETE') NOT NULL,
        amount DOUBLE NOT NULL,
        note VARCHAR(255),
        counterparty BIGINT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (account_number) REFERENCES accounts(account_number)
    )""")
    conn.commit()
    cur.close()
    conn.close()

# ------------------------------
# Utilities
# ------------------------------
def read_fast2sms_key():
    if os.environ.get("FAST2SMS_API_KEY"):
        return os.environ["FAST2SMS_API_KEY"]
    if os.path.exists(FAST2SMS_FILE):
        try:
            with open(FAST2SMS_FILE, 'r', encoding='utf-8') as f:
                k = f.read().strip()
                if k: return k
        except Exception:
            pass
    return None

def send_sms(mobile: str, message: str):
    api_key = read_fast2sms_key()
    if not api_key:
        # no key configured; skip SMS in demo
        print("(SMS) no key configured; skipping.")
        return
    try:
        headers = {'authorization': api_key}
        data = {
            'route': 'v3',
            'sender_id': 'TXTIND',
            'message': message,
            'language': 'english',
            'numbers': mobile
        }
        resp = requests.post(FAST2SMS_ENDPOINT, headers=headers, data=data, timeout=8)
        if resp.status_code != 200:
            print("(SMS) non-200", resp.status_code, resp.text)
    except Exception as e:
        print("(SMS) failed:", e)

def generate_account_number(cur):
    while True:
        acc = random.randint(2000000000, 9999999999)
        cur.execute("SELECT 1 FROM accounts WHERE account_number=%s", (acc,))
        if not cur.fetchone():
            return acc

def calc_age(dob: date):
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

# ------------------------------
# Templates (inlined for single-file)
# ------------------------------
base_tpl = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Aathithyan Bank (Demo)</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
  </head>
  <body class="bg-light">
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary mb-4">
      <div class="container">
        <a class="navbar-brand" href="{{ url_for('index') }}">Aathithyan Bank</a>
        <div class="collapse navbar-collapse">
          <ul class="navbar-nav ms-auto">
            {% if session.get('acc_no') %}
              <li class="nav-item"><a class="nav-link" href="{{ url_for('dashboard') }}">Dashboard</a></li>
              <li class="nav-item"><a class="nav-link" href="{{ url_for('logout') }}">Logout</a></li>
            {% else %}
              <li class="nav-item"><a class="nav-link" href="{{ url_for('login') }}">Login</a></li>
              <li class="nav-item"><a class="nav-link" href="{{ url_for('create_account') }}">Create Account</a></li>
            {% endif %}
          </ul>
        </div>
      </div>
    </nav>
    <div class="container">
      {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
          {% for cat, msg in messages %}
            <div class="alert alert-{{ cat }} alert-dismissible">{{ msg }}<button class="btn-close" data-bs-dismiss="alert"></button></div>
          {% endfor %}
        {% endif %}
      {% endwith %}
      {{ content }}
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
  </body>
</html>
"""

index_content = """
<div class="row">
  <div class="col-md-8">
    <div class="card p-3">
      <h3>Welcome to Aathithyan Bank (Demo)</h3>
      <p>This is a local Flask demo of your bank app. Use the links above to create an account or login.</p>
      <ul>
        <li>Local MySQL used (see DB config)</li>
        <li>Fast2SMS optional — store key in <code>fast2sms_key.txt</code> or env var <code>FAST2SMS_API_KEY</code></li>
      </ul>
    </div>
  </div>
  <div class="col-md-4">
    <div class="card p-3">
      <h5>Quick actions</h5>
      <a href="{{ url_for('create_account') }}" class="btn btn-success mb-2">Create Account</a><br>
      <a href="{{ url_for('login') }}" class="btn btn-primary">Login</a>
    </div>
  </div>
</div>
"""

create_account_form = """
<div class="card p-3">
  <h4>Create Account</h4>
  <form method="post">
    <div class="mb-3"><label class="form-label">Full name</label><input class="form-control" name="name" required></div>
    <div class="mb-3"><label class="form-label">DOB (YYYY-MM-DD)</label><input class="form-control" name="dob" required></div>
    <div class="mb-3"><label class="form-label">Phone</label><input class="form-control" name="phone" required></div>
    <div class="mb-3"><label class="form-label">Aadhar (12 digits)</label><input class="form-control" name="aadhar" required></div>
    <div class="mb-3"><label class="form-label">PAN</label><input class="form-control" name="pan" required></div>
    <div class="mb-3"><label class="form-label">ATM PIN (4 digits)</label><input class="form-control" name="pin" required></div>
    <div class="mb-3"><label class="form-label">Initial deposit (min 1000)</label><input class="form-control" name="init_amt" type="number" required></div>
    <button class="btn btn-success">Create</button>
  </form>
</div>
"""

login_form = """
<div class="card p-3">
  <h4>Login</h4>
  <form method="post">
    <div class="mb-3"><label class="form-label">Account Number</label><input class="form-control" name="acc_no" required></div>
    <div class="mb-3"><label class="form-label">PIN</label><input class="form-control" name="pin" required></div>
    <button class="btn btn-primary">Login</button>
  </form>
  <hr>
  <a href="{{ url_for('atm_login') }}" class="btn btn-outline-secondary">ATM Login (use PIN only)</a>
</div>
"""

dashboard_tpl = """
<div class="row">
  <div class="col-md-8">
    <div class="card p-3">
      <h4>Account Dashboard — {{ acc_no }}</h4>
      <p><strong>Name:</strong> {{ name }} &nbsp; <strong>Balance:</strong> ₹{{ balance }}</p>
      <div class="mb-3">
        <a class="btn btn-success" href="{{ url_for('deposit') }}">Deposit</a>
        <a class="btn btn-warning" href="{{ url_for('withdraw') }}">Withdraw</a>
        <a class="btn btn-info" href="{{ url_for('transfer') }}">Transfer</a>
        <a class="btn btn-secondary" href="{{ url_for('change_pin') }}">Change PIN</a>
      </div>
      <h5>Last 10 Transactions</h5>
      <table class="table table-sm">
        <thead><tr><th>Date</th><th>Type</th><th>Amount</th><th>Note</th></tr></thead>
        <tbody>
          {% for t in transactions %}
            <tr><td>{{ t[4] }}</td><td>{{ t[2] }}</td><td>{{ t[3] }}</td><td>{{ t[5] or '' }}</td></tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  </div>
</div>
"""

# ------------------------------
# Routes
# ------------------------------
@app.route('/')
def index():
    return render_template_string(base_tpl, content=index_content)

@app.route('/create', methods=['GET','POST'])
def create_account():
    if request.method == 'GET':
        return render_template_string(base_tpl, content=create_account_form)
    # POST -> create
    name = request.form.get('name','').strip()
    dob_str = request.form.get('dob','').strip()
    phone = request.form.get('phone','').strip()
    aadhar = request.form.get('aadhar','').strip()
    pan = request.form.get('pan','').strip().upper()
    pin = request.form.get('pin','').strip()
    try:
        dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
    except Exception:
        flash("Invalid DOB format", "danger"); return redirect(url_for('create_account'))
    if calc_age(dob) < 18:
        flash("Must be 18+", "danger"); return redirect(url_for('create_account'))
    try:
        init_amt = float(request.form.get('init_amt', '0'))
        if init_amt < 1000:
            flash("Minimum initial deposit ₹1000", "danger"); return redirect(url_for('create_account'))
    except:
        flash("Invalid initial amount", "danger"); return redirect(url_for('create_account'))

    conn = get_db_conn(); cur = conn.cursor()
    try:
        acc_no = generate_account_number(cur)
        cur.execute("""INSERT INTO accounts (account_number,name,dob,phone,aadhar,pan,pin,balance)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (acc_no, name, dob, phone, aadhar, pan, pin, init_amt))
        cur.execute("""INSERT INTO transactions (account_number, txn_type, amount, note)
                       VALUES (%s,'ACCOUNT_CREATE',%s,%s)""", (acc_no, init_amt, "Initial deposit"))
        conn.commit()
        send_sms(phone, f"Aathithyan Bank: Account {acc_no} created. Balance ₹{init_amt:.2f}")
        flash(f"Account created: {acc_no}", "success")
        return redirect(url_for('login'))
    except Error as e:
        conn.rollback()
        flash(f"Failed to create account: {e}", "danger")
        return redirect(url_for('create_account'))
    finally:
        cur.close(); conn.close()

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'GET':
        return render_template_string(base_tpl, content=login_form)
    try:
        acc_no = int(request.form.get('acc_no'))
    except:
        flash("Invalid account number", "danger"); return redirect(url_for('login'))
    pin = request.form.get('pin','').strip()
    conn = get_db_conn(); cur = conn.cursor()
    cur.execute("SELECT name FROM accounts WHERE account_number=%s AND pin=%s", (acc_no, pin))
    row = cur.fetchone()
    cur.close(); conn.close()
    if row:
        session['acc_no'] = acc_no
        flash("Login successful", "success")
        return redirect(url_for('dashboard'))
    flash("Wrong account or PIN", "danger")
    return redirect(url_for('login'))

@app.route('/atm-login', methods=['GET','POST'])
def atm_login():
    # ATM login: enter PIN only
    content = """
    <div class="card p-3">
      <h4>ATM Login (enter PIN)</h4>
      <form method="post">
        <div class="mb-3"><label class="form-label">4-digit PIN</label><input class="form-control" name="pin" required></div>
        <button class="btn btn-primary">Login</button>
      </form>
    </div>"""
    if request.method == 'GET':
        return render_template_string(base_tpl, content=content)
    pin = request.form.get('pin','').strip()
    conn = get_db_conn(); cur = conn.cursor()
    cur.execute("SELECT account_number,name FROM accounts WHERE pin=%s", (pin,))
    rows = cur.fetchall()
    cur.close(); conn.close()
    if not rows:
        flash("No account with this PIN", "danger"); return redirect(url_for('atm_login'))
    if len(rows) > 1:
        flash("Multiple accounts use this PIN — please login with account number.", "warning")
        return redirect(url_for('login'))
    acc_no = rows[0][0]
    session['acc_no'] = acc_no
    flash("ATM login success", "success")
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    acc_no = session.get('acc_no')
    if not acc_no:
        return redirect(url_for('login'))
    conn = get_db_conn(); cur = conn.cursor()
    cur.execute("SELECT name, balance FROM accounts WHERE account_number=%s", (acc_no,))
    row = cur.fetchone()
    if not row:
        flash("Account not found", "danger"); return redirect(url_for('logout'))
    name, balance = row
    cur.execute("SELECT id, account_number, txn_type, amount, created_at, note FROM transactions WHERE account_number=%s ORDER BY created_at DESC LIMIT 10", (acc_no,))
    transactions = cur.fetchall()
    cur.close(); conn.close()
    content = render_template_string(dashboard_tpl, acc_no=acc_no, name=name, balance=f"{balance:.2f}", transactions=transactions)
    return render_template_string(base_tpl, content=content)

@app.route('/logout')
def logout():
    session.pop('acc_no', None)
    flash("Logged out", "success")
    return redirect(url_for('index'))

@app.route('/deposit', methods=['GET','POST'])
def deposit():
    acc_no = session.get('acc_no'); 
    if not acc_no: return redirect(url_for('login'))
    if request.method == 'GET':
        return render_template_string(base_tpl, content="""
          <div class="card p-3"><h4>Deposit</h4>
            <form method="post"><div class="mb-3"><label>Amount</label><input class="form-control" name="amount" required></div><button class="btn btn-success">Deposit</button></form></div>""")
    try:
        amt = float(request.form.get('amount'))
        if amt <= 0: raise ValueError()
    except:
        flash("Invalid amount", "danger"); return redirect(url_for('deposit'))
    conn = get_db_conn(); cur = conn.cursor()
    try:
        cur.execute("UPDATE accounts SET balance = balance + %s WHERE account_number=%s", (amt, acc_no))
        cur.execute("INSERT INTO transactions (account_number, txn_type, amount, note) VALUES (%s,'DEPOSIT',%s,%s)", (acc_no, amt, "Web deposit"))
        cur.execute("SELECT phone FROM accounts WHERE account_number=%s", (acc_no,))
        phone = cur.fetchone()[0]
        conn.commit()
        send_sms(phone, f"Aathithyan Bank: ₹{amt:.2f} deposited to {acc_no}")
        flash("Deposit successful", "success")
    except Exception as e:
        conn.rollback(); flash(f"Deposit failed: {e}", "danger")
    finally:
        cur.close(); conn.close()
    return redirect(url_for('dashboard'))

@app.route('/withdraw', methods=['GET','POST'])
def withdraw():
    acc_no = session.get('acc_no'); 
    if not acc_no: return redirect(url_for('login'))
    if request.method == 'GET':
        return render_template_string(base_tpl, content="""
          <div class="card p-3"><h4>Withdraw</h4>
            <form method="post"><div class="mb-3"><label>Amount</label><input class="form-control" name="amount" required></div><button class="btn btn-warning">Withdraw</button></form></div>""")
    try:
        amt = float(request.form.get('amount'))
        if amt <= 0: raise ValueError()
    except:
        flash("Invalid amount", "danger"); return redirect(url_for('withdraw'))
    conn = get_db_conn(); cur = conn.cursor()
    try:
        conn.start_transaction()
        cur.execute("SELECT balance, phone FROM accounts WHERE account_number=%s FOR UPDATE", (acc_no,))
        r = cur.fetchone()
        if not r:
            raise ValueError("Account not found")
        bal, phone = r
        if bal < amt:
            raise ValueError("Insufficient balance")
        cur.execute("UPDATE accounts SET balance = balance - %s WHERE account_number=%s", (amt, acc_no))
        cur.execute("INSERT INTO transactions (account_number, txn_type, amount, note) VALUES (%s,'WITHDRAW',%s,%s)", (acc_no, amt, "Web withdraw"))
        conn.commit()
        send_sms(phone, f"Aathithyan Bank: ₹{amt:.2f} withdrawn from {acc_no}")
        flash("Withdrawal success", "success")
    except Exception as e:
        conn.rollback(); flash(f"Withdraw failed: {e}", "danger")
    finally:
        cur.close(); conn.close()
    return redirect(url_for('dashboard'))

@app.route('/transfer', methods=['GET','POST'])
def transfer():
    acc_no = session.get('acc_no'); 
    if not acc_no: return redirect(url_for('login'))
    if request.method == 'GET':
        return render_template_string(base_tpl, content="""
          <div class="card p-3"><h4>Transfer</h4>
            <form method="post">
              <div class="mb-3"><label>To Account</label><input class="form-control" name="to_acc" required></div>
              <div class="mb-3"><label>Amount</label><input class="form-control" name="amount" required></div>
              <button class="btn btn-info">Send</button>
            </form>
          </div>""")
    try:
        to_acc = int(request.form.get('to_acc'))
        amt = float(request.form.get('amount'))
        if amt <= 0: raise ValueError()
        if to_acc == acc_no: raise ValueError("Cannot transfer to same account")
    except Exception as e:
        flash(f"Invalid input: {e}", "danger"); return redirect(url_for('transfer'))
    conn = get_db_conn(); cur = conn.cursor()
    try:
        conn.start_transaction()
        cur.execute("SELECT balance, phone FROM accounts WHERE account_number=%s FOR UPDATE", (acc_no,))
        src = cur.fetchone()
        if not src: raise ValueError("Source not found")
        src_bal, src_phone = src
        if src_bal < amt: raise ValueError("Insufficient balance")
        cur.execute("SELECT phone FROM accounts WHERE account_number=%s FOR UPDATE", (to_acc,))
        dst = cur.fetchone()
        if not dst: raise ValueError("Destination not found")
        dst_phone = dst[0]
        cur.execute("UPDATE accounts SET balance = balance - %s WHERE account_number=%s", (amt, acc_no))
        cur.execute("UPDATE accounts SET balance = balance + %s WHERE account_number=%s", (amt, to_acc))
        cur.execute("INSERT INTO transactions (account_number, txn_type, amount, note, counterparty) VALUES (%s,'TRANSFER_OUT',%s,%s,%s)",
                    (acc_no, amt, f"Transfer to {to_acc}", to_acc))
        cur.execute("INSERT INTO transactions (account_number, txn_type, amount, note, counterparty) VALUES (%s,'TRANSFER_IN',%s,%s,%s)",
                    (to_acc, amt, f"Transfer from {acc_no}", acc_no))
        conn.commit()
        send_sms(src_phone, f"Aathithyan Bank: ₹{amt:.2f} sent to {to_acc}")
        send_sms(dst_phone, f"Aathithyan Bank: ₹{amt:.2f} received from {acc_no}")
        flash("Transfer successful", "success")
    except Exception as e:
        conn.rollback(); flash(f"Transfer failed: {e}", "danger")
    finally:
        cur.close(); conn.close()
    return redirect(url_for('dashboard'))

@app.route('/change-pin', methods=['GET','POST'])
def change_pin():
    acc_no = session.get('acc_no'); 
    if not acc_no: return redirect(url_for('login'))
    if request.method == 'GET':
        return render_template_string(base_tpl, content="""
          <div class="card p-3"><h4>Change PIN</h4>
            <form method="post"><div class="mb-3"><label>New 4-digit PIN</label><input class="form-control" name="new_pin" required></div><button class="btn btn-secondary">Change</button></form></div>""")
    new_pin = request.form.get('new_pin','').strip()
    if not (new_pin.isdigit() and len(new_pin) == 4):
        flash("PIN must be 4 digits", "danger"); return redirect(url_for('change_pin'))
    conn = get_db_conn(); cur = conn.cursor()
    try:
        cur.execute("UPDATE accounts SET pin=%s WHERE account_number=%s", (new_pin, acc_no))
        cur.execute("INSERT INTO transactions (account_number, txn_type, amount, note) VALUES (%s,'PIN_CHANGE',0,%s)", (acc_no, "PIN changed via web"))
        cur.execute("SELECT phone FROM accounts WHERE account_number=%s", (acc_no,))
        phone = cur.fetchone()[0]
        conn.commit()
        send_sms(phone, f"Aathithyan Bank: PIN changed for {acc_no}")
        flash("PIN updated", "success")
    except Exception as e:
        conn.rollback(); flash(f"Failed to change PIN: {e}", "danger")
    finally:
        cur.close(); conn.close()
    return redirect(url_for('dashboard'))

# ------------------------------
# Start
# ------------------------------
if __name__ == '__main__':
    print("Initializing database schema (if needed)...")
    init_schema()
    print("Starting Flask (development server). Visit http://127.0.0.1:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
