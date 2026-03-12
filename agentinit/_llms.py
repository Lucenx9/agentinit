"""llms.txt rendering helpers for agentinit."""

import os
import re

from agentinit._project_detect import (
    _PURPOSE_PLACEHOLDER,
    _extract_purpose_original_marker,
    _extract_purpose_text,
)

_LLMS_DEFAULT_SUMMARY = (
    "(not configured - run init to set project name and description)"
)
_LLMS_KEY_FILES = [
    ("AGENTS.md", "Instructions and Rules"),
    ("docs/STATE.md", "Current State & Focus"),
    ("docs/CONVENTIONS.md", "Development Conventions"),
    ("docs/TODO.md", "Pending Tasks"),
    ("docs/DECISIONS.md", "Architectural Log"),
]
_LLMS_MAX_MANDATES = 8
_GENERATED_LLMS_HEADINGS = (
    "## Key Files",
    "## Hardened Mandates",
    "## Skills & Routers",
)


def _resolve_project_context_path(dest):
    """Resolve project context file preferring docs/PROJECT.md, then PROJECT.md."""
    candidates = [
        os.path.join(dest, "docs", "PROJECT.md"),
        os.path.join(dest, "PROJECT.md"),
    ]
    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate
    return candidates[0]


def _project_name_from_pyproject(pyproject_path):
    """Extract project.name from pyproject.toml when available."""
    if not os.path.isfile(pyproject_path):
        return ""
    try:
        import tomllib

        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
        project = data.get("project")
        if isinstance(project, dict):
            return str(project.get("name") or "").strip()
    except (OSError, ImportError, ValueError):
        return ""
    return ""


def _project_name_from_package_json(package_json_path):
    """Extract name from package.json when available."""
    if not os.path.isfile(package_json_path):
        return ""
    try:
        import json

        with open(package_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return str(data.get("name") or "").strip()
    except (OSError, ValueError):
        return ""


def _project_name_from_project_doc(project_path):
    """Extract first markdown title from PROJECT.md-style files."""
    if not os.path.isfile(project_path):
        return ""
    with open(project_path, "r", encoding="utf-8") as f:
        content = f.read()
    match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if not match:
        return ""
    title = match.group(1).strip()
    if title and title.lower() not in {"project", "project context", "context"}:
        return title
    return ""


def _extract_project_name(dest, project_path):
    """Infer project name from manifests, then docs/PROJECT.md, then folder name."""
    pyproject_path = os.path.join(dest, "pyproject.toml")
    name = _project_name_from_pyproject(pyproject_path)
    if name:
        return name

    package_json_path = os.path.join(dest, "package.json")
    name = _project_name_from_package_json(package_json_path)
    if name:
        return name

    name = _project_name_from_project_doc(project_path)
    if name:
        return name

    folder_name = os.path.basename(os.path.abspath(dest)).strip()
    return folder_name or "Project"


def _extract_stack_field(content, field_name):
    """Extract a Stack field value from docs/PROJECT.md."""
    pattern = re.compile(
        rf"^- \*\*{re.escape(field_name)}:\*\*\s*(.+)$",
        re.MULTILINE,
    )
    match = pattern.search(content)
    if not match:
        return ""
    value = match.group(1).strip()
    if not value or "(not configured)" in value:
        return ""
    return value


def _detect_project_summary(dest):
    """Infer a one-line summary from common project manifests."""
    # Prefer pyproject.toml when available.
    pyproject_path = os.path.join(dest, "pyproject.toml")
    if os.path.isfile(pyproject_path):
        requires_python = ""
        try:
            import tomllib

            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)
            project = data.get("project")
            if isinstance(project, dict):
                requires_python = str(project.get("requires-python") or "").strip()
        except (OSError, ImportError, ValueError):
            try:
                with open(pyproject_path, "r", encoding="utf-8") as f:
                    text = f.read()
                match = re.search(
                    r'^\s*requires-python\s*=\s*["\']([^"\']+)["\']\s*$',
                    text,
                    re.MULTILINE,
                )
                if match:
                    requires_python = match.group(1).strip()
            except OSError:
                requires_python = ""

        runtime = "Python"
        if requires_python:
            runtime = f"Python {requires_python}"
        return f"{runtime} project."

    package_json_path = os.path.join(dest, "package.json")
    if os.path.isfile(package_json_path):
        return "Node.js project."

    go_mod_path = os.path.join(dest, "go.mod")
    if os.path.isfile(go_mod_path):
        return "Go project."

    cargo_path = os.path.join(dest, "Cargo.toml")
    if os.path.isfile(cargo_path):
        return "Rust project."

    return ""


def _extract_project_summary(dest, project_path):
    """Return a one-line project summary from PROJECT.md or manifest detection."""
    if not os.path.isfile(project_path):
        detected = _detect_project_summary(dest)
        return detected or _LLMS_DEFAULT_SUMMARY

    with open(project_path, "r", encoding="utf-8") as f:
        content = f.read()

    for pattern in (r"^\*\*Purpose:\*\*\s*(.+)$", r"^Purpose:\s*(.+)$"):
        match = re.search(pattern, content, re.MULTILINE)
        if not match:
            continue
        summary = match.group(1).strip()
        if (
            summary
            and "Describe what this project" not in summary
            and "(not configured)" not in summary
            and "(describe your project" not in summary
        ):
            return summary

    language = _extract_stack_field(content, "Language(s)")
    runtime = _extract_stack_field(content, "Runtime")
    framework = _extract_stack_field(content, "Framework(s)")
    parts = [part for part in (language, framework, runtime) if part]
    if parts:
        return f"{' | '.join(parts)} project."

    detected = _detect_project_summary(dest)
    if detected:
        return detected

    return _LLMS_DEFAULT_SUMMARY


def _mandate_priority(line):
    """Score mandates so llms.txt keeps the most critical constraints first."""
    score = 0
    upper = line.upper()
    if "YOU MUST ALWAYS" in upper or "YOU MUST NEVER" in upper:
        score += 5
    if "MUST NEVER" in upper:
        score += 3
    if "MUST ALWAYS" in upper:
        score += 2
    if (
        "DOCS/STATE.MD" in upper
        or "DOCS/TODO.MD" in upper
        or "DOCS/DECISIONS.MD" in upper
    ):
        score += 2
    if "DO NOT ASK FOR PERMISSION" in upper:
        score += 1
    if "AUTONOMOUS" in upper:
        score += 1
    return score


def _extract_hardened_mandates(agents_path):
    """Extract MUST ALWAYS / MUST NEVER mandates from AGENTS.md."""
    scored = []
    seen = set()
    mandates_url = "AGENTS.md"
    if os.path.isfile(agents_path):
        with open(agents_path, "r", encoding="utf-8") as f:
            index = 0
            for raw_line in f:
                clean = raw_line.strip()
                clean = re.sub(r"^>\s*", "", clean)
                clean = re.sub(r"^[-*]\s*", "", clean)
                if not clean:
                    continue
                if "MUST ALWAYS" not in clean and "MUST NEVER" not in clean:
                    continue
                bullet = f"- [{clean}]({mandates_url})"
                if bullet not in seen:
                    seen.add(bullet)
                    scored.append((index, _mandate_priority(clean), bullet))
                index += 1

    mandates = []
    if scored:
        top = sorted(scored, key=lambda item: (-item[1], item[0]))[:_LLMS_MAX_MANDATES]
        top.sort(key=lambda item: item[0])
        mandates = [item[2] for item in top]

    if not mandates:
        mandates.append(
            "- [No explicit MUST ALWAYS/MUST NEVER mandates found](AGENTS.md)"
        )
    return mandates


def _build_key_files_list(dest):
    """Build the Key Files section with availability markers."""
    key_files = []
    for rel_path, description in _LLMS_KEY_FILES:
        full_path = os.path.join(dest, rel_path)
        suffix = "" if os.path.isfile(full_path) else " (missing in this profile)"
        key_files.append(f"- [{rel_path}]({rel_path}): {description}{suffix}")
    return key_files


def _list_agents_entries(dest):
    """List all entries under .agents/ for Skills & Routers."""
    agents_dir = os.path.join(dest, ".agents")
    entries = []
    if os.path.isdir(agents_dir):
        for root, dirs, files in os.walk(agents_dir):
            dirs.sort()
            files.sort()
            for dirname in dirs:
                rel_dir = os.path.relpath(os.path.join(root, dirname), dest).replace(
                    os.sep, "/"
                )
                entries.append(f"- [{rel_dir}/]({rel_dir}/)")
            for filename in files:
                rel_file = os.path.relpath(os.path.join(root, filename), dest).replace(
                    os.sep, "/"
                )
                entries.append(f"- [{rel_file}]({rel_file})")

    if not entries:
        entries.append("- [No additional skills or routers configured](AGENTS.md)")
    return entries


def _looks_generated_llms(content):
    """Return True when llms.txt still matches agentinit's generated shape."""
    lines = content.splitlines()
    return bool(
        len(lines) >= 2
        and lines[0].startswith("# ")
        and lines[1].startswith("> ")
        and all(heading in content for heading in _GENERATED_LLMS_HEADINGS)
    )


def _render_llms_content(dest, template_dir):
    """Render llms.txt from project files using the llms template."""
    project_path = _resolve_project_context_path(dest)
    project_name = _extract_project_name(dest, project_path)
    summary = _extract_project_summary(dest, project_path)
    if os.path.isfile(project_path):
        with open(project_path, "r", encoding="utf-8") as f:
            project_content = f.read()
        original_purpose = _extract_purpose_original_marker(project_content)
        translated_purpose = _extract_purpose_text(project_content)
        if (
            original_purpose
            and translated_purpose
            and translated_purpose != _PURPOSE_PLACEHOLDER
        ):
            project_name = translated_purpose
            summary = original_purpose
    key_files = _build_key_files_list(dest)
    mandates = _extract_hardened_mandates(os.path.join(dest, "AGENTS.md"))
    skills = _list_agents_entries(dest)

    template_path = os.path.join(template_dir, "llms.txt")
    if os.path.isfile(template_path):
        with open(template_path, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        content = (
            "# {{PROJECT_NAME}}\n> {{PROJECT_SUMMARY}}\n\n"
            "## Key Files\n{{KEY_FILES}}\n\n"
            "## Hardened Mandates\n{{HARDENED_MANDATES}}\n\n"
            "## Skills & Routers\n{{SKILLS_AND_ROUTERS}}\n"
        )

    replacements = {
        "{{PROJECT_NAME}}": project_name,
        "{{PROJECT_SUMMARY}}": summary,
        "{{KEY_FILES}}": "\n".join(key_files),
        "{{HARDENED_MANDATES}}": "\n".join(mandates),
        "{{SKILLS_AND_ROUTERS}}": "\n".join(skills),
    }
    if all(token in content for token in replacements):
        for token, value in replacements.items():
            content = content.replace(token, value)
        return content

    return (
        f"# {project_name}\n> {summary}\n\n"
        f"## Key Files\n{replacements['{{KEY_FILES}}']}\n\n"
        f"## Hardened Mandates\n{replacements['{{HARDENED_MANDATES}}']}\n\n"
        f"## Skills & Routers\n{replacements['{{SKILLS_AND_ROUTERS}}']}\n"
    )
