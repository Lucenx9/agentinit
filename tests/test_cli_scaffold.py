"""Tests for agentinit.cli."""

import sys

import pytest

import agentinit.cli as cli
from tests.helpers import (
    make_args,
    make_init_args,
)


class TestCopyTemplate:
    def test_copies_managed_files(self, tmp_path):
        copied, skipped = cli.copy_template(str(tmp_path))
        assert len(copied) > 0
        assert (tmp_path / "AGENTS.md").exists()
        assert (tmp_path / "docs" / "PROJECT.md").exists()

    def test_skips_existing_without_force(self, tmp_path):
        cli.copy_template(str(tmp_path))
        copied, skipped = cli.copy_template(str(tmp_path))
        assert copied == []
        assert len(skipped) > 0

    def test_overwrites_with_force(self, tmp_path):
        cli.copy_template(str(tmp_path))
        (tmp_path / "AGENTS.md").write_text("custom")
        copied, _ = cli.copy_template(str(tmp_path), force=True)
        assert "AGENTS.md" in copied
        assert (tmp_path / "AGENTS.md").read_text() != "custom"

    def test_gitignore_never_overwritten(self, tmp_path):
        cli.copy_template(str(tmp_path))
        (tmp_path / ".gitignore").write_text("custom")
        cli.copy_template(str(tmp_path), force=True)
        assert (tmp_path / ".gitignore").read_text() == "custom"

    def test_skips_symlink_destination(self, tmp_path):
        target = tmp_path / "target"
        target.write_text("x")
        agents = tmp_path / "AGENTS.md"
        agents.symlink_to(target)
        _, skipped = cli.copy_template(str(tmp_path))
        assert "AGENTS.md" in skipped

    def test_empty_template_dir(self, tmp_path, monkeypatch):
        fake = tmp_path / "empty_template"
        fake.mkdir()
        monkeypatch.setattr(cli, "TEMPLATE_DIR", str(fake))
        copied, skipped = cli.copy_template(str(tmp_path / "dest"))
        assert copied == []
        assert skipped == []


class TestWriteTodo:
    def test_creates_file(self, tmp_path):
        cli.write_todo(str(tmp_path))
        assert (tmp_path / "docs" / "TODO.md").exists()
        content = (tmp_path / "docs" / "TODO.md").read_text(encoding="utf-8")
        assert "# TODO" in content

    def test_creates_docs_dir(self, tmp_path):
        dest = tmp_path / "sub"
        dest.mkdir()
        cli.write_todo(str(dest))
        assert (dest / "docs" / "TODO.md").exists()

    def test_skips_existing_without_force(self, tmp_path, capsys):
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "TODO.md").write_text("my stuff")
        cli.write_todo(str(tmp_path), force=False)
        assert (docs / "TODO.md").read_text() == "my stuff"
        assert "already exists" in capsys.readouterr().err

    def test_overwrites_with_force(self, tmp_path):
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "TODO.md").write_text("my stuff")
        cli.write_todo(str(tmp_path), force=True)
        assert "# TODO" in (docs / "TODO.md").read_text()


class TestWriteDecisions:
    def test_creates_file(self, tmp_path):
        cli.write_decisions(str(tmp_path))
        path = tmp_path / "docs" / "DECISIONS.md"
        assert path.exists()
        assert "# Decisions" in path.read_text(encoding="utf-8")

    def test_skips_existing_without_force(self, tmp_path, capsys):
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "DECISIONS.md").write_text("keep")
        cli.write_decisions(str(tmp_path), force=False)
        assert (docs / "DECISIONS.md").read_text() == "keep"
        assert "already exists" in capsys.readouterr().err

    def test_overwrites_with_force(self, tmp_path):
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "DECISIONS.md").write_text("old")
        cli.write_decisions(str(tmp_path), force=True)
        assert "# Decisions" in (docs / "DECISIONS.md").read_text()


class TestApplyUpdates:
    def test_replaces_placeholder(self, tmp_path):
        cli.copy_template(str(tmp_path))
        args = make_args(purpose="My awesome project", prompt=False)
        cli.apply_updates(str(tmp_path), args)
        content = (tmp_path / "docs" / "PROJECT.md").read_text(encoding="utf-8")
        assert "My awesome project" in content
        assert "Describe what this project is for" not in content

    def test_noop_when_file_missing(self, tmp_path, capsys):
        args = make_args(purpose="anything", prompt=False)
        cli.apply_updates(str(tmp_path), args)
        assert "not a regular file" in capsys.readouterr().err

    def test_prompt_fails_if_not_tty(self, tmp_path, monkeypatch, capsys):
        cli.copy_template(str(tmp_path))
        args = make_args(prompt=True)
        monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
        with pytest.raises(SystemExit) as exc:
            cli.apply_updates(str(tmp_path), args)
        assert exc.value.code == 1
        err = capsys.readouterr().err
        assert "requires an interactive terminal" in err
        assert "--purpose" in err

    def test_wizard_injects_safe_defaults_after_heading(self, tmp_path, monkeypatch):
        """Safe Defaults block should be inserted after # Conventions heading, not prepended."""
        cli.copy_template(str(tmp_path))
        args = make_args(prompt=True, purpose="Test project")
        # Simulate wizard inputs: env, constraints, commands (all empty for this test)
        inputs = iter(["", "", ""])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        cli.apply_updates(str(tmp_path), args)

        content = (tmp_path / "docs" / "CONVENTIONS.md").read_text(encoding="utf-8")
        lines = content.splitlines()

        # Find positions of key headings
        conventions_idx = None
        safe_defaults_idx = None
        style_idx = None
        for i, line in enumerate(lines):
            if line == "# Conventions":
                conventions_idx = i
            elif line == "## Safe Defaults":
                safe_defaults_idx = i
            elif line == "## Style":
                style_idx = i

        assert conventions_idx is not None, "Should have # Conventions heading"
        assert safe_defaults_idx is not None, "Should have ## Safe Defaults heading"
        assert style_idx is not None, "Should have ## Style heading"
        # Safe Defaults should be AFTER # Conventions and BEFORE ## Style
        assert conventions_idx < safe_defaults_idx < style_idx, (
            f"Safe Defaults should be between # Conventions and ## Style, got positions: "
            f"Conventions={conventions_idx}, SafeDefaults={safe_defaults_idx}, Style={style_idx}"
        )

    def test_wizard_env_inserts_before_stack(self, tmp_path, monkeypatch):
        """Wizard environment should be inserted before ## Stack."""
        cli.copy_template(str(tmp_path))
        args = make_args(prompt=True, purpose="Test project")
        inputs = iter(["Linux x86_64", "", ""])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        cli.apply_updates(str(tmp_path), args)

        content = (tmp_path / "docs" / "PROJECT.md").read_text(encoding="utf-8")
        assert "## Environment" in content
        assert "- OS/device: Linux x86_64" in content
        env_pos = content.index("## Environment")
        stack_pos = content.index("## Stack")
        assert env_pos < stack_pos

    def test_wizard_constraints_replaces_placeholders(self, tmp_path, monkeypatch):
        """Wizard constraints should replace the template constraint placeholders."""
        cli.copy_template(str(tmp_path))
        args = make_args(prompt=True, purpose="Test project")
        inputs = iter(["", "No external API calls", ""])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        cli.apply_updates(str(tmp_path), args)

        content = (tmp_path / "docs" / "PROJECT.md").read_text(encoding="utf-8")
        assert "- No external API calls" in content
        assert "(document security constraints)" not in content

    def test_wizard_safe_defaults_not_duplicated(self, tmp_path, monkeypatch):
        """Running wizard multiple times should inject Safe Defaults only once."""
        cli.copy_template(str(tmp_path))
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)

        args = make_args(prompt=True, purpose=None)
        for purpose in ("First run", "Second run"):
            inputs = iter([purpose, "", "", ""])
            monkeypatch.setattr("builtins.input", lambda _: next(inputs))
            cli.apply_updates(str(tmp_path), args)

        content = (tmp_path / "docs" / "CONVENTIONS.md").read_text(encoding="utf-8")
        assert content.count("## Safe Defaults") == 1

    def test_non_english_purpose_warns(self, tmp_path, capsys):
        cli.copy_template(str(tmp_path))
        args = make_args(
            purpose="Una semplice API REST per gestire todo list con FastAPI + SQLite",
            prompt=False,
        )
        cli.apply_updates(str(tmp_path), args)
        err = capsys.readouterr().err
        assert "appears non-English" in err

    def test_translate_purpose_flag_translates_project_and_llms(self, tmp_path, capsys):
        cli.copy_template(str(tmp_path))
        args = make_args(
            purpose="Una semplice API REST per gestire todo list con FastAPI + SQLite",
            prompt=False,
            translate_purpose=True,
        )
        cli.apply_updates(str(tmp_path), args)

        project = (tmp_path / "docs" / "PROJECT.md").read_text(encoding="utf-8")
        assert (
            "**Purpose:** A simple REST API to manage a todo list with FastAPI + SQLite"
            in project
        )
        llms = (tmp_path / "llms.txt").read_text(encoding="utf-8")
        assert llms.splitlines()[0] == (
            "# A simple REST API to manage a todo list with FastAPI + SQLite"
        )
        assert (
            llms.splitlines()[1]
            == "> Una semplice API REST per gestire todo list con FastAPI + SQLite"
        )
        out = capsys.readouterr().out
        assert "Purpose translated to English for docs/*" in out

    def test_detect_auto_translates_romance_purpose(self, tmp_path):
        cli.copy_template(str(tmp_path))
        args = make_args(
            purpose="Une API REST simple pour gerer une liste de taches avec FastAPI + SQLite",
            prompt=False,
            detect=True,
        )
        cli.apply_updates(str(tmp_path), args)
        project = (tmp_path / "docs" / "PROJECT.md").read_text(encoding="utf-8")
        assert (
            "A simple REST API to manage a todo list with FastAPI + SQLite" in project
        )


class TestRefreshLlms:
    def test_generates_enriched_llms_from_existing_files(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args(purpose="AI-powered code review assistant"))

        agents_path = tmp_path / "AGENTS.md"
        agents_content = agents_path.read_text(encoding="utf-8")
        agents_path.write_text(
            agents_content + "\n- **YOU MUST NEVER** skip unit tests.\n",
            encoding="utf-8",
        )

        skill_dir = tmp_path / ".agents" / "skills" / "reviewer"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("# Reviewer\n", encoding="utf-8")

        elapsed = cli.refresh_llms_txt(str(tmp_path))
        llms = (tmp_path / "llms.txt").read_text(encoding="utf-8")

        assert elapsed < 1.0
        lines = llms.splitlines()
        assert lines[0].startswith("# ")
        assert lines[1] == "> AI-powered code review assistant"
        assert "## Key Files" in llms
        assert "- [AGENTS.md](AGENTS.md): Instructions and Rules" in llms
        assert "- [docs/STATE.md](docs/STATE.md): Current State & Focus" in llms
        assert (
            "- [docs/CONVENTIONS.md](docs/CONVENTIONS.md): Development Conventions"
            in llms
        )
        assert "- [docs/TODO.md](docs/TODO.md): Pending Tasks" in llms
        assert "- [docs/DECISIONS.md](docs/DECISIONS.md): Architectural Log" in llms
        assert "## Hardened Mandates" in llms
        assert "**YOU MUST ALWAYS**" in llms
        assert "**YOU MUST NEVER** skip unit tests." in llms
        assert "(AGENTS.md)" in llms
        assert "## Skills & Routers" in llms
        assert "(.agents/skills/reviewer/SKILL.md)" in llms
        assert "- [.agents/skills/](.agents/skills/)" in llms

    def test_marks_missing_key_files_for_minimal_profile(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args(minimal=True))
        llms = (tmp_path / "llms.txt").read_text(encoding="utf-8")

        assert "(missing in this profile)" in llms
        assert (
            "[docs/STATE.md](docs/STATE.md): Current State & Focus (missing in this profile)"
            in llms
        )
        assert (
            "[docs/TODO.md](docs/TODO.md): Pending Tasks (missing in this profile)"
            in llms
        )
        assert (
            "[docs/DECISIONS.md](docs/DECISIONS.md): Architectural Log (missing in this profile)"
            in llms
        )
        assert "- [No additional skills or routers configured](AGENTS.md)" in llms

    def test_hardened_and_skills_sections_are_link_lists(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args(purpose="Strict format check"))
        llms = (tmp_path / "llms.txt").read_text(encoding="utf-8")
        lines = llms.splitlines()

        def section_lines(title):
            start = lines.index(title) + 1
            end = len(lines)
            for i in range(start, len(lines)):
                if lines[i].startswith("## "):
                    end = i
                    break
            return [line for line in lines[start:end] if line.strip()]

        hardened = section_lines("## Hardened Mandates")
        skills = section_lines("## Skills & Routers")

        assert hardened
        assert skills
        assert all(line.startswith("- [") for line in hardened)
        assert all("](" in line for line in hardened)
        assert all(line.startswith("- [") for line in skills)
        assert all("](" in line for line in skills)

    def test_summary_falls_back_to_manifest_detection(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text(
            "[project]\nname = 'demo-tool'\nrequires-python = '>=3.11'\n",
            encoding="utf-8",
        )
        cli.cmd_init(make_init_args(minimal=True))

        elapsed = cli.refresh_llms_txt(str(tmp_path))
        llms = (tmp_path / "llms.txt").read_text(encoding="utf-8")

        assert elapsed < 1.0
        assert llms.splitlines()[1] == "> Python >=3.11 project."

    def test_skips_symlink_destination(self, tmp_path, capsys):
        outside = tmp_path / "outside"
        outside.mkdir()
        cli.copy_template(str(tmp_path))
        (tmp_path / "llms.txt").unlink()
        (tmp_path / "llms.txt").symlink_to(outside / "llms.txt")

        elapsed = cli.refresh_llms_txt(str(tmp_path))

        assert elapsed is None
        assert not (outside / "llms.txt").exists()
        assert "managed path is a symlink" in capsys.readouterr().err
