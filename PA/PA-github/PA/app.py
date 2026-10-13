import os
import sqlite3
from datetime import datetime
from flask import (
    Flask, render_template, request,
    redirect, url_for, flash, send_file
)
from io import BytesIO
from analyzer import analyze_code, analyze_project

app = Flask(__name__)
app.secret_key = os.environ.get(
    "FLASK_SECRET_KEY", "dev-key-change-before-deployment"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "project_history.db")


def get_db():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_db():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                technology TEXT,
                difficulty TEXT,
                code_status TEXT,
                created_at TEXT NOT NULL
            )
        """)


def save_analysis(title, technology, difficulty, code_status):
    with get_db() as db:
        db.execute("""
            INSERT INTO analyses
            (title, technology, difficulty, code_status, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            title, technology, difficulty, code_status,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))


@app.route("/", methods=["GET", "POST"])
def index():
    project = None
    code_result = None

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        technology = request.form.get("technology", "").strip()
        code = request.form.get("code", "")

        if not title:
            flash("Please enter a project title.")
            return render_template("index.html")

        if len(title) > 150 or len(description) > 10000:
            flash("The title or description is too long.")
            return render_template("index.html")

        if len(code) > 100000:
            flash("Please keep the code below 100,000 characters.")
            return render_template("index.html")

        project = analyze_project(title, description, technology)

        if code.strip():
            code_result = analyze_code(code)

        save_analysis(
            project["title"],
            project["technology"],
            project["difficulty"],
            code_result["status"] if code_result else "Not analyzed"
        )

    history = get_history()

    return render_template(
        "index.html",
        project=project,
        code_result=code_result,
        history=history
    )


def get_history():
    with get_db() as db:
        rows = db.execute("""
            SELECT * FROM analyses ORDER BY id DESC LIMIT 10
        """).fetchall()

    return rows


@app.route("/report/<int:analysis_id>")
def download_report(analysis_id):
    with get_db() as db:
        row = db.execute(
            "SELECT * FROM analyses WHERE id = ?",
            (analysis_id,)
        ).fetchone()

    if row is None:
        flash("Report not found.")
        return redirect(url_for("index"))

    content = f"""PROJECT ANALYZER REPORT

Project title: {row['title']}
Technology: {row['technology']}
Difficulty estimate: {row['difficulty']}
Code status: {row['code_status']}
Analyzed at: {row['created_at']}

Note: Difficulty is an approximate estimate.
This report does not guarantee project quality.
"""

    report = BytesIO(content.encode("utf-8"))
    report.seek(0)

    return send_file(
        report,
        mimetype="text/plain",
        as_attachment=True,
        download_name=f"project_report_{analysis_id}.txt"
    )


initialize_db()

if __name__ == "__main__":
    import logging
    app.logger.setLevel(logging.DEBUG)
    app.run(host="127.0.0.1", port=8080, debug=True)