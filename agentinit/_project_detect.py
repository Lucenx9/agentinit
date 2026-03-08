"""Project purpose, translation, and manifest-detection helpers for the CLI."""

import os
import re
import sys
import unicodedata

_PURPOSE_PLACEHOLDER = "(describe your project purpose and goals)"
_PURPOSE_ORIGINAL_MARKER_PREFIX = "<!-- agentinit:purpose-original:"
_PURPOSE_ORIGINAL_MARKER_RE = re.compile(
    r"^<!--\s*agentinit:purpose-original:\s*(.*?)\s*-->\s*$",
    re.MULTILINE,
)

_LANGUAGE_MARKERS = {
    "it": {
        "una",
        "uno",
        "semplice",
        "gestire",
        "progetto",
        "applicazione",
        "elenco",
        "lista",
        "con",
        "per",
        "delle",
        "degli",
        "della",
        "todo",
    },
    "es": {
        "una",
        "simple",
        "proyecto",
        "aplicacion",
        "lista",
        "tareas",
        "gestionar",
        "con",
        "para",
        "crear",
        "servicio",
    },
    "fr": {
        "une",
        "simple",
        "projet",
        "application",
        "liste",
        "taches",
        "gerer",
        "avec",
        "pour",
        "service",
    },
}

_PURPOSE_EXACT_TRANSLATIONS = {
    "una semplice api rest per gestire todo list con fastapi + sqlite": "A simple REST API to manage a todo list with FastAPI + SQLite",
    "una simple api rest para gestionar una lista de tareas con fastapi + sqlite": "A simple REST API to manage a todo list with FastAPI + SQLite",
    "une api rest simple pour gerer une liste de taches avec fastapi + sqlite": "A simple REST API to manage a todo list with FastAPI + SQLite",
}

_ROMANCE_TO_ENGLISH_REPLACEMENTS = [
    (r"\bapi rest\b", "REST API"),
    (r"\bapplication\b", "application"),
    (r"\baplicaci[oó]n\b", "application"),
    (r"\bprojet\b", "project"),
    (r"\bproyecto\b", "project"),
    (r"\blista de tareas\b", "todo list"),
    (r"\bliste de t[aâ]ches\b", "todo list"),
    (r"\btodo list\b", "todo list"),
    (r"\bavec\b", "with"),
    (r"\bcon\b", "with"),
    (r"\bpour\b", "to"),
    (r"\bpara\b", "to"),
    (r"\bper\b", "to"),
    (r"\bg[ée]rer\b", "manage"),
    (r"\bgestionar\b", "manage"),
    (r"\bgestire\b", "manage"),
    (r"\bune\b", "a"),
    (r"\buna\b", "a"),
    (r"\bun\b", "a"),
    (r"\bsimple\b", "simple"),
    (r"\bsemplice\b", "simple"),
]


def _ascii_fold(text):
    """Lowercase text and strip diacritics for lightweight language heuristics."""
    normalized = unicodedata.normalize("NFKD", text.lower())
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _extract_purpose_text(content):
    """Extract Purpose text from docs/PROJECT.md content."""
    for pattern in (r"^\*\*Purpose:\*\*\s*(.+)$", r"^Purpose:\s*(.+)$"):
        match = re.search(pattern, content, re.MULTILINE)
        if match:
            return match.group(1).strip()
    return ""


def _extract_purpose_original_marker(content):
    """Return preserved non-English purpose, if present."""
    match = _PURPOSE_ORIGINAL_MARKER_RE.search(content)
    if not match:
        return ""
    return match.group(1).strip()


def _set_purpose_original_marker(content, original_purpose):
    """Insert or update the purpose-original marker right below Purpose."""
    sanitized = re.sub(r"\s+", " ", original_purpose).replace("-->", "").strip()
    marker = f"{_PURPOSE_ORIGINAL_MARKER_PREFIX} {sanitized} -->"
    if _PURPOSE_ORIGINAL_MARKER_RE.search(content):
        return _PURPOSE_ORIGINAL_MARKER_RE.sub(marker, content, count=1)

    pattern = re.compile(r"^(\*\*Purpose:\*\*.+)$", re.MULTILINE)
    if pattern.search(content):
        return pattern.sub(rf"\1\n{marker}", content, count=1)
    return content


def _clear_purpose_original_marker(content):
    """Remove any purpose-original marker from content."""
    return _PURPOSE_ORIGINAL_MARKER_RE.sub("", content)


def _replace_purpose_text(content, new_purpose):
    """Replace Purpose value in PROJECT.md content."""
    for pattern in (r"(\*\*Purpose:\*\*\s*)(.+)", r"(Purpose:\s*)(.+)"):
        updated, count = re.subn(
            pattern,
            lambda m: f"{m.group(1)}{new_purpose}",
            content,
            count=1,
            flags=re.MULTILINE,
        )
        if count:
            return updated
    return content


def _detect_purpose_language(text):
    """Best-effort language detection for purpose text."""
    if not text:
        return "unknown"
    folded = _ascii_fold(text)
    tokens = {tok for tok in re.findall(r"[a-z]+", folded) if len(tok) >= 2}
    if not tokens:
        return "unknown"
    scores = {
        lang: len(tokens.intersection(markers))
        for lang, markers in _LANGUAGE_MARKERS.items()
    }
    best_lang, best_score = max(scores.items(), key=lambda item: item[1])
    if best_score >= 2:
        return best_lang
    return "en"


def _purpose_seems_non_english(text):
    """Backwards-compatible check for non-English purpose text."""
    return _detect_purpose_language(text) in {"it", "es", "fr"}


def _translate_text_to_english(text):
    """Translate common Romance-language project phrasing to English."""
    if not text:
        return text
    normalized = re.sub(r"\s+", " ", _ascii_fold(text.strip()))
    if normalized in _PURPOSE_EXACT_TRANSLATIONS:
        return _PURPOSE_EXACT_TRANSLATIONS[normalized]

    translated = text
    for pattern, repl in _ROMANCE_TO_ENGLISH_REPLACEMENTS:
        translated = re.sub(pattern, repl, translated, flags=re.IGNORECASE)
    translated = re.sub(r"\s+", " ", translated).strip()
    if not translated:
        return text
    return translated[0].upper() + translated[1:]


def _infer_python_setup_command_from_purpose(purpose_text):
    """Infer Python setup command from purpose phrasing."""
    lower = purpose_text.lower()
    if "poetry" in lower:
        return "poetry install"
    if (
        re.search(r"\buv\b", lower)
        or "uvicorn" in lower
        or "fastapi moderno" in lower
        or "modern fastapi" in lower
    ):
        return "uv sync"
    return "pip install -e ."


def _detect_from_purpose(content):
    """Infer baseline stack/commands from Purpose when manifests are missing."""
    purpose = _extract_purpose_text(content)
    if not purpose or purpose == _PURPOSE_PLACEHOLDER:
        return {}, {}

    lower = purpose.lower()
    stack_updates = {}
    cmd_updates = {}

    mentions_python = any(
        term in lower for term in ("python", "fastapi", "flask", "django")
    )
    if mentions_python:
        stack_updates["- **Language(s):** (not configured)"] = (
            "- **Language(s):** Python"
        )
        stack_updates["- **Runtime:** (not configured)"] = "- **Runtime:** Python 3.12"
        setup_cmd = _infer_python_setup_command_from_purpose(purpose)
        cmd_updates["- Setup: (not configured)"] = f"- Setup: {setup_cmd}"
        cmd_updates["- Test: (not configured)"] = "- Test: pytest -q"
        cmd_updates["- Lint/Format: (not configured)"] = "- Lint/Format: ruff check ."

    if "fastapi" in lower:
        stack_updates["- **Framework(s):** (not configured)"] = (
            "- **Framework(s):** FastAPI + Uvicorn"
        )
        cmd_updates["- Run: (not configured)"] = "- Run: uvicorn main:app --reload"
    elif "django" in lower:
        stack_updates["- **Framework(s):** (not configured)"] = (
            "- **Framework(s):** Django"
        )
        cmd_updates["- Run: (not configured)"] = "- Run: python manage.py runserver"
    elif "flask" in lower:
        stack_updates["- **Framework(s):** (not configured)"] = (
            "- **Framework(s):** Flask"
        )
        cmd_updates["- Run: (not configured)"] = (
            "- Run: flask --app main.py run --debug"
        )

    if "sqlite" in lower:
        stack_updates["- **Storage/Infra:** (not configured)"] = (
            "- **Storage/Infra:** SQLite"
        )
    elif "postgres" in lower or "postgresql" in lower:
        stack_updates["- **Storage/Infra:** (not configured)"] = (
            "- **Storage/Infra:** PostgreSQL"
        )
    elif "mysql" in lower:
        stack_updates["- **Storage/Infra:** (not configured)"] = (
            "- **Storage/Infra:** MySQL"
        )

    return stack_updates, cmd_updates


def _run_detect_conventions(project_content, conventions_content):
    """Fill conventions placeholders with stack-aware defaults."""
    lower = project_content.lower()
    is_python = "- **language(s):** python" in lower
    has_fastapi = "fastapi" in lower
    if not is_python:
        return conventions_content

    replacements = {
        "- **Formatting standard:** (not configured)": "- **Formatting standard:** Ruff (`ruff check .` + `ruff format .`)",
        "- **Commenting expectations:** (not configured)": "- **Commenting expectations:** Docstrings for public modules and API surface; comments only for non-obvious decisions.",
        "- **Files/directories:** (not configured)": "- **Files/directories:** `snake_case` for files/modules, grouped by feature/domain.",
        "- **Variables/functions/types:** (not configured)": "- **Variables/functions/types:** `snake_case` for variables/functions, `PascalCase` for classes, `UPPER_SNAKE_CASE` for constants.",
        "- **Branch naming:** (not configured)": "- **Branch naming:** `feature/<scope>`, `fix/<scope>`, `chore/<scope>`.",
        "- **Required test types:** (not configured)": "- **Required test types:** Unit tests with `pytest`; add integration/API tests for behavior-critical flows.",
        "- **Minimum coverage/gates:** (not configured)": "- **Minimum coverage/gates:** Tests must pass in CI before merge.",
        "- **Test data/fixtures:** (not configured)": "- **Test data/fixtures:** Reuse fixtures from `tests/conftest.py`; keep fixture scope minimal.",
        "- **Commit message format:** (not configured)": "- **Commit message format:** Conventional Commits (`feat:`, `fix:`, `chore:`).",
        "- **PR requirements/reviews:** (not configured)": "- **PR requirements/reviews:** Green CI and at least one reviewer approval.",
        "- **Merge strategy:** (not configured)": "- **Merge strategy:** Squash merge.",
    }
    if has_fastapi:
        replacements["- **Required test types:** (not configured)"] = (
            "- **Required test types:** Unit tests with `pytest` plus API integration tests for endpoints."
        )

    updated = conventions_content
    for old, new in replacements.items():
        updated = updated.replace(old, new)
    return updated


def _run_detect(dest, project_path, content):
    """Detect stack and commands from manifests and return updated content."""
    import json

    stack_updates = {}
    cmd_updates = {}

    # 1. Node: package.json
    pkg_json_path = os.path.join(dest, "package.json")
    if os.path.isfile(pkg_json_path):
        try:
            with open(pkg_json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            stack_updates["- **Runtime:** (not configured)"] = "- **Runtime:** Node.js"

            pm = str(data.get("packageManager") or "")
            manager = "npm"
            if "pnpm" in pm:
                manager = "pnpm"
            elif "yarn" in pm:
                manager = "yarn"
            elif "bun" in pm:
                manager = "bun"
            else:
                if os.path.isfile(os.path.join(dest, "pnpm-lock.yaml")):
                    manager = "pnpm"
                elif os.path.isfile(os.path.join(dest, "yarn.lock")):
                    manager = "yarn"
                elif os.path.isfile(os.path.join(dest, "bun.lockb")):
                    manager = "bun"
                else:
                    manager = "npm"

            scripts = data.get("scripts")
            if not isinstance(scripts, dict):
                scripts = {}
            run_prefix = (
                f"{manager} run " if manager not in ("yarn", "bun") else f"{manager} "
            )

            if "setup" in scripts:
                cmd_updates["- Setup: (not configured)"] = f"- Setup: {run_prefix}setup"
            else:
                cmd_updates["- Setup: (not configured)"] = f"- Setup: {manager} install"

            if "build" in scripts:
                cmd_updates["- Build: (not configured)"] = f"- Build: {run_prefix}build"
            if "test" in scripts:
                cmd_updates["- Test: (not configured)"] = f"- Test: {run_prefix}test"
            if "lint" in scripts:
                cmd_updates["- Lint/Format: (not configured)"] = (
                    f"- Lint/Format: {run_prefix}lint"
                )
            elif "format" in scripts:
                cmd_updates["- Lint/Format: (not configured)"] = (
                    f"- Lint/Format: {run_prefix}format"
                )
            if "dev" in scripts:
                cmd_updates["- Run: (not configured)"] = f"- Run: {run_prefix}dev"
            elif "start" in scripts:
                cmd_updates["- Run: (not configured)"] = f"- Run: {run_prefix}start"
        except (OSError, ValueError, TypeError):
            pass

    # 2. Go: go.mod
    go_mod_path = os.path.join(dest, "go.mod")
    if os.path.isfile(go_mod_path):
        try:
            with open(go_mod_path, "r", encoding="utf-8") as f:
                go_version = None
                for line in f:
                    line = line.strip()
                    if line.startswith("go "):
                        parts = line.split()
                        if len(parts) >= 2:
                            go_version = parts[1]
                        break

            stack_updates["- **Language(s):** (not configured)"] = (
                "- **Language(s):** Go"
            )
            if go_version:
                stack_updates["- **Runtime:** (not configured)"] = (
                    f"- **Runtime:** Go {go_version}"
                )

            cmd_updates["- Setup: (not configured)"] = "- Setup: go mod download"
            cmd_updates["- Build: (not configured)"] = "- Build: go build ./..."
            cmd_updates["- Test: (not configured)"] = "- Test: go test ./..."
            cmd_updates["- Run: (not configured)"] = "- Run: go run ."
        except (OSError, ValueError, IndexError):
            pass

    # TOML parsers (Python, Rust)
    try:
        import tomllib
    except ImportError:
        tomllib = None

    if not tomllib:
        toml_files = [
            f
            for f in ("pyproject.toml", "Cargo.toml")
            if os.path.isfile(os.path.join(dest, f))
        ]
        if toml_files:
            print(
                "Warning:" + f" TOML detection ({', '.join(toml_files)}) skipped — "
                "requires Python 3.11+. Run with Python 3.11 or later for full detection.",
                file=sys.stderr,
            )

    if tomllib:
        # 3. Rust: Cargo.toml
        cargo_path = os.path.join(dest, "Cargo.toml")
        if os.path.isfile(cargo_path):
            try:
                with open(cargo_path, "rb") as f:
                    cargo_data = tomllib.load(f)

                pkg = cargo_data.get("package")
                if not isinstance(pkg, dict):
                    pkg = {}
                edition = pkg.get("edition", "")

                lang_str = "- **Language(s):** Rust"
                if edition:
                    lang_str += f" ({edition})"
                stack_updates["- **Language(s):** (not configured)"] = lang_str

                cmd_updates["- Setup: (not configured)"] = "- Setup: cargo fetch"
                cmd_updates["- Build: (not configured)"] = "- Build: cargo build"
                cmd_updates["- Test: (not configured)"] = "- Test: cargo test"
                cmd_updates["- Lint/Format: (not configured)"] = (
                    "- Lint/Format: cargo fmt && cargo clippy"
                )
                cmd_updates["- Run: (not configured)"] = "- Run: cargo run"
            except (OSError, ValueError, TypeError, tomllib.TOMLDecodeError):
                pass

        # 4. Python: pyproject.toml
        pyproject_path = os.path.join(dest, "pyproject.toml")
        if os.path.isfile(pyproject_path):
            try:
                with open(pyproject_path, "rb") as f:
                    py_data = tomllib.load(f)

                manager = "pip"
                tool = py_data.get("tool")
                if isinstance(tool, dict):
                    if "poetry" in tool:
                        manager = "poetry"
                    elif "uv" in tool:
                        manager = "uv"
                    elif "pdm" in tool:
                        manager = "pdm"

                project = py_data.get("project")
                if not isinstance(project, dict):
                    project = {}
                requires_python = project.get("requires-python", "")

                stack_updates["- **Language(s):** (not configured)"] = (
                    "- **Language(s):** Python"
                )
                if requires_python:
                    stack_updates["- **Runtime:** (not configured)"] = (
                        f"- **Runtime:** Python {requires_python}"
                    )

                if manager == "poetry":
                    cmd_updates["- Setup: (not configured)"] = "- Setup: poetry install"
                    cmd_updates["- Run: (not configured)"] = "- Run: poetry run python"
                elif manager == "uv":
                    cmd_updates["- Setup: (not configured)"] = "- Setup: uv sync"
                    cmd_updates["- Run: (not configured)"] = "- Run: uv run python"
                elif manager == "pdm":
                    cmd_updates["- Setup: (not configured)"] = "- Setup: pdm install"
                    cmd_updates["- Run: (not configured)"] = "- Run: pdm run python"
                else:
                    cmd_updates["- Setup: (not configured)"] = (
                        "- Setup: pip install -e ."
                    )
            except (OSError, ValueError, TypeError, tomllib.TOMLDecodeError):
                pass

    purpose_stack_updates, purpose_cmd_updates = _detect_from_purpose(content)
    for key, value in purpose_stack_updates.items():
        stack_updates.setdefault(key, value)
    for key, value in purpose_cmd_updates.items():
        cmd_updates.setdefault(key, value)

    for k, v in stack_updates.items():
        content = content.replace(k, v)
    for k, v in cmd_updates.items():
        content = content.replace(k, v)

    return content


_COMMANDS_START = "<!-- agentinit:commands:start -->"
_COMMANDS_END = "<!-- agentinit:commands:end -->"
_COMMANDS_NOTE = "<!-- managed by agentinit --detect / --prompt -->"


def _replace_commands_section(content, new_body):
    """Replace content between commands markers, preserving surrounding text."""
    pattern = re.compile(
        re.escape(_COMMANDS_START) + r".*?" + re.escape(_COMMANDS_END),
        re.DOTALL,
    )
    replacement = f"{_COMMANDS_START}\n{_COMMANDS_NOTE}\n{new_body}\n{_COMMANDS_END}"
    new_content = pattern.sub(lambda m: replacement, content, count=1)
    return new_content
