"""Project document update helpers used by scaffold commands."""

from __future__ import annotations

import os
import re
import sys
from argparse import Namespace
from collections.abc import Callable

from agentinit._llms import _looks_generated_llms
from agentinit._project_detect import (
    _PURPOSE_PLACEHOLDER,
    _clear_purpose_original_marker,
    _detect_purpose_language,
    _extract_purpose_text,
    _purpose_seems_non_english,
    _replace_commands_section,
    _replace_purpose_text,
    _run_detect,
    _run_detect_conventions,
    _set_purpose_original_marker,
    _translate_text_to_english,
)

ValidateManagedPath = Callable[[str, str], bool]
RefreshLlms = Callable[[str], float | None]
PrefixFactory = Callable[[], str]


_ENVIRONMENT_SECTION_RE = re.compile(
    r"^## Environment\s*\n.*?(?=^## [^\n]+|\Z)",
    re.MULTILINE | re.DOTALL,
)


def _upsert_environment_section(content: str, env: str) -> str:
    """Insert or replace the Environment section in PROJECT.md content."""
    if not env:
        return content

    section = f"## Environment\n\n- OS/device: {env}\n\n"
    updated, count = _ENVIRONMENT_SECTION_RE.subn(section, content, count=1)
    if count:
        return updated
    return content.replace("## Stack", section + "## Stack", 1)


def _refresh_llms_if_generated(dest: str, refresh_llms_txt: RefreshLlms) -> bool:
    """Refresh llms.txt only when the current file still looks generated."""
    llms_path = os.path.join(dest, "llms.txt")
    if not os.path.isfile(llms_path):
        return False
    with open(llms_path, "r", encoding="utf-8") as f:
        current = f.read()
    if not _looks_generated_llms(current):
        return False
    return refresh_llms_txt(dest) is not None


def apply_updates(
    dest: str,
    args: Namespace,
    *,
    validate_managed_path: ValidateManagedPath,
    refresh_llms_txt: RefreshLlms,
    error_prefix: PrefixFactory,
    warning_prefix: PrefixFactory,
    writable_files: set[str] | None = None,
) -> None:
    """Apply purpose, wizard, and detection updates to project docs."""
    writable = (
        {os.path.normpath(rel).replace("\\", "/") for rel in writable_files}
        if writable_files is not None
        else None
    )

    def can_write(rel: str) -> bool:
        norm_rel = os.path.normpath(rel).replace("\\", "/")
        return writable is None or norm_rel in writable

    wizard_run = args.prompt
    if wizard_run:
        if not sys.stdin.isatty():
            print(
                error_prefix()
                + " --prompt requires an interactive terminal. Use --purpose for non-interactive prefill, or run without --prompt.",
                file=sys.stderr,
            )
            sys.exit(1)
        try:
            purpose = args.purpose
            if not purpose:
                purpose = input("Purpose (required): ").strip()
            if not purpose:
                purpose = input("Purpose cannot be empty: ").strip()
            if not purpose:
                print("No purpose provided — leaving as placeholder.")
                purpose = ""
            env = input("Environment (OS/device) [optional]: ").strip()
            constraints = input("Constraints [optional]: ").strip()
            commands = input(
                "Commands I can run (comma-separated) [optional]: "
            ).strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.")
            sys.exit(130)
    else:
        purpose = args.purpose or ""
        env = ""
        constraints = ""
        commands = ""

    translate_requested = bool(getattr(args, "translate_purpose", False))
    translated_for_docs = False

    project_changed = False
    project_content = ""
    project_path = os.path.join(dest, "docs", "PROJECT.md")
    project_rel = os.path.join("docs", "PROJECT.md")
    project_safe = validate_managed_path(dest, project_path)
    if project_safe and not os.path.isfile(project_path):
        print(
            warning_prefix()
            + " docs/PROJECT.md is not a regular file; skipping purpose update.",
            file=sys.stderr,
        )
    elif project_safe:
        with open(project_path, "r", encoding="utf-8") as f:
            content = original_content = f.read()

        if can_write(project_rel):
            if purpose:
                content = content.replace(_PURPOSE_PLACEHOLDER, purpose)
                content = _replace_purpose_text(content, purpose)
                if _detect_purpose_language(purpose) == "en":
                    content = _clear_purpose_original_marker(content)

            if wizard_run:
                content = _upsert_environment_section(content, env)
                if commands:
                    cmds_list = "\n".join(
                        f"- {command.strip()}"
                        for command in commands.split(",")
                        if command.strip()
                    )
                    content = _replace_commands_section(content, cmds_list)
                if constraints:
                    old_constraints = (
                        "- **Security:** (not configured)\n"
                        "- **Performance:** (not configured)\n"
                        "- **Deadlines/Limits:** (not configured)"
                    )
                    content = content.replace(old_constraints, f"- {constraints}")

            current_purpose = _extract_purpose_text(content)
            current_lang = _detect_purpose_language(current_purpose)
            should_translate = bool(
                current_purpose
                and current_purpose != _PURPOSE_PLACEHOLDER
                and current_lang in {"it", "es", "fr"}
                and (translate_requested or getattr(args, "detect", False))
            )
            if should_translate:
                translated = _translate_text_to_english(current_purpose)
                if translated and translated != current_purpose:
                    content = _replace_purpose_text(content, translated)
                    content = _set_purpose_original_marker(content, current_purpose)
                    translated_for_docs = True
                    print("Purpose translated to English for docs/*")
            elif purpose and _purpose_seems_non_english(purpose):
                print(
                    warning_prefix()
                    + " --purpose appears non-English; keep docs/* in English when possible.",
                    file=sys.stderr,
                )

            if getattr(args, "detect", False):
                content = _run_detect(dest, project_path, content)

            project_changed = content != original_content
            with open(project_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(content)
        project_content = content

        if can_write(project_rel) and not wizard_run and "(not configured)" in content:
            print("Run with --prompt to fill interactively.")

    if wizard_run:
        conv_path = os.path.join(dest, "docs", "CONVENTIONS.md")
        conv_rel = os.path.join("docs", "CONVENTIONS.md")
        if (
            can_write(conv_rel)
            and validate_managed_path(dest, conv_path)
            and os.path.isfile(conv_path)
        ):
            safe_defaults = (
                "## Safe Defaults\n\n"
                "- Prefer small, reversible changes\n"
                "- Ask before destructive actions\n"
                "- Provide copy-paste commands\n"
                "- State assumptions\n\n"
            )
            with open(conv_path, "r", encoding="utf-8") as f:
                conv_content = f.read()
            if "## Safe Defaults" not in conv_content:
                if "# Conventions\n" in conv_content:
                    conv_content = conv_content.replace(
                        "# Conventions\n",
                        f"# Conventions\n\n{safe_defaults}",
                        1,
                    )
                else:
                    conv_content = safe_defaults + conv_content
                with open(conv_path, "w", encoding="utf-8", newline="\n") as f:
                    f.write(conv_content)

    if getattr(args, "detect", False):
        conv_path = os.path.join(dest, "docs", "CONVENTIONS.md")
        conv_rel = os.path.join("docs", "CONVENTIONS.md")
        if (
            can_write(conv_rel)
            and validate_managed_path(dest, conv_path)
            and os.path.isfile(conv_path)
            and project_content
        ):
            with open(conv_path, "r", encoding="utf-8") as f:
                conv_content = f.read()
            conv_updated = _run_detect_conventions(project_content, conv_content)
            if translated_for_docs:
                conv_updated = _translate_text_to_english(conv_updated)
            if conv_updated != conv_content:
                with open(conv_path, "w", encoding="utf-8", newline="\n") as f:
                    f.write(conv_updated)
    elif translated_for_docs:
        conv_path = os.path.join(dest, "docs", "CONVENTIONS.md")
        conv_rel = os.path.join("docs", "CONVENTIONS.md")
        if (
            can_write(conv_rel)
            and validate_managed_path(dest, conv_path)
            and os.path.isfile(conv_path)
        ):
            with open(conv_path, "r", encoding="utf-8") as f:
                conv_content = f.read()
            conv_updated = _translate_text_to_english(conv_content)
            if conv_updated != conv_content:
                with open(conv_path, "w", encoding="utf-8", newline="\n") as f:
                    f.write(conv_updated)

    if can_write("llms.txt"):
        refresh_llms_txt(dest)
    elif validate_managed_path(dest, os.path.join(dest, "llms.txt")):
        if _refresh_llms_if_generated(dest, refresh_llms_txt):
            return
        if project_changed:
            print(
                warning_prefix()
                + " llms.txt already exists and was left untouched. Run 'agentinit refresh-llms' if you want to resync it.",
                file=sys.stderr,
            )
