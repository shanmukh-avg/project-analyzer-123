import ast
import os
import sqlite3
from datetime import datetime
from io import BytesIO

from flask import (Flask, abort, flash, g, render_template, request,
                   send_file)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-in-production")
app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024  # 1 MB request limit

DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "analyzer.db")
MAX_CODE = 100_000
MAX_DESC = 10_000
MAX_TITLE = 150


# ---------- Database ----------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    with sqlite3.connect(DATABASE) as db:
        db.execute(
            """CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                technology TEXT,
                difficulty TEXT,
                word_count INTEGER,
                reason TEXT,
                objectives TEXT,
                code_status TEXT,
                code_summary TEXT,
                created_at TEXT NOT NULL
            )"""
        )


# ---------- Analysis logic ----------
def analyze_project(title, description, technology, code_lines):
    words = len(description.split())
    techs = [t.strip() for t in technology.split(",") if t.strip()]

    score = 0
    score += 0 if words < 40 else 1 if words < 150 else 2
    score += 0 if len(techs) <= 2 else 1 if len(techs) <= 4 else 2
    score += 0 if code_lines < 80 else 1 if code_lines < 300 else 2

    difficulty = "Beginner" if score <= 1 else "Intermediate" if score <= 3 else "Advanced"
    reason = (f"Rated {difficulty} based on {words} description words, "
              f"{len(techs)} technologies and {code_lines} lines of code.")

    objectives = [
        f"Define the main problem that “{title}” solves.",
        "List the core features and the users who will use them.",
        "Design the data model and how data will be stored.",
        "Write test cases and document how to run the project.",
    ]
    if techs:
        objectives.insert(2, f"Plan how {', '.join(techs)} will work together.")
    if words < 40:
        objectives.insert(1, "Expand the project description with more detail.")

    return {
        "title": title,
        "description": description,
        "technology": ", ".join(techs) or "Not specified",
        "difficulty": difficulty,
        "word_count": words,
        "reason": reason,
        "objectives": objectives,
    }


def analyze_code(code):
    if not code.strip():
        return None

    lines = code.splitlines()
    result = {
        "total_lines": len([l for l in lines if l.strip()]),
        "functions": 0, "classes": 0, "imports": 0,
        "syntax_error": None, "status": "", "suggestions": [],
    }

    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        result["status"] = "Syntax error found"
        result["syntax_error"] = f"Line {exc.lineno}: {exc.msg}"
        result["suggestions"].append("Fix the syntax error and analyze again.")
        return result

    suggestions = result["suggestions"]
    has_docstring = False
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            result["functions"] += 1
        elif isinstance(node, ast.ClassDef):
            result["classes"] += 1
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            result["imports"] += 1
            if isinstance(node, ast.ImportFrom) and any(a.name == "*" for a in node.names):
                suggestions.append("Avoid wildcard imports (from x import *).")
        elif isinstance(node, ast.ExceptHandler) and node.type is None:
            suggestions.append("Avoid bare 'except:'; catch specific exceptions.")
        elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
              and node.func.id in ("eval", "exec")):
            suggestions.append(f"Avoid using {node.func.id}(); it can run untrusted code.")
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
            if ast.get_docstring(node):
                has_docstring = True

    if result["functions"] == 0 and result["total_lines"] > 20:
        suggestions.append("Split longer code into functions to improve readability.")
    if not has_docstring:
        suggestions.append("Add docstrings to explain modules, functions and classes.")
    if not any(l.lstrip().startswith("#") for l in lines):
        suggestions.append("Add comments where the logic is not obvious.")
    if any(len(l) > 100 for l in lines):
        suggestions.append("Some lines exceed 100 characters; consider shortening them.")

    suggestions[:] = list(dict.fromkeys(suggestions))
    if not suggestions:
        suggestions.append("No obvious issues found by the basic checks.")
    result["status"] = "Code parsed successfully"
    return result


# ---------- Routes ----------
@app.route("/", methods=["GET", "POST"])
def index():
    project = code_result = None
    form = {"title": "", "description": "", "technology": "", "code": ""}

    if request.method == "POST":
        for key in form:
            form[key] = request.form.get(key, "")
        title = form["title"].strip()
        description = form["description"].strip()
        technology = form["technology"].strip()
        code = form["code"]

        error = None
        if not title:
            error = "Please enter a project title."
        elif len(title) > MAX_TITLE:
            error = f"Title must be {MAX_TITLE} characters or fewer."
        elif len(description) > MAX_DESC:
            error = f"Description must be {MAX_DESC:,} characters or fewer."
        elif len(code) > MAX_CODE:
            error = f"Source code must be below {MAX_CODE:,} characters."

        if error:
            flash(error)
        else:
            code_result = analyze_code(code)
            lines = code_result["total_lines"] if code_result else 0
            project = analyze_project(title, description, technology, lines)

            code_status = code_result["status"] if code_result else "No code submitted"
            code_summary = (
                f"Lines: {code_result['total_lines']}, Functions: {code_result['functions']}, "
                f"Classes: {code_result['classes']}, Imports: {code_result['imports']}"
                if code_result else "")
            db = get_db()
            db.execute(
                """INSERT INTO analyses (title, description, technology, difficulty,
                   word_count, reason, objectives, code_status, code_summary, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (title, description, project["technology"], project["difficulty"],
                 project["word_count"], project["reason"],
                 "\n".join(project["objectives"]), code_status, code_summary,
                 datetime.now().strftime("%Y-%m-%d %H:%M")))
            db.commit()
            if code_result:
                code_result["suggestions"] = code_result["suggestions"]

    history = get_db().execute(
        "SELECT id, title, difficulty, code_status, created_at "
        "FROM analyses ORDER BY id DESC LIMIT 20").fetchall()

    return render_template("index.html", project=project, code_result=code_result,
                           history=history, form=form)


@app.route("/report/<int:analysis_id>")
def download_report(analysis_id):
    row = get_db().execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
    if row is None:
        abort(404)

    objectives = "\n".join(f"  - {o}" for o in (row["objectives"] or "").splitlines())
    text = (
        f"PROJECT ANALYSIS REPORT\n{'=' * 40}\n"
        f"Title:        {row['title']}\n"
        f"Date:         {row['created_at']}\n"
        f"Difficulty:   {row['difficulty']}\n"
        f"Technologies: {row['technology']}\n"
        f"Word count:   {row['word_count']}\n\n"
        f"Description:\n{row['description'] or 'No description provided.'}\n\n"
        f"Assessment:\n{row['reason']}\n\n"
        f"Suggested objectives:\n{objectives}\n\n"
        f"Code review: {row['code_status']}\n{row['code_summary'] or ''}\n"
    )
    return send_file(BytesIO(text.encode("utf-8")), mimetype="text/plain",
                     as_attachment=True, download_name=f"report_{analysis_id}.txt")


@app.errorhandler(413)
def too_large(_e):
    flash("Your submission is too large.")
    return render_template("index.html", project=None, code_result=None, history=[],
                           form={"title": "", "description": "", "technology": "", "code": ""}), 413


init_db()

if __name__ == "__main__":
    app.run(debug=True)
