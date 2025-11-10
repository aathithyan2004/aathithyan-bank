##import mysql.connector
##from mysql.connector import Error
##import requests
##from datetime import datetime, date
##import random
##import os
##import time
##import sys
##
##
### ===============================
### CONFIG
### ===============================
##DB_CONFIG = {
##    "host": "localhost",
##    "user": "root",
##    "password": "Aathi2004@#",   # <-- your MySQL root password
##    "database": "aathi_bank"
##}
##
##SECRETS_FILE = "fast2sms_key.txt"  # Fast2SMS API key stored here (kept local)
##FAST2SMS_ENDPOINT = "https://www.fast2sms.com/dev/bulkV2"
##
### ===============================
### DB Helpers
### ===============================
##
##def get_db():
##    return mysql.connector.connect(**DB_CONFIG)
##
##
##def init_schema():
##    """Create required tables if they don't exist."""
##    conn = get_db()
##    cur = conn.cursor()
##
##    cur.execute(
##        """
##        CREATE TABLE IF NOT EXISTS accounts (
##            account_number BIGINT PRIMARY KEY,
##            name VARCHAR(80) NOT NULL,
##            dob DATE NOT NULL,
##            phone VARCHAR(15) NOT NULL,
##            aadhar VARCHAR(12) NOT NULL UNIQUE,
##            pan VARCHAR(10) NOT NULL UNIQUE,
##            pin VARCHAR(6) NOT NULL,
##            balance DOUBLE NOT NULL DEFAULT 0,
##            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
##            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
##        );
##        """
##    )
##
##    cur.execute(
##        """
##        CREATE TABLE IF NOT EXISTS transactions (
##            id BIGINT PRIMARY KEY AUTO_INCREMENT,
##            account_number BIGINT NOT NULL,
##            txn_type ENUM('DEPOSIT','WITHDRAW','TRANSFER_OUT','TRANSFER_IN','ACCOUNT_CREATE','PIN_CHANGE','ACCOUNT_DELETE') NOT NULL,
##            amount DOUBLE NOT NULL,
##            note VARCHAR(255),
##            counterparty BIGINT NULL,
##            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
##            FOREIGN KEY (account_number) REFERENCES accounts(account_number)
##        );
##        """
##    )
##
##    conn.commit()
##    cur.close()
##    conn.close()
##
##
### ===============================
### Utilities
### ===============================
##
##def read_fast2sms_key() -> str:
##    """Read or prompt-and-save Fast2SMS API key. We never print it back."""
##    if os.path.exists(SECRETS_FILE):
##        try:
##            with open(SECRETS_FILE, 'r', encoding='utf-8') as f:
##                key = f.read().strip()
##                if key:
##                    return key
##        except Exception:
##            pass
##    # Prompt once if missing
##    print("Fast2SMS API key not found. Paste it once. It will be stored in fast2sms_key.txt locally (kept private).")
##    key = input("Enter Fast2SMS API Key: ").strip()
##    with open(SECRETS_FILE, 'w', encoding='utf-8') as f:
##        f.write(key)
##    return key
##
##
##def send_sms(mobile: str, message: str):
##    """Send REAL SMS via Fast2SMS. If fail, print a short message and continue."""
##    try:
##        api_key = read_fast2sms_key()
##        headers = {'authorization': api_key}
##        data = {
##            'route': 'v3',
##            'sender_id': 'TXTIND',
##            'message': message,
##            'language': 'english',
##            'flash': 0,
##            'numbers': mobile
##        }
##        resp = requests.post(FAST2SMS_ENDPOINT, headers=headers, data=data, timeout=10)
##        if resp.status_code != 200:
##            print(f"(SMS) Non-200 response: {resp.status_code}")
##    except Exception as e:
##        print(f"(SMS) Failed to send: {e}")
##
##
##def generate_account_number(cur) -> int:
##    while True:
##        acc = random.randint(2000000000, 9999999999)  # 10-digit
##        cur.execute("SELECT 1 FROM accounts WHERE account_number=%s", (acc,))
##        if not cur.fetchone():
##            return acc
##
##
##def calc_age(dob: date) -> int:
##    today = date.today()
##    years = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
##    return years
##
##
##def require_min_deposit(amount: float):
##    if amount < 1000:
##        raise ValueError("Minimum initial deposit is ₹1000")
##
##
##def atm_animate(msg="Processing"):
##    print(msg, end="", flush=True)
##    for _ in range(3):
##        time.sleep(0.4)
##        print('.', end='', flush=True)
##
### ===============================
### BANK FLOWS
### ===============================
##
##def create_account_flow():
##    print("\n=== Create New Bank Account ===")
##    name = input("Full Name: ").strip()
##    dob_str = input("Date of Birth (YYYY-MM-DD): ").strip()
##    phone = input("Mobile Number (+91XXXXXXXXXX or 10 digits): ").strip()
##    aadhar = input("Aadhar (12 digits): ").strip()
##    pan = input("PAN (10 chars, e.g. ABCDE1234F): ").strip().upper()
##    pin = input("Set 4-digit ATM PIN: ").strip()
##
##    try:
##        dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
##    except ValueError:
##        print("Invalid DOB format.")
##        return
##
##    age = calc_age(dob)
##    if age < 18:
##        print("Only users 18+ can create an account.")
##        return
##
##    if not (pin.isdigit() and len(pin) == 4):
##        print("PIN must be 4 digits.")
##        return
##
##    try:
##        init_amt = float(input("Initial Deposit (min ₹1000): "))
##        require_min_deposit(init_amt)
##    except Exception as e:
##        print(f"{e}")
##        return
##
##    conn = get_db()
##    cur = conn.cursor()
##    try:
##        acc_no = generate_account_number(cur)
##        cur.execute(
##            """
##            INSERT INTO accounts (account_number, name, dob, phone, aadhar, pan, pin, balance)
##            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
##            """,
##            (acc_no, name, dob, phone, aadhar, pan, pin, init_amt)
##        )
##        cur.execute(
##            """
##            INSERT INTO transactions (account_number, txn_type, amount, note)
##            VALUES (%s,'ACCOUNT_CREATE',%s,%s)
##            """,
##            (acc_no, init_amt, "Initial deposit on account creation")
##        )
##        conn.commit()
##        print(f" Account created! Your Account Number is {acc_no}")
##        send_sms(phone, f"Sanjay Bank: Account {acc_no} created successfully. Opening balance ₹{init_amt:.2f}.")
##    except Error as e:
##        conn.rollback()
##        print(" Failed to create account:", e)
##    finally:
##        cur.close(); conn.close()
##
##
##def login_flow() -> int | None:
##    print("\n=== Login (using Account Number + PIN) ===")
##    try:
##        acc_no = int(input("Account Number: ").strip())
##    except ValueError:
##        print(" Invalid account number")
##        return None
##    pin = input("ATM PIN (4 digits): ").strip()
##    conn = get_db(); cur = conn.cursor()
##    cur.execute("SELECT account_number FROM accounts WHERE account_number=%s AND pin=%s", (acc_no, pin))
##    row = cur.fetchone()
##    cur.close(); conn.close()
##    if row:
##        print(" Login successful!")
##        return acc_no
##    print(" Wrong account number or PIN")
##    return None
##
##
##def view_balance(acc_no: int):
##    conn = get_db(); cur = conn.cursor()
##    cur.execute("SELECT balance, phone FROM accounts WHERE account_number=%s", (acc_no,))
##    row = cur.fetchone()
##    cur.close(); conn.close()
##    if row:
##        bal, _ = row
##        atm_animate("Fetching balance")
##        print(f" Balance: ₹{bal:.2f}")
##
##
##def deposit_money(acc_no: int):
##    try:
##        amt = float(input("Amount to deposit: ").strip())
##        if amt <= 0:
##            print(" Amount must be positive.")
##            return
##    except ValueError:
##        print(" Invalid amount")
##        return
##    conn = get_db(); cur = conn.cursor()
##    try:
##        cur.execute("UPDATE accounts SET balance = balance + %s WHERE account_number=%s", (amt, acc_no))
##        cur.execute("INSERT INTO transactions (account_number, txn_type, amount, note) VALUES (%s,'DEPOSIT',%s,%s)", (acc_no, amt, "Online deposit"))
##        cur.execute("SELECT phone FROM accounts WHERE account_number=%s", (acc_no,))
##        phone = cur.fetchone()[0]
##        conn.commit()
##        atm_animate("Processing deposit")
##        print(" Deposit successful!")
##        send_sms(phone, f"Sanjay Bank: ₹{amt:.2f} deposited. A/c {acc_no}.")
##    except Error as e:
##        conn.rollback(); print(" Deposit failed:", e)
##    finally:
##        cur.close(); conn.close()
##
##
##def online_transfer(acc_no: int):
##    print("\n=== Online Transfer (Account → Account) ===")
##    try:
##        to_acc = int(input("Receiver Account Number: ").strip())
##        amt = float(input("Amount to transfer: ").strip())
##    except ValueError:
##        print(" Invalid input.")
##        return
##    if to_acc == acc_no:
##        print(" Cannot transfer to the same account.")
##        return
##    if amt <= 0:
##        print(" Amount must be positive.")
##        return
##
##    conn = get_db(); cur = conn.cursor()
##    try:
##        conn.start_transaction()
##        cur.execute("SELECT balance, phone FROM accounts WHERE account_number=%s FOR UPDATE", (acc_no,))
##        src = cur.fetchone()
##        if not src:
##            raise ValueError("Source account not found")
##        src_bal, src_phone = src
##        if src_bal < amt:
##            raise ValueError("Insufficient balance")
##
##        cur.execute("SELECT phone FROM accounts WHERE account_number=%s FOR UPDATE", (to_acc,))
##        dst = cur.fetchone()
##        if not dst:
##            raise ValueError("Destination account not found")
##        dst_phone = dst[0]
##
##        cur.execute("UPDATE accounts SET balance = balance - %s WHERE account_number=%s", (amt, acc_no))
##        cur.execute("UPDATE accounts SET balance = balance + %s WHERE account_number=%s", (amt, to_acc))
##
##        cur.execute("INSERT INTO transactions (account_number, txn_type, amount, note, counterparty) VALUES (%s,'TRANSFER_OUT',%s,%s,%s)", (acc_no, amt, "Online transfer to another account", to_acc))
##        cur.execute("INSERT INTO transactions (account_number, txn_type, amount, note, counterparty) VALUES (%s,'TRANSFER_IN',%s,%s,%s)", (to_acc, amt, "Online transfer received", acc_no))
##
##        conn.commit()
##        atm_animate("Processing transfer")
##        print(" Transfer successful!")
##        send_sms(src_phone, f"Aathithyan Bank: ₹{amt:.2f} sent to {to_acc}. A/c {acc_no}.")
##        send_sms(dst_phone, f"Aathithyan Bank: ₹{amt:.2f} received from {acc_no}. A/c {to_acc}.")
##    except Exception as e:
##        conn.rollback(); print(" Transfer failed:", e)
##    finally:
##        cur.close(); conn.close()
##
##
### delete_account() remains in the file but is NOT reachable from menus
##def delete_account(acc_no: int):
##    # internal utility - not used in menus
##    conn = get_db(); cur = conn.cursor()
##    try:
##        cur.execute("DELETE FROM transactions WHERE account_number=%s", (acc_no,))
##        cur.execute("DELETE FROM accounts WHERE account_number=%s", (acc_no,))
##        conn.commit()
##    except Exception:
##        conn.rollback()
##    finally:
##        cur.close(); conn.close()
##
##
##def pin_change(acc_no: int):
##    new_pin = input("Enter NEW 4-digit PIN: ").strip()
##    if not (new_pin.isdigit() and len(new_pin) == 4):
##        print(" PIN must be 4 digits.")
##        return
##    conn = get_db(); cur = conn.cursor()
##    try:
##        cur.execute("UPDATE accounts SET pin=%s WHERE account_number=%s", (new_pin, acc_no))
##        cur.execute("INSERT INTO transactions (account_number, txn_type, amount, note) VALUES (%s,'PIN_CHANGE',0,%s)", (acc_no, "PIN changed via ATM"))
##        cur.execute("SELECT phone FROM accounts WHERE account_number=%s", (acc_no,))
##        phone = cur.fetchone()[0]
##        conn.commit()
##        atm_animate("Updating PIN")
##        print(" PIN updated.")
##        send_sms(phone, f"Aathithyan Bank: PIN for A/c {acc_no} has been changed.")
##    except Error as e:
##        conn.rollback(); print(" Failed:", e)
##    finally:
##        cur.close(); conn.close()
##
##
### ===============================
### ATM FLOWS
### ===============================
##
##def atm_auth() -> int | None:
##    print("\n=== ATM Login ===")
##    pin = input("Enter 4-digit PIN: ").strip()
##    if not (pin.isdigit() and len(pin) == 4):
##        print(" Invalid PIN format")
##        return None
##    conn = get_db(); cur = conn.cursor()
##    cur.execute("SELECT account_number FROM accounts WHERE pin=%s", (pin,))
##    rows = cur.fetchall()
##    cur.close(); conn.close()
##    if not rows:
##        print(" No account found with this PIN")
##        return None
##    if len(rows) > 1:
##        # Shouldn't happen when "one PIN per account" policy is enforced, but handle gracefully
##        print(" Multiple accounts use this PIN. Please enter account number to confirm.")
##        try:
##            acc_no = int(input("Enter Account Number: ").strip())
##        except ValueError:
##            print(" Invalid account number")
##            return None
##        for (a,) in rows:
##            if a == acc_no:
##                print(" Authenticated.")
##                return acc_no
##        print(" PIN matched but account number did not.")
##        return None
##    # exactly one match
##    acc_no = rows[0][0]
##    print(" Authenticated.")
##    return acc_no
##
##
##def atm_withdraw(acc_no: int):
##    try:
##        amt = float(input("Withdraw amount: ").strip())
##    except ValueError:
##        print(" Invalid amount")
##        return
##    if amt <= 0:
##        print(" Amount must be positive.")
##        return
##    conn = get_db(); cur = conn.cursor()
##    try:
##        conn.start_transaction()
##        cur.execute("SELECT balance, phone FROM accounts WHERE account_number=%s FOR UPDATE", (acc_no,))
##        row = cur.fetchone()
##        if not row:
##            raise ValueError("Account not found")
##        bal, phone = row
##        if bal < amt:
##            raise ValueError("Insufficient balance")
##        cur.execute("UPDATE accounts SET balance = balance - %s WHERE account_number=%s", (amt, acc_no))
##        cur.execute("INSERT INTO transactions (account_number, txn_type, amount, note) VALUES (%s,'WITHDRAW',%s,%s)", (acc_no, amt, "ATM cash withdrawal"))
##        conn.commit()
##        atm_animate("Processing transaction")
##        print(" Cash withdrawn.")
##        send_sms(phone, f"Aathithyan Bank: ₹{amt:.2f} withdrawn via ATM. A/c {acc_no}.")
##    except Exception as e:
##        conn.rollback(); print(" Withdrawal failed:", e)
##    finally:
##        cur.close(); conn.close()
##
##
##def atm_deposit(acc_no: int):
##    try:
##        amt = float(input("Deposit amount: ").strip())
##    except ValueError:
##        print(" Invalid amount")
##        return
##    if amt <= 0:
##        print(" Amount must be positive.")
##        return
##    conn = get_db(); cur = conn.cursor()
##    try:
##        cur.execute("UPDATE accounts SET balance = balance + %s WHERE account_number=%s", (amt, acc_no))
##        cur.execute("INSERT INTO transactions (account_number, txn_type, amount, note) VALUES (%s,'DEPOSIT',%s,%s)", (acc_no, amt, "ATM cash deposit"))
##        cur.execute("SELECT phone FROM accounts WHERE account_number=%s", (acc_no,))
##        phone = cur.fetchone()[0]
##        conn.commit()
##        atm_animate("Processing deposit")
##        print(" Cash deposited.")
##        send_sms(phone, f"Aathtihyan Bank: ₹{amt:.2f} deposited via ATM. A/c {acc_no}.")
##    except Error as e:
##        conn.rollback(); print(" Deposit failed:", e)
##    finally:
##        cur.close(); conn.close()
##
##
### ===============================
### MENUS
### ===============================
##
##def find_account_number():
##    print("\n=== Forgot Account Number ===")
##    conn = get_db(); cur = conn.cursor()
##    print("Search using:")
##    print("1) Phone Number")
##    print("2) Aadhaar Number")
##    print("3) PAN Number")
##    ch = input("Select: ").strip()
##    if ch == '1':
##        key = input("Enter Phone Number: ").strip()
##        cur.execute("SELECT account_number FROM accounts WHERE phone=%s", (key,))
##    elif ch == '2':
##        key = input("Enter Aadhaar Number: ").strip()
##        cur.execute("SELECT account_number FROM accounts WHERE aadhar=%s", (key,))
##    elif ch == '3':
##        key = input("Enter PAN Number: ").strip().upper()
##        cur.execute("SELECT account_number FROM accounts WHERE pan=%s", (key,))
##    else:
##        print("Invalid choice.")
##        cur.close(); conn.close(); return
##    row = cur.fetchone()
##    cur.close(); conn.close()
##    if row:
##        print(f" Your Account Number is: {row[0]}")
##    else:
##        print(" No matching account found.")
##
##def bank_portal():
##    while True:
##        print("\n==== Aathithyan BANK — Online Portal ====")
##        print("1) Create Account")
##        print("2) Login to Existing Account (PIN)")
##        print("3) Forgot Account Number")
##        print("4) Explore (Rates, Help, Branch Info)")
##        print("5) Back to Main")
##        ch = input("Select: ").strip()
##        if ch == '1':
##            create_account_flow()
##        elif ch == '2':
##            acc = login_flow()
##            if acc:
##                while True:
##                    print("-- Logged In --")
##                    print("1) View Balance")
##                    print("2) Deposit")
##                    print("3) Online Money Transfer")
##                    print("4) Change PIN")
##                    print("5) Logout")
##                    sub = input("Choose: ").strip()
##                    if sub == '1': view_balance(acc)
##                    elif sub == '2': deposit_money(acc)
##                    elif sub == '3': online_transfer(acc)
##                    elif sub == '4': pin_change(acc)
##                    elif sub == '5': break
##                    else: print("Invalid option")
##        elif ch == '3':
##            find_account_number()
##        elif ch == '4':
##            print("— Common Info —")
##            print("Savings Interest Rate: 3.00% p.a. (illustrative)")
##            print("NEFT/IMPS: Available 24x7")
##            print("Customer Care: 1800-000-000 (demo)")
##            print("Nearest Branch: Use branch locator on our website (demo)")
##        elif ch == '5':
##            return
##            return
##        else:
##            print("Invalid choice")
##
##
##def atm_portal():
##    acc = atm_auth()
##    if not acc:
##        return
##    while True:
##        print("\n==== Aathithyan BANK — ATM ====")
##        print("1) Cash Withdraw")
##        print("2) Deposit Cash")
##        print("3) Change PIN")
##        print("4) View Balance")
##        print("5) Exit ATM")
##        ch = input("Select: ").strip()
##        if ch == '1':
##            atm_withdraw(acc)
##        elif ch == '2':
##            atm_deposit(acc)
##        elif ch == '3':
##            pin_change(acc)
##        elif ch == '4':
##            view_balance(acc)
##        elif ch == '5':
##            break
##        else:
##            print("Invalid choice")
##
##
##def main():
##    init_schema()
##    print("\n==============================")
##    print(" Welcome to Aathithyan Bank ")
##    print("==============================")
##    while True:
##        print("\nMain Menu:")
##        print("1) Bank Account")
##        print("2) ATM")
##        print("3) Exit")
##        choice = input("Select: ").strip()
##        if choice == '1':
##            bank_portal()
##        elif choice == '2':
##            atm_portal()
##        elif choice == '3':
##            print("Thank you for banking with us. ✨")
##            break
##        else:
##            print("Invalid choice")
##
##
##if __name__ == '__main__':
##    main()
##
##
## 
##
## 
# bank_styled.py
import mysql.connector
from mysql.connector import Error
import requests
from datetime import datetime, date
import random
import os
import time
import sys

# UI libs
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.align import Align
from rich.prompt import Prompt, IntPrompt
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.text import Text
from rich import box

# ===============================
# CONFIG (unchanged)
# ===============================
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "Aathi2004@#",   # <-- your MySQL root password
    "database": "aathi_bank"
}

SECRETS_FILE = "fast2sms_key.txt"
FAST2SMS_ENDPOINT = "https://www.fast2sms.com/dev/bulkV2"

# ===============================
# GLOBALS: Console + Theme manager
# ===============================
console = Console()

PALETTES = {
    "A": {  # Neon Bank ATM Look
        "accent": "bright_green",
        "title": "bright_green",
        "info": "white",
        "warn": "yellow",
        "err": "bold red",
        "success": "bold bright_green"
    },
    "B": {  # Modern Blue Bank Theme
        "accent": "cyan",
        "title": "cyan",
        "info": "white",
        "warn": "yellow",
        "err": "red",
        "success": "bold cyan"
    },
    "C": {  # Full Color Rich UI
        "accent": "magenta",
        "title": "magenta",
        "info": "white",
        "warn": "orange1",
        "err": "bold red",
        "success": "bold magenta"
    },
    "D": {  # Minimal Soft Color
        "accent": "bright_white",
        "title": "bright_white",
        "info": "white",
        "warn": "bright_yellow",
        "err": "red",
        "success": "bold bright_white"
    }
}
# default palette (will update on user choice)
PALETTE = PALETTES["B"]

def set_palette(key: str):
    global PALETTE
    key = key.upper()
    if key in PALETTES:
        PALETTE = PALETTES[key]
    else:
        PALETTE = PALETTES["B"]

def styled_panel(text: str, title: str = "", width: int | None = None):
    return Panel(text, title=title, title_align="left", border_style=PALETTE["accent"], width=width)

def styled_print(msg: str, style: str | None = None, justify: str = "left"):
    console.print(msg, style=(style or PALETTE["info"]), justify=justify)

def show_header(app_title: str = "Aathithyan BANK"):
    header = Text(app_title, style=PALETTE["title"], justify="center")
    console.rule(header)

# ===============================
# DB Helpers (unchanged logic)
# ===============================
def get_db():
    return mysql.connector.connect(**DB_CONFIG)

def init_schema():
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
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
        );
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS transactions (
            id BIGINT PRIMARY KEY AUTO_INCREMENT,
            account_number BIGINT NOT NULL,
            txn_type ENUM('DEPOSIT','WITHDRAW','TRANSFER_OUT','TRANSFER_IN','ACCOUNT_CREATE','PIN_CHANGE','ACCOUNT_DELETE') NOT NULL,
            amount DOUBLE NOT NULL,
            note VARCHAR(255),
            counterparty BIGINT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (account_number) REFERENCES accounts(account_number)
        );
        """
    )
    conn.commit()
    cur.close()
    conn.close()

# ===============================
# Utilities (same behavior; nicer messages)
# ===============================
def read_fast2sms_key() -> str:
    if os.path.exists(SECRETS_FILE):
        try:
            with open(SECRETS_FILE, 'r', encoding='utf-8') as f:
                key = f.read().strip()
                if key:
                    return key
        except Exception:
            pass
    console.print("[bold yellow]Fast2SMS API key not found.[/bold yellow]")
    key = Prompt.ask("Paste Fast2SMS API Key (it will be stored locally)", password=False).strip()
    with open(SECRETS_FILE, 'w', encoding='utf-8') as f:
        f.write(key)
    return key

def send_sms(mobile: str, message: str):
    try:
        api_key = read_fast2sms_key()
        headers = {'authorization': api_key}
        data = {
            'route': 'v3',
            'sender_id': 'TXTIND',
            'message': message,
            'language': 'english',
            'flash': 0,
            'numbers': mobile
        }
        resp = requests.post(FAST2SMS_ENDPOINT, headers=headers, data=data, timeout=10)
        if resp.status_code != 200:
            console.print(f"[{PALETTE['warn']}](SMS) Non-200 response: {resp.status_code}[/]")
    except Exception as e:
        console.print(f"[{PALETTE['warn']}](SMS) Failed to send: {e}[/]")

def generate_account_number(cur) -> int:
    while True:
        acc = random.randint(2000000000, 9999999999)  # 10-digit
        cur.execute("SELECT 1 FROM accounts WHERE account_number=%s", (acc,))
        if not cur.fetchone():
            return acc

def calc_age(dob: date) -> int:
    today = date.today()
    years = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    return years

def require_min_deposit(amount: float):
    if amount < 1000:
        raise ValueError("Minimum initial deposit is ₹1000")

def atm_animate(msg="Processing"):
    # rich spinner for a short friendly delay
    with Progress(SpinnerColumn(style=PALETTE["accent"]), TextColumn("[progress.description]{task.description}")) as progress:
        task = progress.add_task(msg, total=None)
        time.sleep(0.9)
        progress.remove_task(task)

# ===============================
# BANK FLOWS (logic preserved)
# ===============================
def create_account_flow():
    console.print(styled_panel("Create New Bank Account", title="🟢 New Account"))
    name = Prompt.ask("Full Name").strip()
    dob_str = Prompt.ask("Date of Birth (YYYY-MM-DD)").strip()
    phone = Prompt.ask("Mobile Number (+91XXXXXXXXXX or 10 digits)").strip()
    aadhar = Prompt.ask("Aadhar (12 digits)").strip()
    pan = Prompt.ask("PAN (10 chars, e.g. ABCDE1234F)").strip().upper()
    pin = Prompt.ask("Set 4-digit ATM PIN").strip()

    try:
        dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
    except ValueError:
        console.print(f"[{PALETTE['err']}]Invalid DOB format.[/]")
        return

    age = calc_age(dob)
    if age < 18:
        console.print(f"[{PALETTE['err']}]Only users 18+ can create an account.[/]")
        return

    if not (pin.isdigit() and len(pin) == 4):
        console.print(f"[{PALETTE['err']}]PIN must be 4 digits.[/]")
        return

    try:
        init_amt = float(Prompt.ask("Initial Deposit (min ₹1000)"))
        require_min_deposit(init_amt)
    except Exception as e:
        console.print(f"[{PALETTE['err']}] {e}[/]")
        return

    conn = get_db()
    cur = conn.cursor()
    try:
        acc_no = generate_account_number(cur)
        cur.execute(
            """
            INSERT INTO accounts (account_number, name, dob, phone, aadhar, pan, pin, balance)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (acc_no, name, dob, phone, aadhar, pan, pin, init_amt)
        )
        cur.execute(
            """
            INSERT INTO transactions (account_number, txn_type, amount, note)
            VALUES (%s,'ACCOUNT_CREATE',%s,%s)
            """,
            (acc_no, init_amt, "Initial deposit on account creation")
        )
        conn.commit()
        console.print(Panel(f"[{PALETTE['success']}]Account created![/]\nYour Account Number: [bold]{acc_no}[/]", border_style=PALETTE["accent"]))
        send_sms(phone, f"Aathithyan Bank: Account {acc_no} created successfully. Opening balance ₹{init_amt:.2f}.")
    except Error as e:
        conn.rollback()
        console.print(f"[{PALETTE['err']}]Failed to create account: {e}[/]")
    finally:
        cur.close(); conn.close()

def login_flow() -> int | None:
    console.print(styled_panel("Login (Account Number + PIN)", title="🔐 Login"))
    try:
        acc_no = int(Prompt.ask("Account Number").strip())
    except ValueError:
        console.print(f"[{PALETTE['err']}]Invalid account number[/]")
        return None
    pin = Prompt.ask("ATM PIN (4 digits)").strip()
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT account_number FROM accounts WHERE account_number=%s AND pin=%s", (acc_no, pin))
    row = cur.fetchone()
    cur.close(); conn.close()
    if row:
        console.print(f"[{PALETTE['success']}]Login successful![/]")
        return acc_no
    console.print(f"[{PALETTE['err']}]Wrong account number or PIN[/]")
    return None

def view_balance(acc_no: int):
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT balance, phone FROM accounts WHERE account_number=%s", (acc_no,))
    row = cur.fetchone()
    cur.close(); conn.close()
    if row:
        bal, _ = row
        atm_animate("Fetching balance")
        console.print(Panel(f"Balance: ₹{bal:.2f}", title="💰 Account Balance", border_style=PALETTE["accent"]))

def deposit_money(acc_no: int):
    try:
        amt = float(Prompt.ask("Amount to deposit").strip())
        if amt <= 0:
            console.print(f"[{PALETTE['err']}]Amount must be positive.[/]")
            return
    except ValueError:
        console.print(f"[{PALETTE['err']}]Invalid amount[/]")
        return
    conn = get_db(); cur = conn.cursor()
    try:
        cur.execute("UPDATE accounts SET balance = balance + %s WHERE account_number=%s", (amt, acc_no))
        cur.execute("INSERT INTO transactions (account_number, txn_type, amount, note) VALUES (%s,'DEPOSIT',%s,%s)", (acc_no, amt, "Online deposit"))
        cur.execute("SELECT phone FROM accounts WHERE account_number=%s", (acc_no,))
        phone = cur.fetchone()[0]
        conn.commit()
        atm_animate("Processing deposit")
        console.print(f"[{PALETTE['success']}]Deposit successful![/]")
        send_sms(phone, f"Aathithyan Bank: ₹{amt:.2f} deposited. A/c {acc_no}.")
    except Error as e:
        conn.rollback(); console.print(f"[{PALETTE['err']}]Deposit failed: {e}[/]")
    finally:
        cur.close(); conn.close()

def online_transfer(acc_no: int):
    console.print(styled_panel("Online Transfer (Account → Account)", title="🔁 Transfer"))
    try:
        to_acc = int(Prompt.ask("Receiver Account Number").strip())
        amt = float(Prompt.ask("Amount to transfer").strip())
    except ValueError:
        console.print(f"[{PALETTE['err']}]Invalid input.[/]")
        return
    if to_acc == acc_no:
        console.print(f"[{PALETTE['err']}]Cannot transfer to the same account.[/]")
        return
    if amt <= 0:
        console.print(f"[{PALETTE['err']}]Amount must be positive.[/]")
        return

    conn = get_db(); cur = conn.cursor()
    try:
        conn.start_transaction()
        cur.execute("SELECT balance, phone FROM accounts WHERE account_number=%s FOR UPDATE", (acc_no,))
        src = cur.fetchone()
        if not src:
            raise ValueError("Source account not found")
        src_bal, src_phone = src
        if src_bal < amt:
            raise ValueError("Insufficient balance")

        cur.execute("SELECT phone FROM accounts WHERE account_number=%s FOR UPDATE", (to_acc,))
        dst = cur.fetchone()
        if not dst:
            raise ValueError("Destination account not found")
        dst_phone = dst[0]

        cur.execute("UPDATE accounts SET balance = balance - %s WHERE account_number=%s", (amt, acc_no))
        cur.execute("UPDATE accounts SET balance = balance + %s WHERE account_number=%s", (amt, to_acc))

        cur.execute("INSERT INTO transactions (account_number, txn_type, amount, note, counterparty) VALUES (%s,'TRANSFER_OUT',%s,%s,%s)", (acc_no, amt, "Online transfer to another account", to_acc))
        cur.execute("INSERT INTO transactions (account_number, txn_type, amount, note, counterparty) VALUES (%s,'TRANSFER_IN',%s,%s,%s)", (to_acc, amt, "Online transfer received", acc_no))

        conn.commit()
        atm_animate("Processing transfer")
        console.print(f"[{PALETTE['success']}]Transfer successful![/]")
        send_sms(src_phone, f"Aathithyan Bank: ₹{amt:.2f} sent to {to_acc}. A/c {acc_no}.")
        send_sms(dst_phone, f"Aathithyan Bank: ₹{amt:.2f} received from {acc_no}. A/c {to_acc}.")
    except Exception as e:
        conn.rollback(); console.print(f"[{PALETTE['err']}]Transfer failed: {e}[/]")
    finally:
        cur.close(); conn.close()

def delete_account(acc_no: int):
    conn = get_db(); cur = conn.cursor()
    try:
        cur.execute("DELETE FROM transactions WHERE account_number=%s", (acc_no,))
        cur.execute("DELETE FROM accounts WHERE account_number=%s", (acc_no,))
        conn.commit()
    except Exception:
        conn.rollback()
    finally:
        cur.close(); conn.close()

def pin_change(acc_no: int):
    new_pin = Prompt.ask("Enter NEW 4-digit PIN").strip()
    if not (new_pin.isdigit() and len(new_pin) == 4):
        console.print(f"[{PALETTE['err']}]PIN must be 4 digits.[/]")
        return
    conn = get_db(); cur = conn.cursor()
    try:
        cur.execute("UPDATE accounts SET pin=%s WHERE account_number=%s", (new_pin, acc_no))
        cur.execute("INSERT INTO transactions (account_number, txn_type, amount, note) VALUES (%s,'PIN_CHANGE',0,%s)", (acc_no, "PIN changed via ATM"))
        cur.execute("SELECT phone FROM accounts WHERE account_number=%s", (acc_no,))
        phone = cur.fetchone()[0]
        conn.commit()
        atm_animate("Updating PIN")
        console.print(f"[{PALETTE['success']}]PIN updated.[/]")
        send_sms(phone, f"Aathithyan Bank: PIN for A/c {acc_no} has been changed.")
    except Error as e:
        conn.rollback(); console.print(f"[{PALETTE['err']}]Failed: {e}[/]")
    finally:
        cur.close(); conn.close()

# ===============================
# ATM FLOWS (preserved)
# ===============================
def atm_auth() -> int | None:
    console.print(styled_panel("ATM Login", title="🏧 ATM"))
    pin = Prompt.ask("Enter 4-digit PIN").strip()
    if not (pin.isdigit() and len(pin) == 4):
        console.print(f"[{PALETTE['err']}]Invalid PIN format[/]")
        return None
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT account_number FROM accounts WHERE pin=%s", (pin,))
    rows = cur.fetchall()
    cur.close(); conn.close()
    if not rows:
        console.print(f"[{PALETTE['err']}]No account found with this PIN[/]")
        return None
    if len(rows) > 1:
        console.print(f"[{PALETTE['warn']}]Multiple accounts use this PIN. Please enter account number to confirm.[/]")
        try:
            acc_no = int(Prompt.ask("Enter Account Number").strip())
        except ValueError:
            console.print(f"[{PALETTE['err']}]Invalid account number[/]")
            return None
        for (a,) in rows:
            if a == acc_no:
                console.print(f"[{PALETTE['success']}]Authenticated.[/]")
                return acc_no
        console.print(f"[{PALETTE['err']}]PIN matched but account number did not.[/]")
        return None
    acc_no = rows[0][0]
    console.print(f"[{PALETTE['success']}]Authenticated.[/]")
    return acc_no

def atm_withdraw(acc_no: int):
    try:
        amt = float(Prompt.ask("Withdraw amount").strip())
    except ValueError:
        console.print(f"[{PALETTE['err']}]Invalid amount[/]")
        return
    if amt <= 0:
        console.print(f"[{PALETTE['err']}]Amount must be positive.[/]")
        return
    conn = get_db(); cur = conn.cursor()
    try:
        conn.start_transaction()
        cur.execute("SELECT balance, phone FROM accounts WHERE account_number=%s FOR UPDATE", (acc_no,))
        row = cur.fetchone()
        if not row:
            raise ValueError("Account not found")
        bal, phone = row
        if bal < amt:
            raise ValueError("Insufficient balance")
        cur.execute("UPDATE accounts SET balance = balance - %s WHERE account_number=%s", (amt, acc_no))
        cur.execute("INSERT INTO transactions (account_number, txn_type, amount, note) VALUES (%s,'WITHDRAW',%s,%s)", (acc_no, amt, "ATM cash withdrawal"))
        conn.commit()
        atm_animate("Processing transaction")
        console.print(f"[{PALETTE['success']}]Cash withdrawn.[/]")
        send_sms(phone, f"Aathithyan Bank: ₹{amt:.2f} withdrawn via ATM. A/c {acc_no}.")
    except Exception as e:
        conn.rollback(); console.print(f"[{PALETTE['err']}]Withdrawal failed: {e}[/]")
    finally:
        cur.close(); conn.close()

def atm_deposit(acc_no: int):
    try:
        amt = float(Prompt.ask("Deposit amount").strip())
    except ValueError:
        console.print(f"[{PALETTE['err']}]Invalid amount[/]")
        return
    if amt <= 0:
        console.print(f"[{PALETTE['err']}]Amount must be positive.[/]")
        return
    conn = get_db(); cur = conn.cursor()
    try:
        cur.execute("UPDATE accounts SET balance = balance + %s WHERE account_number=%s", (amt, acc_no))
        cur.execute("INSERT INTO transactions (account_number, txn_type, amount, note) VALUES (%s,'DEPOSIT',%s,%s)", (acc_no, amt, "ATM cash deposit"))
        cur.execute("SELECT phone FROM accounts WHERE account_number=%s", (acc_no,))
        phone = cur.fetchone()[0]
        conn.commit()
        atm_animate("Processing deposit")
        console.print(f"[{PALETTE['success']}]Cash deposited.[/]")
        send_sms(phone, f"Aathithyan Bank: ₹{amt:.2f} deposited via ATM. A/c {acc_no}.")
    except Error as e:
        conn.rollback(); console.print(f"[{PALETTE['err']}]Deposit failed: {e}[/]")
    finally:
        cur.close(); conn.close()

# ===============================
# MENUS (interactive and styled)
# ===============================
def find_account_number():
    console.print(styled_panel("Forgot Account Number", title="🔎 Find Account"))
    conn = get_db(); cur = conn.cursor()
    console.print("Search using:\n1) Phone Number\n2) Aadhaar Number\n3) PAN Number", style=PALETTE["info"])
    ch = Prompt.ask("Select", choices=["1","2","3"], default="1")
    if ch == '1':
        key = Prompt.ask("Enter Phone Number").strip()
        cur.execute("SELECT account_number FROM accounts WHERE phone=%s", (key,))
    elif ch == '2':
        key = Prompt.ask("Enter Aadhaar Number").strip()
        cur.execute("SELECT account_number FROM accounts WHERE aadhar=%s", (key,))
    elif ch == '3':
        key = Prompt.ask("Enter PAN Number").strip().upper()
        cur.execute("SELECT account_number FROM accounts WHERE pan=%s", (key,))
    row = cur.fetchone()
    cur.close(); conn.close()
    if row:
        console.print(Panel(f"Your Account Number is: [bold]{row[0]}[/]", border_style=PALETTE["accent"]))
    else:
        console.print(f"[{PALETTE['warn']}]No matching account found.[/]")

def bank_portal():
    while True:
        console.print(Panel("Aathithyan BANK — Online Portal", title="🏦 Bank Portal", border_style=PALETTE["accent"]))
        console.print("1) Create Account\n2) Login to Existing Account (PIN)\n3) Forgot Account Number\n4) Explore (Rates, Help, Branch Info)\n5) Back to Main", style=PALETTE["info"])
        ch = Prompt.ask("Select", choices=["1","2","3","4","5"], default="5")
        if ch == '1':
            create_account_flow()
        elif ch == '2':
            acc = login_flow()
            if acc:
                while True:
                    console.print(Panel("-- Logged In --", border_style=PALETTE["accent"]))
                    console.print("1) View Balance\n2) Deposit\n3) Online Money Transfer\n4) Change PIN\n5) Logout", style=PALETTE["info"])
                    sub = Prompt.ask("Choose", choices=["1","2","3","4","5"], default="5")
                    if sub == '1': view_balance(acc)
                    elif sub == '2': deposit_money(acc)
                    elif sub == '3': online_transfer(acc)
                    elif sub == '4': pin_change(acc)
                    elif sub == '5': break
                    else: console.print(f"[{PALETTE['err']}]Invalid option[/]")
        elif ch == '3':
            find_account_number()
        elif ch == '4':
            console.print(Panel(
                "— Common Info —\nSavings Interest Rate: 3.00% p.a. (illustrative)\nNEFT/IMPS: Available 24x7\nCustomer Care: 1800-000-000 (demo)\nNearest Branch: Use branch locator on our website (demo)",
                title="ℹ️ Info",
                border_style=PALETTE["accent"]
            ))
        elif ch == '5':
            return
        else:
            console.print(f"[{PALETTE['err']}]Invalid choice[/]")

def atm_portal():
    acc = atm_auth()
    if not acc:
        return
    while True:
        console.print(Panel("Aathithyan BANK — ATM", title="🏧 ATM", border_style=PALETTE["accent"]))
        console.print("1) Cash Withdraw\n2) Deposit Cash\n3) Change PIN\n4) View Balance\n5) Exit ATM", style=PALETTE["info"])
        ch = Prompt.ask("Select", choices=["1","2","3","4","5"], default="5")
        if ch == '1': atm_withdraw(acc)
        elif ch == '2': atm_deposit(acc)
        elif ch == '3': pin_change(acc)
        elif ch == '4': view_balance(acc)
        elif ch == '5': break
        else: console.print(f"[{PALETTE['err']}]Invalid choice[/]")

# ===============================
# ENTRY: Main with theme choice
# ===============================
def main():
    console.clear()
    console.print(Panel("Welcome to Aathithyan Bank", style=PALETTE["title"], border_style=PALETTE["accent"]))
    console.print("Choose UI Theme / Style:", style=PALETTE["info"])
    console.print("A) Neon Bank ATM Look\nB) Modern Blue Bank Theme\nC) Full Color Rich UI\nD) Minimal Soft Color\n", style=PALETTE["info"])
    theme = Prompt.ask("Pick A / B / C / D (or press Enter for B)", choices=["A","B","C","D",""], default="B").strip().upper()
    if theme == "": theme = "B"
    set_palette(theme)
    init_schema()
    show_header("✨ Aathithyan BANK ✨")
    while True:
        console.print("\nMain Menu:", style=PALETTE["info"])
        console.print("1) Bank Account\n2) ATM\n3) Exit", style=PALETTE["info"])
        choice = Prompt.ask("Select", choices=["1","2","3"], default="3")
        if choice == '1':
            bank_portal()
        elif choice == '2':
            atm_portal()
        elif choice == '3':
            console.print(Panel("Thank you for banking with us. ✨", border_style=PALETTE["accent"]))
            break
        else:
            console.print(f"[{PALETTE['err']}]Invalid choice[/]")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Goodbye.[/]")
        sys.exit(0)
