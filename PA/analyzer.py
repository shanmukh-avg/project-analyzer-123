import ast
import re


def analyze_code(code):
    lines = code.splitlines()

    non_empty_lines = [
        line for line in lines if line.strip()
    ]

    comment_lines = [
        line for line in lines
        if line.strip().startswith("#")
    ]

    functions = 0
    classes = 0
    imports = 0
    syntax_error = None

    try:
        tree = ast.parse(code)

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions += 1

            elif isinstance(node, ast.ClassDef):
                classes += 1

            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                imports += 1

    except SyntaxError as error:
        syntax_error = (
            f"Line {error.lineno}: {error.msg}"
        )

    # Simple pattern-based suggestions, not guaranteed bugs.
    suggestions = []

    if not code.strip():
        suggestions.append("Add some Python code to analyze.")

    if code.strip() and "def " not in code and "class " not in code:
        suggestions.append(
            "Consider organizing larger programs into functions or classes."
        )

    if re.search(r"\bexcept\s*:", code):
        suggestions.append(
            "Avoid bare except clauses; catch specific exceptions."
        )

    if "eval(" in code:
        suggestions.append(
            "Review eval() carefully; untrusted input can be dangerous."
        )

    if not comment_lines and non_empty_lines:
        suggestions.append(
            "Add comments where they help explain complex logic."
        )

    if syntax_error:
        suggestions.append(
            "Fix the syntax error before running the program."
        )
    elif code.strip():
        suggestions.append("Python syntax check passed.")

    return {
        "total_lines": len(lines),
        "code_lines": len(non_empty_lines),
        "comment_lines": len(comment_lines),
        "blank_lines": len(lines) - len(non_empty_lines),
        "functions": functions,
        "classes": classes,
        "imports": imports,
        "syntax_error": syntax_error,
        "suggestions": suggestions,
        "status": (
            "Syntax error found" if syntax_error
            else "No syntax errors found"
        ) if code.strip() else "No code provided"
    }


def analyze_project(title, description, technology):
    description = description.strip()

    if not title.strip():
        title = "Untitled Project"

    words = len(description.split())

    if words < 15:
        level = "Beginner"
        reason = "The project description is short and may have a limited scope."
    elif words < 50:
        level = "Intermediate"
        reason = "The project has a moderate description and scope."
    else:
        level = "Advanced"
        reason = "The project description suggests a broader scope."

    objectives = [
        "Define the problem the project will solve.",
        "Identify the intended users and main features.",
        "Select suitable technologies.",
        "Test the implementation and document the results."
    ]

    return {
        "title": title.strip(),
        "description": description,
        "technology": technology.strip() or "Not specified",
        "word_count": words,
        "difficulty": level,
        "reason": reason,
        "objectives": objectives
    }