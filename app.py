import io
from datetime import date
from flask import Flask, render_template, redirect, url_for, request, send_file, flash
import db
from pdf_sacs import generate_sacs_pdf
from pdf_tcc import generate_tcc_pdf

app = Flask(__name__)
app.secret_key = "aw-portal-secret-2026"

db.init_db()
db.seed_demo_data()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_accounts_from_form(form):
    """Extract dynamic account rows submitted from client_form."""
    accounts = []
    indices = set()
    for key in form:
        if key.startswith("acc_type_"):
            indices.add(key.split("_")[-1])
    for i in sorted(indices, key=lambda x: int(x)):
        acc_type = form.get(f"acc_type_{i}", "").strip()
        if not acc_type:
            continue
        accounts.append({
            "owner": form.get(f"acc_owner_{i}", "joint"),
            "category": form.get(f"acc_category_{i}", "non_retirement"),
            "account_type": acc_type,
            "account_last4": form.get(f"acc_last4_{i}", "").strip(),
            "interest_rate": form.get(f"acc_rate_{i}", "").strip(),
            "property_address": form.get(f"acc_address_{i}", "").strip(),
        })
    return accounts


# ── Dashboard ─────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return redirect(url_for("clients"))


@app.route("/clients")
def clients():
    all_clients = db.get_all_clients()
    return render_template("clients.html", clients=all_clients)


# ── Client CRUD ───────────────────────────────────────────────────────────────

@app.route("/clients/new", methods=["GET", "POST"])
def client_new():
    if request.method == "POST":
        client_id = db.create_client(request.form)
        accounts = _parse_accounts_from_form(request.form)
        db.replace_accounts(client_id, accounts)
        flash("Client added successfully.", "success")
        return redirect(url_for("clients"))
    return render_template("client_form.html", client=None, accounts=[], action="new")


@app.route("/clients/<int:client_id>/edit", methods=["GET", "POST"])
def client_edit(client_id):
    client = db.get_client(client_id)
    if not client:
        flash("Client not found.", "error")
        return redirect(url_for("clients"))
    if request.method == "POST":
        db.update_client(client_id, request.form)
        accounts = _parse_accounts_from_form(request.form)
        db.replace_accounts(client_id, accounts)
        flash("Client updated.", "success")
        return redirect(url_for("clients"))
    accounts = db.get_accounts(client_id)
    return render_template("client_form.html", client=client, accounts=accounts, action="edit")


@app.route("/clients/<int:client_id>/delete", methods=["POST"])
def client_delete(client_id):
    db.delete_client(client_id)
    flash("Client deleted.", "success")
    return redirect(url_for("clients"))


# ── Reports ───────────────────────────────────────────────────────────────────

@app.route("/clients/<int:client_id>/report/new", methods=["GET", "POST"])
def report_new(client_id):
    client = db.get_client(client_id)
    if not client:
        return redirect(url_for("clients"))
    accounts = db.get_accounts(client_id)
    last_report = db.get_last_report(client_id)
    last_balances = db.get_last_report_balances(client_id)

    if request.method == "POST":
        balances = {}
        for acc in accounts:
            aid = acc["id"]
            balances[aid] = {
                "balance": request.form.get(f"bal_{aid}", 0),
                "cash_balance": request.form.get(f"cash_{aid}", 0),
            }
        report_id = db.create_report(client_id, request.form, balances)
        flash("Report saved.", "success")
        return redirect(url_for("report_detail", report_id=report_id))

    today = date.today().isoformat()
    return render_template(
        "report_form.html",
        client=client,
        accounts=accounts,
        last_report=last_report,
        last_balances=last_balances,
        today=today,
        quarter=db._to_quarter(today),
    )


@app.route("/reports/<int:report_id>")
def report_detail(report_id):
    report = db.get_report(report_id)
    if not report:
        return redirect(url_for("clients"))
    client = db.get_client(report["client_id"])
    balances = db.get_report_balances(report_id)
    sacs = db.compute_sacs(client, report)
    tcc = db.compute_tcc(client, report, balances)
    all_reports = db.get_reports_for_client(report["client_id"])
    return render_template(
        "report_detail.html",
        client=client,
        report=report,
        balances=balances,
        sacs=sacs,
        tcc=tcc,
        all_reports=all_reports,
    )


# ── PDF Downloads ─────────────────────────────────────────────────────────────

@app.route("/reports/<int:report_id>/pdf/sacs")
def pdf_sacs(report_id):
    report = db.get_report(report_id)
    client = db.get_client(report["client_id"])
    sacs_data = db.compute_sacs(client, report)
    buf = io.BytesIO()
    generate_sacs_pdf(buf, client, report, sacs_data)
    buf.seek(0)
    filename = f"SACS_{client['name1'].replace(' ', '_')}_{report['quarter'].replace(' ', '_')}.pdf"
    return send_file(buf, mimetype="application/pdf", as_attachment=True, download_name=filename)


@app.route("/reports/<int:report_id>/pdf/tcc")
def pdf_tcc(report_id):
    report = db.get_report(report_id)
    client = db.get_client(report["client_id"])
    balances = db.get_report_balances(report_id)
    accounts = db.get_accounts(report["client_id"])
    tcc_data = db.compute_tcc(client, report, balances)
    buf = io.BytesIO()
    generate_tcc_pdf(buf, client, report, accounts, balances, tcc_data)
    buf.seek(0)
    filename = f"TCC_{client['name1'].replace(' ', '_')}_{report['quarter'].replace(' ', '_')}.pdf"
    return send_file(buf, mimetype="application/pdf", as_attachment=True, download_name=filename)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
