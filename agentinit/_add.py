"""Resource installation logic for `agentinit add`."""

from __future__ import annotations

import os
import shutil
import sys
from typing import Callable

ADD_RESOURCE_TYPES = ("mcp", "security", "skill", "soul")

_ADD_HANDLERS = {
    "skill": {
        "template_src": os.path.join("skills", "{name}"),
        "dest_pattern": os.path.join(".agents", "skills", "{name}"),
        "dest_pattern_alt": os.path.join(".claude", "skills", "{name}"),
        "agents_section": None,
        "needs_name": True,
        "is_dir": True,
    },
    "mcp": {
        "template_src": os.path.join("mcp", "{name}.md"),
        "dest_pattern": os.path.join(".agents", "mcp-{name}.md"),
        "agents_section": "## Tools & Integrations",
        "needs_name": True,
        "is_dir": False,
    },
    "security": {
        "template_src": "security.md",
        "dest_pattern": os.path.join(".agents", "security.md"),
        "agents_section": "## Rules & Guardrails",
        "needs_name": False,
        "is_dir": False,
    },
    "soul": {
        "template_src": "soul.md",
        "dest_pattern": os.path.join(".agents", "soul.md"),
        "agents_section": "## Personality",
        "needs_name": False,
        "is_dir": False,
    },
}


def _fail(message: str) -> None:
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(1)


def _warn(message: str) -> None:
    print(f"Warning: {message}", file=sys.stderr)


def _resolve_template_source(
    handler: dict[str, object], add_template_dir: str, name: str | None
) -> str:
    """Resolve the resource template path from handler and optional *name*."""
    src_pattern = str(handler["template_src"])
    if handler["needs_name"]:
        return os.path.join(add_template_dir, src_pattern.replace("{name}", str(name)))
    return os.path.join(add_template_dir, src_pattern)


def _extract_template_description(src_path: str) -> str:
    """Extract short description from a template file."""
    if not os.path.isfile(src_path):
        return ""
    try:
        with open(src_path, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if line.startswith("description:"):
                    return line.split(":", 1)[1].strip()
                if line.startswith("# "):
                    return line[2:].strip()
    except OSError:
        return ""
    return ""


def _list_available(resource_type: str, add_template_dir: str) -> list[str]:
    """List available items for a resource type."""
    handler = _ADD_HANDLERS[resource_type]
    src_pattern = handler["template_src"]

    if handler["needs_name"]:
        parent = os.path.join(add_template_dir, os.path.dirname(src_pattern))
        if not os.path.isdir(parent):
            return []
        entries = sorted(os.listdir(parent))
        if handler["is_dir"]:
            return [e for e in entries if os.path.isdir(os.path.join(parent, e))]
        return [
            os.path.splitext(e)[0]
            for e in entries
            if os.path.isfile(os.path.join(parent, e)) and e.endswith(".md")
        ]

    src = os.path.join(add_template_dir, src_pattern)
    if os.path.isfile(src):
        return [os.path.splitext(os.path.basename(src_pattern))[0]]
    return []


def _item_source_for_list(resource_type: str, add_template_dir: str, item: str) -> str:
    """Resolve the template file path to inspect for an item description."""
    handler = _ADD_HANDLERS[resource_type]
    src_path = _resolve_template_source(handler, add_template_dir, item)
    if handler["is_dir"]:
        return os.path.join(src_path, "SKILL.md")
    return src_path


def _print_add_list(resource_type: str, add_template_dir: str) -> None:
    """Print a formatted table of available resources."""
    items = _list_available(resource_type, add_template_dir)
    if not items:
        print(f"  No {resource_type} templates available.")
        return
    print(f"\n  Available {resource_type} resources:")
    for item in items:
        src_path = _item_source_for_list(resource_type, add_template_dir, item)
        desc = _extract_template_description(src_path)
        if desc:
            print(f"    {item:30s} {desc}")
        else:
            print(f"    {item}")


def _append_agents_section(
    dest: str, section_heading: str, reference_line: str
) -> None:
    """Append a reference line under a section in AGENTS.md, creating it if needed."""
    agents_path = os.path.join(dest, "AGENTS.md")
    if not os.path.isfile(agents_path):
        print(
            "Warning: AGENTS.md not found. Run 'agentinit init' first, or create it manually.",
            file=sys.stderr,
        )
        return

    with open(agents_path, "r", encoding="utf-8") as f:
        content = f.read()

    if reference_line.strip() in content:
        return

    lines = content.splitlines()
    heading_index = _find_heading_line(lines, section_heading)
    if heading_index is not None:
        insert_at = heading_index + 1
        insert_lines = ["", reference_line, ""]
        if insert_at < len(lines) and not lines[insert_at].strip():
            insert_at += 1
            insert_lines = [reference_line, ""]
        lines[insert_at:insert_at] = insert_lines
        content = "\n".join(lines)
        if content and not content.endswith("\n"):
            content += "\n"
    else:
        content = content.rstrip("\n") + f"\n\n{section_heading}\n\n{reference_line}\n"

    with open(agents_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)


def _find_heading_line(lines: list[str], heading: str) -> int | None:
    """Return the first markdown heading line index outside fenced code blocks."""
    in_fence = False
    fence_marker = ""

    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(("```", "~~~")):
            marker = stripped[:3]
            if not in_fence:
                in_fence = True
                fence_marker = marker
            elif marker == fence_marker:
                in_fence = False
                fence_marker = ""
            continue

        if not in_fence and stripped == heading:
            return index

    return None


def _validate_name(
    resource_type: str,
    handler: dict[str, object],
    name: str | None,
    available: list[str],
) -> None:
    """Validate required/known name constraints."""
    if resource_type == "soul" and not name:
        _fail(
            "'soul' requires a persona name. Example: agentinit add soul \"YourAgentName\""
        )
    if not handler["needs_name"]:
        return
    if not name:
        if available:
            _fail(
                f"'{resource_type}' requires a name. Available: {', '.join(available)}"
            )
        _fail(f"'{resource_type}' requires a name.")
    if name not in available:
        known = f" Available: {', '.join(available)}" if available else ""
        _fail(f"unknown {resource_type}: '{name}'.{known}")


def _validate_source(
    resource_type: str,
    name: str | None,
    src: str,
    handler: dict[str, object],
    add_template_dir: str,
    available: list[str],
    resolves_within: Callable[[str, str], bool],
) -> None:
    """Validate source template path and existence."""
    add_template_root = os.path.realpath(add_template_dir)
    if not resolves_within(add_template_root, src):
        _fail(f"template path escapes add template directory: {name!r}")

    missing = (handler["is_dir"] and not os.path.isdir(src)) or (
        not handler["is_dir"] and not os.path.isfile(src)
    )
    if missing:
        known = f" Available: {', '.join(available)}" if available else ""
        _fail(f"unknown {resource_type}: '{name}'.{known}")


def _resolve_destination(
    dest: str,
    resource_type: str,
    handler: dict[str, object],
    name: str | None,
) -> str:
    """Resolve destination path (with skill fallback rules)."""
    if handler["needs_name"]:
        dst = os.path.join(
            dest, str(handler["dest_pattern"]).replace("{name}", str(name))
        )
    else:
        dst = os.path.join(dest, str(handler["dest_pattern"]))

    if resource_type != "skill":
        return dst

    alt = handler.get("dest_pattern_alt")
    alt_dst = os.path.join(dest, str(alt).replace("{name}", str(name))) if alt else None
    if not os.path.isdir(os.path.join(dest, ".agents")):
        return alt_dst or dst
    if alt_dst and os.path.exists(alt_dst) and not os.path.exists(dst):
        return alt_dst
    return dst


def _validate_destination_path(
    dest: str, dst: str, resolves_within: Callable[[str, str], bool]
) -> bool:
    """Validate destination safety. Return False when operation should skip."""
    dest_real = os.path.realpath(dest)
    if not resolves_within(dest_real, os.path.dirname(dst)) or not resolves_within(
        dest_real, dst
    ):
        _fail(f"destination path escapes project root: {os.path.relpath(dst, dest)}")

    if os.path.lexists(dst) and os.path.islink(dst):
        _warn(f"destination is a symlink, skipping: {os.path.relpath(dst, dest)}")
        return False
    return True


def _prepare_destination(dest: str, dst: str, force: bool) -> bool:
    """Prepare destination path. Return False when nothing should be changed."""
    rel = os.path.relpath(dst, dest)
    if os.path.exists(dst) and not force:
        _warn(f"{rel} already exists. Use --force to overwrite.")
        return False

    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.exists(dst) and force:
        try:
            if os.path.isdir(dst):
                shutil.rmtree(dst)
            else:
                os.remove(dst)
        except OSError as exc:
            _fail(f"failed to overwrite existing path: {rel} ({exc})")
    return True


def _copy_resource(src: str, dst: str, is_dir: bool) -> None:
    """Copy file or directory resource into destination."""
    if is_dir:
        shutil.copytree(src, dst)
    else:
        shutil.copy2(src, dst)


def _apply_post_copy(resource_type: str, dst: str, name: str | None) -> None:
    """Apply resource-specific post-copy transforms."""
    if resource_type != "soul":
        return
    with open(dst, "r", encoding="utf-8") as f:
        content = f.read()
    content = content.replace("{{NAME}}", str(name))
    with open(dst, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)


def cmd_add(
    args, *, template_dir: str, resolves_within: Callable[[str, str], bool]
) -> None:
    """Add a modular agentic resource to the current project."""
    add_template_dir = os.path.join(template_dir, "add")
    resource_type = args.type
    handler = _ADD_HANDLERS[resource_type]
    dest = os.path.abspath(".")

    if args.list:
        _print_add_list(resource_type, add_template_dir)
        return

    name = args.name
    available = (
        _list_available(resource_type, add_template_dir)
        if handler["needs_name"]
        else []
    )
    _validate_name(resource_type, handler, name, available)

    src = _resolve_template_source(handler, add_template_dir, name)
    _validate_source(
        resource_type,
        name,
        src,
        handler,
        add_template_dir,
        available,
        resolves_within,
    )

    dst = _resolve_destination(dest, resource_type, handler, name)
    if not _validate_destination_path(dest, dst, resolves_within):
        return
    if not _prepare_destination(dest, dst, bool(args.force)):
        return

    _copy_resource(src, dst, bool(handler["is_dir"]))
    _apply_post_copy(resource_type, dst, name)

    rel_dst = os.path.relpath(dst, dest)
    print(f"Added {resource_type}: {rel_dst}")

    if handler["agents_section"]:
        reference = f"- `{rel_dst}`"
        _append_agents_section(dest, handler["agents_section"], reference)
        print(f"  Updated AGENTS.md ({handler['agents_section']})")
