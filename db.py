import sqlite3
import os
from datetime import date

DB_PATH = os.environ.get("RAILWAY_DATABASE_PATH", "aw_portal.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name1 TEXT NOT NULL,
            dob1 TEXT,
            ssn_last4_1 TEXT,
            name2 TEXT,
            dob2 TEXT,
            ssn_last4_2 TEXT,
            monthly_salary REAL DEFAULT 0,
            monthly_expense_budget REAL DEFAULT 0,
            deductible_car REAL DEFAULT 0,
            deductible_home REAL DEFAULT 0,
            deductible_health REAL DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            last_report_date TEXT
        );

        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
            owner TEXT NOT NULL,
            category TEXT NOT NULL,
            account_type TEXT NOT NULL,
            account_last4 TEXT,
            interest_rate REAL,
            property_address TEXT
        );

        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
            report_date TEXT NOT NULL,
            quarter TEXT NOT NULL,
            private_reserve_balance REAL DEFAULT 0,
            schwab_balance REAL DEFAULT 0,
            zillow_value REAL DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS report_balances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
            account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
            balance REAL DEFAULT 0,
            cash_balance REAL DEFAULT 0
        );
    """)
    conn.commit()
    conn.close()


# ── Clients ──────────────────────────────────────────────────────────────────

def get_all_clients():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM clients ORDER BY name1"
    ).fetchall()
    conn.close()
    return rows


def get_client(client_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM clients WHERE id = ?", (client_id,)).fetchone()
    conn.close()
    return row


def create_client(data):
    conn = get_db()
    cur = conn.execute(
        """INSERT INTO clients
           (name1, dob1, ssn_last4_1, name2, dob2, ssn_last4_2,
            monthly_salary, monthly_expense_budget,
            deductible_car, deductible_home, deductible_health)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (
            data["name1"], data.get("dob1"), data.get("ssn_last4_1"),
            data.get("name2") or None, data.get("dob2") or None, data.get("ssn_last4_2") or None,
            float(data.get("monthly_salary") or 0),
            float(data.get("monthly_expense_budget") or 0),
            float(data.get("deductible_car") or 0),
            float(data.get("deductible_home") or 0),
            float(data.get("deductible_health") or 0),
        ),
    )
    client_id = cur.lastrowid
    conn.commit()
    conn.close()
    return client_id


def update_client(client_id, data):
    conn = get_db()
    conn.execute(
        """UPDATE clients SET
           name1=?, dob1=?, ssn_last4_1=?,
           name2=?, dob2=?, ssn_last4_2=?,
           monthly_salary=?, monthly_expense_budget=?,
           deductible_car=?, deductible_home=?, deductible_health=?
           WHERE id=?""",
        (
            data["name1"], data.get("dob1"), data.get("ssn_last4_1"),
            data.get("name2") or None, data.get("dob2") or None, data.get("ssn_last4_2") or None,
            float(data.get("monthly_salary") or 0),
            float(data.get("monthly_expense_budget") or 0),
            float(data.get("deductible_car") or 0),
            float(data.get("deductible_home") or 0),
            float(data.get("deductible_health") or 0),
            client_id,
        ),
    )
    conn.commit()
    conn.close()


def delete_client(client_id):
    conn = get_db()
    conn.execute("DELETE FROM clients WHERE id=?", (client_id,))
    conn.commit()
    conn.close()


# ── Accounts ─────────────────────────────────────────────────────────────────

def get_accounts(client_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM accounts WHERE client_id=? ORDER BY category, owner, account_type",
        (client_id,),
    ).fetchall()
    conn.close()
    return rows


def replace_accounts(client_id, accounts):
    """Delete all existing accounts for client and insert new list."""
    conn = get_db()
    conn.execute("DELETE FROM accounts WHERE client_id=?", (client_id,))
    for acc in accounts:
        if not acc.get("account_type"):
            continue
        conn.execute(
            """INSERT INTO accounts
               (client_id, owner, category, account_type, account_last4, interest_rate, property_address)
               VALUES (?,?,?,?,?,?,?)""",
            (
                client_id,
                acc["owner"],
                acc["category"],
                acc["account_type"],
                acc.get("account_last4") or None,
                float(acc["interest_rate"]) if acc.get("interest_rate") else None,
                acc.get("property_address") or None,
            ),
        )
    conn.commit()
    conn.close()


# ── Reports ───────────────────────────────────────────────────────────────────

def get_reports_for_client(client_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM reports WHERE client_id=? ORDER BY report_date DESC",
        (client_id,),
    ).fetchall()
    conn.close()
    return rows


def get_report(report_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM reports WHERE id=?", (report_id,)).fetchone()
    conn.close()
    return row


def get_last_report(client_id):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM reports WHERE client_id=? ORDER BY report_date DESC LIMIT 1",
        (client_id,),
    ).fetchone()
    conn.close()
    return row


def create_report(client_id, data, balances):
    today = data.get("report_date") or date.today().isoformat()
    quarter = data.get("quarter") or _to_quarter(today)
    conn = get_db()
    cur = conn.execute(
        """INSERT INTO reports
           (client_id, report_date, quarter, private_reserve_balance, schwab_balance, zillow_value)
           VALUES (?,?,?,?,?,?)""",
        (
            client_id, today, quarter,
            float(data.get("private_reserve_balance") or 0),
            float(data.get("schwab_balance") or 0),
            float(data.get("zillow_value") or 0),
        ),
    )
    report_id = cur.lastrowid
    for account_id, vals in balances.items():
        conn.execute(
            "INSERT INTO report_balances (report_id, account_id, balance, cash_balance) VALUES (?,?,?,?)",
            (report_id, account_id, float(vals.get("balance") or 0), float(vals.get("cash_balance") or 0)),
        )
    conn.execute(
        "UPDATE clients SET last_report_date=? WHERE id=?", (today, client_id)
    )
    conn.commit()
    conn.close()
    return report_id


def get_report_balances(report_id):
    conn = get_db()
    rows = conn.execute(
        """SELECT rb.*, a.owner, a.category, a.account_type, a.account_last4,
                  a.interest_rate, a.property_address
           FROM report_balances rb
           JOIN accounts a ON a.id = rb.account_id
           WHERE rb.report_id=?""",
        (report_id,),
    ).fetchall()
    conn.close()
    return rows


def get_last_report_balances(client_id):
    """Returns {account_id: {balance, cash_balance}} for the most recent report."""
    last = get_last_report(client_id)
    if not last:
        return {}
    rows = get_report_balances(last["id"])
    return {r["account_id"]: {"balance": r["balance"], "cash_balance": r["cash_balance"]} for r in rows}


# ── Calculations ──────────────────────────────────────────────────────────────

def compute_sacs(client, report):
    salary = client["monthly_salary"]
    budget = client["monthly_expense_budget"]
    excess = salary - budget
    pr_target = (budget * 6) + client["deductible_car"] + client["deductible_home"] + client["deductible_health"]
    return {
        "inflow": salary,
        "outflow": budget,
        "excess": excess,
        "pr_balance": report["private_reserve_balance"],
        "pr_target": pr_target,
        "schwab_balance": report["schwab_balance"],
        "floor": 1000,
    }


def compute_tcc(client, report, balances):
    c1_ret = sum(b["balance"] for b in balances if b["owner"] == "client1" and b["category"] == "retirement")
    c2_ret = sum(b["balance"] for b in balances if b["owner"] == "client2" and b["category"] == "retirement")
    non_ret = sum(b["balance"] for b in balances if b["category"] == "non_retirement")
    liab = sum(b["balance"] for b in balances if b["category"] == "liability")
    zillow = report["zillow_value"]
    grand_total = c1_ret + c2_ret + non_ret + zillow
    return {
        "client1_retirement_total": c1_ret,
        "client2_retirement_total": c2_ret,
        "non_retirement_total": non_ret,
        "liabilities_total": liab,
        "zillow_value": zillow,
        "grand_total": grand_total,
    }


def _to_quarter(date_str):
    try:
        m = int(date_str[5:7])
        y = date_str[:4]
        q = (m - 1) // 3 + 1
        return f"Q{q} {y}"
    except Exception:
        return ""


def calc_age(dob_str):
    if not dob_str:
        return None
    try:
        born = date.fromisoformat(dob_str)
        today = date.today()
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    except Exception:
        return None


def seed_demo_data():
    """Insert the demo client on first boot if the database is empty."""
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM clients").fetchone()[0]
    conn.close()
    if count > 0:
        return

    cid = create_client({
        "name1": "John Smith", "dob1": "1975-03-15", "ssn_last4_1": "4321",
        "name2": "Jane Smith", "dob2": "1978-07-22", "ssn_last4_2": "8765",
        "monthly_salary": 15000, "monthly_expense_budget": 11000,
        "deductible_car": 1000, "deductible_home": 2000, "deductible_health": 1000,
    })
    replace_accounts(cid, [
        {"owner": "client1", "category": "retirement",     "account_type": "IRA",             "account_last4": "1234", "interest_rate": "", "property_address": ""},
        {"owner": "client1", "category": "retirement",     "account_type": "Roth IRA",        "account_last4": "5678", "interest_rate": "", "property_address": ""},
        {"owner": "client2", "category": "retirement",     "account_type": "401k",            "account_last4": "9012", "interest_rate": "", "property_address": ""},
        {"owner": "client2", "category": "retirement",     "account_type": "Pension",         "account_last4": "3456", "interest_rate": "", "property_address": ""},
        {"owner": "joint",   "category": "non_retirement", "account_type": "Schwab Brokerage","account_last4": "7890", "interest_rate": "", "property_address": ""},
        {"owner": "joint",   "category": "trust",          "account_type": "Family Trust",    "account_last4": "",     "interest_rate": "", "property_address": "123 Oak Lane, Atlanta GA 30301"},
        {"owner": "joint",   "category": "liability",      "account_type": "Mortgage",        "account_last4": "2345", "interest_rate": 3.75, "property_address": ""},
        {"owner": "joint",   "category": "liability",      "account_type": "Auto Loan",       "account_last4": "6789", "interest_rate": 5.99, "property_address": ""},
    ])
    accs = get_accounts(cid)
    bal_map = {
        "IRA": 18000, "Roth IRA": 50000, "401k": 42000, "Pension": 185000,
        "Schwab Brokerage": 42000, "Family Trust": 0, "Mortgage": 15000, "Auto Loan": 26000,
    }
    balances = {
        a["id"]: {
            "balance": bal_map.get(a["account_type"], 0),
            "cash_balance": 5000 if a["account_type"] == "Schwab Brokerage" else 0,
        }
        for a in accs
    }
    create_report(cid, {
        "report_date": "2026-05-20", "quarter": "Q2 2026",
        "private_reserve_balance": 75000, "schwab_balance": 50000, "zillow_value": 450000,
    }, balances)
