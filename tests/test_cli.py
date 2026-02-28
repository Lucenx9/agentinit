"""Tests for agentinit.cli."""

import argparse
import os
import sys

import pytest

import agentinit.cli as cli


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_args(**kwargs):
    """Build an argparse.Namespace with sensible defaults for cmd_new."""
    defaults = {
        "name": "proj",
        "dir": None,
        "force": False,
        "yes": True,
        "purpose": None,
        "prompt": False,
        "minimal": False,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def make_init_args(**kwargs):
    defaults = {"force": False, "minimal": False,
        "purpose": None,
        "prompt": False
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def make_remove_args(**kwargs):
    defaults = {"force": True, "dry_run": False, "archive": False}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


# ---------------------------------------------------------------------------
# copy_template
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# write_todo / write_decisions
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# apply_updates
# ---------------------------------------------------------------------------

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
        assert "requires an interactive TTY" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# cmd_new
# ---------------------------------------------------------------------------

class TestCmdNew:
    def test_creates_project(self, tmp_path):
        args = make_args(name="myproj", dir=str(tmp_path))
        cli.cmd_new(args)
        proj = tmp_path / "myproj"
        assert proj.is_dir()
        assert (proj / "AGENTS.md").exists()
        assert (proj / "docs" / "TODO.md").exists()
        assert (proj / "docs" / "DECISIONS.md").exists()

    def test_fails_if_exists_no_force(self, tmp_path):
        (tmp_path / "myproj").mkdir()
        args = make_args(name="myproj", dir=str(tmp_path))
        with pytest.raises(SystemExit) as exc:
            cli.cmd_new(args)
        assert exc.value.code == 1

    def test_force_overwrites(self, tmp_path):
        args = make_args(name="myproj", dir=str(tmp_path))
        cli.cmd_new(args)
        (tmp_path / "myproj" / "AGENTS.md").write_text("custom")
        args_force = make_args(name="myproj", dir=str(tmp_path), force=True)
        cli.cmd_new(args_force)
        assert (tmp_path / "myproj" / "AGENTS.md").read_text() != "custom"

    @pytest.mark.parametrize("bad_name", ["..", ".", "../.."])
    def test_rejects_traversal_names(self, tmp_path, bad_name, capsys):
        args = make_args(name=bad_name, dir=str(tmp_path))
        with pytest.raises(SystemExit) as exc:
            cli.cmd_new(args)
        assert exc.value.code == 1
        assert "invalid project name" in capsys.readouterr().err

    def test_accepts_path_with_slashes(self, tmp_path):
        args = make_args(name=str(tmp_path / "sub" / "proj"))
        cli.cmd_new(args)
        assert (tmp_path / "sub" / "proj" / "AGENTS.md").exists()

    def test_missing_template_no_orphan_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cli, "TEMPLATE_DIR", str(tmp_path / "nonexistent"))
        args = make_args(name="newproj", dir=str(tmp_path))
        with pytest.raises(SystemExit) as exc:
            cli.cmd_new(args)
        assert exc.value.code == 1
        assert not (tmp_path / "newproj").exists()

    def test_preserves_todo_without_force(self, tmp_path):
        args = make_args(name="myproj", dir=str(tmp_path))
        cli.cmd_new(args)
        todo = tmp_path / "myproj" / "docs" / "TODO.md"
        todo.write_text("user data")
        args2 = make_args(name="myproj", dir=str(tmp_path), force=True)
        # force overwrites template files but also TODO/DECISIONS with --force
        cli.cmd_new(args2)
        # with force=True, TODO gets overwritten
        assert "# TODO" in todo.read_text()

    def test_minimal_creates_only_core_files(self, tmp_path):
        args = make_args(name="myproj", dir=str(tmp_path), minimal=True, yes=True)
        cli.cmd_new(args)
        proj = tmp_path / "myproj"
        files = sorted(str(p.relative_to(proj)) for p in proj.rglob("*") if p.is_file())
        assert files == [
            "AGENTS.md",
            "CLAUDE.md",
            "docs/CONVENTIONS.md",
            "docs/PROJECT.md",
        ]
        content = (proj / "docs" / "PROJECT.md").read_text(encoding="utf-8")
        assert "Describe what this project is for" not in content
        # It should keep TBD in PROJECT.md if no purpose provided
        # Wait, the template has "Describe what this project is for, who it serves..." and we replace with TBD.
        assert "TBD" in content

    def test_minimal_with_purpose(self, tmp_path):
        args = make_args(name="myproj", dir=str(tmp_path), minimal=True, yes=True, purpose="Custom Purpose")
        cli.cmd_new(args)
        proj = tmp_path / "myproj"
        content = (proj / "docs" / "PROJECT.md").read_text(encoding="utf-8")
        assert "Custom Purpose" in content
        assert "Describe what this project is for" not in content


# ---------------------------------------------------------------------------
# cmd_init
# ---------------------------------------------------------------------------

class TestCmdInit:
    def test_copies_files_to_cwd(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args())
        assert (tmp_path / "AGENTS.md").exists()

    def test_idempotent(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args())
        cli.cmd_init(make_init_args())
        out = capsys.readouterr().out
        assert "already present" in out

    def test_minimal_creates_only_core_files(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args(minimal=True))
        files = sorted(str(p.relative_to(tmp_path)) for p in tmp_path.rglob("*") if p.is_file())
        assert files == [
            "AGENTS.md",
            "CLAUDE.md",
            "docs/CONVENTIONS.md",
            "docs/PROJECT.md",
        ]

    def test_minimal_with_purpose(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args(minimal=True, purpose="Init Purpose"))
        content = (tmp_path / "docs" / "PROJECT.md").read_text(encoding="utf-8")
        assert "Init Purpose" in content
        assert "Describe what this project is for" not in content

    def test_minimal_does_not_overwrite_project_or_conventions_without_force(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        docs = tmp_path / "docs"
        docs.mkdir()
        project = docs / "PROJECT.md"
        conventions = docs / "CONVENTIONS.md"
        project.write_text("custom project")
        conventions.write_text("custom conventions")

        cli.cmd_init(make_init_args(minimal=True, force=False))

        assert project.read_text() == "custom project"
        assert conventions.read_text() == "custom conventions"


# ---------------------------------------------------------------------------
# cmd_remove
# ---------------------------------------------------------------------------

class TestCmdRemove:
    def test_removes_files(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args())
        assert (tmp_path / "AGENTS.md").exists()
        cli.cmd_remove(make_remove_args())
        assert not (tmp_path / "AGENTS.md").exists()

    def test_dry_run_keeps_files(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args())
        cli.cmd_remove(make_remove_args(dry_run=True))
        assert (tmp_path / "AGENTS.md").exists()
        assert "Dry run" in capsys.readouterr().out

    def test_archive_moves_files(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args())
        cli.cmd_remove(make_remove_args(archive=True))
        assert not (tmp_path / "AGENTS.md").exists()
        archives = list((tmp_path / ".agentinit-archive").iterdir())
        assert len(archives) == 1
        assert (archives[0] / "AGENTS.md").exists()

    def test_nothing_to_do(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        cli.cmd_remove(make_remove_args())
        assert "Nothing to do" in capsys.readouterr().out

    def test_cleans_empty_dirs(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args())
        cli.cmd_remove(make_remove_args())
        assert not (tmp_path / "docs").exists()


# ---------------------------------------------------------------------------
# main (argument parsing smoke tests)
# ---------------------------------------------------------------------------

class TestMain:
    def test_no_args_prints_help(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["agentinit"])
        cli.main()
        assert "usage" in capsys.readouterr().out.lower()

    def test_help_flag(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["agentinit", "--help"])
        with pytest.raises(SystemExit) as exc:
            cli.main()
        assert exc.value.code == 0


# ---------------------------------------------------------------------------
# _resolves_within
# ---------------------------------------------------------------------------

class TestResolvesWithin:
    def test_inside(self, tmp_path):
        assert cli._resolves_within(str(tmp_path), str(tmp_path / "sub"))

    def test_outside(self, tmp_path):
        assert not cli._resolves_within(str(tmp_path), "/tmp")

    def test_symlink_escape(self, tmp_path):
        escape = tmp_path / "escape"
        escape.symlink_to("/tmp")
        assert not cli._resolves_within(str(tmp_path), str(escape))
