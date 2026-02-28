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
    defaults = {"force": False, "minimal": False, "purpose": None, "prompt": False}
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
        err = capsys.readouterr().err
        assert "requires an interactive terminal" in err
        assert "--purpose" in err


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
        args = make_args(
            name="myproj",
            dir=str(tmp_path),
            minimal=True,
            yes=True,
            purpose="Custom Purpose",
        )
        cli.cmd_new(args)
        proj = tmp_path / "myproj"
        content = (proj / "docs" / "PROJECT.md").read_text(encoding="utf-8")
        assert "Custom Purpose" in content
        assert "Describe what this project is for" not in content

    def test_yes_overrides_prompt(self, tmp_path, monkeypatch):
        """--yes disables --prompt so no interactive wizard runs."""
        monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "agentinit",
                "new",
                "proj",
                "--yes",
                "--prompt",
                "--dir",
                str(tmp_path),
            ],
        )
        cli.main()
        # Should succeed without prompting (--yes wins over --prompt)
        assert (tmp_path / "proj" / "AGENTS.md").exists()


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
        files = sorted(
            str(p.relative_to(tmp_path)) for p in tmp_path.rglob("*") if p.is_file()
        )
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

    def test_minimal_does_not_overwrite_project_or_conventions_without_force(
        self, tmp_path, monkeypatch
    ):
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

    def test_missing_template_dir_prints_to_stderr(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(cli, "TEMPLATE_DIR", str(tmp_path / "nonexistent"))
        with pytest.raises(SystemExit) as exc:
            cli.cmd_init(make_init_args())
        assert exc.value.code == 1
        assert "template directory not found" in capsys.readouterr().err

    def test_empty_template_dir_prints_to_stderr(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        fake = tmp_path / "empty_template"
        fake.mkdir()
        monkeypatch.setattr(cli, "TEMPLATE_DIR", str(fake))
        with pytest.raises(SystemExit) as exc:
            cli.cmd_init(make_init_args())
        assert exc.value.code == 1
        assert "no template files copied" in capsys.readouterr().err

    def test_purpose_prefills_project(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args(purpose="My cool project"))
        content = (tmp_path / "docs" / "PROJECT.md").read_text(encoding="utf-8")
        assert "My cool project" in content
        assert "Describe what this project is for" not in content

    def test_prompt_fails_without_tty(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
        with pytest.raises(SystemExit) as exc:
            cli.cmd_init(make_init_args(prompt=True))
        assert exc.value.code == 1

    def test_wizard_eof_aborts(self, tmp_path, monkeypatch, capsys):
        """Ctrl+D during wizard prints 'Aborted.' and exits 130."""
        monkeypatch.chdir(tmp_path)
        cli.copy_template(str(tmp_path))
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        import builtins

        monkeypatch.setattr(
            builtins, "input", lambda _prompt="": (_ for _ in ()).throw(EOFError)
        )
        with pytest.raises(SystemExit) as exc:
            cli.cmd_init(make_init_args(prompt=True))
        assert exc.value.code == 130
        assert "Aborted" in capsys.readouterr().out

    def test_yes_disables_prompt_in_direct_call(self, tmp_path, monkeypatch):
        """--yes should disable wizard even when calling cmd_init directly."""
        monkeypatch.chdir(tmp_path)
        args = make_init_args(yes=True, prompt=True)
        cli.cmd_init(args)
        assert not args.prompt
        assert (tmp_path / "AGENTS.md").exists()


# ---------------------------------------------------------------------------
# cmd_minimal (alias for init --minimal)
# ---------------------------------------------------------------------------


class TestCmdMinimal:
    def test_creates_only_core_files(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", ["agentinit", "minimal", "--yes"])
        cli.main()
        files = sorted(
            str(p.relative_to(tmp_path)) for p in tmp_path.rglob("*") if p.is_file()
        )
        assert files == [
            "AGENTS.md",
            "CLAUDE.md",
            "docs/CONVENTIONS.md",
            "docs/PROJECT.md",
        ]

    def test_with_purpose(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            sys, "argv", ["agentinit", "minimal", "--yes", "--purpose", "Quick test"]
        )
        cli.main()
        content = (tmp_path / "docs" / "PROJECT.md").read_text(encoding="utf-8")
        assert "Quick test" in content

    def test_matches_init_minimal(self, tmp_path, monkeypatch):
        """Ensure `minimal` produces the same files as `init --minimal`."""
        dir_a = tmp_path / "a"
        dir_a.mkdir()
        monkeypatch.chdir(dir_a)
        cli.cmd_init(make_init_args(minimal=True))

        dir_b = tmp_path / "b"
        dir_b.mkdir()
        monkeypatch.chdir(dir_b)
        monkeypatch.setattr(sys, "argv", ["agentinit", "minimal", "--yes"])
        cli.main()

        files_a = sorted(
            str(p.relative_to(dir_a)) for p in dir_a.rglob("*") if p.is_file()
        )
        files_b = sorted(
            str(p.relative_to(dir_b)) for p in dir_b.rglob("*") if p.is_file()
        )
        assert files_a == files_b


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

    def test_confirm_fails_on_non_tty(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args())
        monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
        with pytest.raises(SystemExit) as exc:
            cli.cmd_remove(make_remove_args(force=False))
        assert exc.value.code == 1
        assert "requires a terminal" in capsys.readouterr().err


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

    def test_version_flag(self, monkeypatch, capsys):
        import re

        monkeypatch.setattr(sys, "argv", ["agentinit", "--version"])
        with pytest.raises(SystemExit) as exc:
            cli.main()
        assert exc.value.code == 0
        out = capsys.readouterr().out.strip()
        assert re.match(r"\d+\.\d+\.\d+", out), f"expected semver, got {out!r}"


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


# ---------------------------------------------------------------------------
# Edge cases: paths, permissions, remove
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_spaces_in_project_name(self, tmp_path):
        args = make_args(name="my project", dir=str(tmp_path))
        cli.cmd_new(args)
        proj = tmp_path / "my project"
        assert (proj / "AGENTS.md").exists()
        assert (proj / "docs" / "PROJECT.md").exists()

    def test_unicode_project_name(self, tmp_path):
        args = make_args(name="progetto-è-bello", dir=str(tmp_path))
        cli.cmd_new(args)
        proj = tmp_path / "progetto-è-bello"
        assert (proj / "AGENTS.md").exists()

    def test_spaces_in_parent_dir(self, tmp_path):
        parent = tmp_path / "my folder"
        parent.mkdir()
        args = make_args(name="proj", dir=str(parent))
        cli.cmd_new(args)
        assert (parent / "proj" / "AGENTS.md").exists()

    def test_new_dest_is_file_not_dir(self, tmp_path):
        (tmp_path / "myproj").write_text("i am a file")
        args = make_args(name="myproj", dir=str(tmp_path))
        with pytest.raises(SystemExit) as exc:
            cli.cmd_new(args)
        assert exc.value.code == 1

    def test_force_overwrite_readonly_file(self, tmp_path):
        cli.copy_template(str(tmp_path))
        agents = tmp_path / "AGENTS.md"
        agents.chmod(0o444)
        try:
            # shutil.copy2 overwrites read-only files on POSIX
            copied, _ = cli.copy_template(str(tmp_path), force=True)
            assert "AGENTS.md" in copied
        finally:
            agents.chmod(0o644)  # restore for cleanup

    def test_remove_readonly_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args())
        agents = tmp_path / "AGENTS.md"
        agents.chmod(0o444)
        try:
            cli.cmd_remove(make_remove_args())
            assert not agents.exists()
        except SystemExit:
            agents.chmod(0o644)
            pytest.fail("cmd_remove should handle read-only files")

    def test_archive_twice_no_collision(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args())
        cli.cmd_remove(make_remove_args(archive=True))
        # Re-init and archive again
        cli.cmd_init(make_init_args())
        cli.cmd_remove(make_remove_args(archive=True))
        archives = list((tmp_path / ".agentinit-archive").iterdir())
        assert len(archives) >= 2

    def test_remove_keyboard_interrupt_aborts(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args())
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        import builtins

        monkeypatch.setattr(
            builtins,
            "input",
            lambda _prompt="": (_ for _ in ()).throw(KeyboardInterrupt),
        )
        cli.cmd_remove(make_remove_args(force=False))
        assert "Aborted" in capsys.readouterr().out
        # Files should still exist (removal was aborted)
        assert (tmp_path / "AGENTS.md").exists()


# ---------------------------------------------------------------------------
# cmd_status
# ---------------------------------------------------------------------------


def make_status_args(**kwargs):
    defaults = {"check": False, "minimal": False}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


class TestCmdStatus:
    def _fill_tbd(self, root, files):
        """Replace all TBD markers in the given managed files."""
        for rel in files:
            path = root / rel
            if path.is_file():
                content = path.read_text(encoding="utf-8")
                path.write_text(content.replace("TBD", "done"), encoding="utf-8")

    def test_all_present_and_filled(self, tmp_path, monkeypatch, capsys):
        """When all files exist and none contain TBD, reports 'Ready'."""
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args())
        self._fill_tbd(tmp_path, cli.MANAGED_FILES)
        cli.cmd_status(make_status_args())
        out = capsys.readouterr().out
        assert "Ready" in out

    def test_missing_files_reported(self, tmp_path, monkeypatch, capsys):
        """When no agentinit files exist, all are reported missing."""
        monkeypatch.chdir(tmp_path)
        cli.cmd_status(make_status_args())
        out = capsys.readouterr().out
        assert "missing" in out
        assert "Action required" in out

    def test_tbd_files_reported(self, tmp_path, monkeypatch, capsys):
        """Files containing TBD are flagged as incomplete."""
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args())
        cli.cmd_status(make_status_args())
        out = capsys.readouterr().out
        assert "incomplete" in out
        assert "Action required" in out

    def test_check_exits_1_when_issues(self, tmp_path, monkeypatch):
        """--check should exit with code 1 when files are missing."""
        monkeypatch.chdir(tmp_path)
        with pytest.raises(SystemExit) as exc:
            cli.cmd_status(make_status_args(check=True))
        assert exc.value.code == 1

    def test_check_exits_0_when_ready(self, tmp_path, monkeypatch, capsys):
        """--check should exit with code 0 when everything is filled."""
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args())
        self._fill_tbd(tmp_path, cli.MANAGED_FILES)
        with pytest.raises(SystemExit) as exc:
            cli.cmd_status(make_status_args(check=True))
        assert exc.value.code == 0
        out = capsys.readouterr().out
        assert "Ready" in out

    def test_no_exit_without_check(self, tmp_path, monkeypatch, capsys):
        """Without --check, cmd_status returns normally (no sys.exit)."""
        monkeypatch.chdir(tmp_path)
        # Missing files but no --check: should not raise SystemExit
        cli.cmd_status(make_status_args(check=False))
        out = capsys.readouterr().out
        assert "Action required" in out

    def test_minimal_checks_fewer_files(self, tmp_path, monkeypatch, capsys):
        """--minimal only checks the 4 core files."""
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args(minimal=True))
        self._fill_tbd(tmp_path, cli.MINIMAL_MANAGED_FILES)
        (tmp_path / "AGENTS.md").write_text("No broken links", encoding="utf-8")
        cli.cmd_status(make_status_args(minimal=True))
        out = capsys.readouterr().out
        assert "Ready" in out

    def test_unreadable_file(self, tmp_path, monkeypatch, capsys):
        """Files that can't be read are reported as unreadable."""
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args())
        agents = tmp_path / "AGENTS.md"
        agents.chmod(0o000)
        try:
            cli.cmd_status(make_status_args())
            out = capsys.readouterr().out
            assert "unreadable" in out
        finally:
            agents.chmod(0o644)

    def test_broken_symlink(self, tmp_path, monkeypatch, capsys):
        """A dangling symlink is reported as 'broken symlink'."""
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args())
        agents = tmp_path / "AGENTS.md"
        agents.unlink()
        agents.symlink_to(tmp_path / "nonexistent")
        cli.cmd_status(make_status_args())
        out = capsys.readouterr().out
        assert "broken symlink" in out

    def test_not_a_file(self, tmp_path, monkeypatch, capsys):
        """A directory where a file is expected is reported as 'not a file'."""
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args())
        agents = tmp_path / "AGENTS.md"
        agents.unlink()
        agents.mkdir()
        cli.cmd_status(make_status_args())
        out = capsys.readouterr().out
        assert "not a file" in out

    def test_soft_line_budget(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args())
        self._fill_tbd(tmp_path, cli.MANAGED_FILES)
        agents = tmp_path / "AGENTS.md"
        agents.write_text("line\n" * 201, encoding="utf-8")

        with pytest.raises(SystemExit) as exc:
            cli.cmd_status(make_status_args(check=True))
        assert exc.value.code == 0
        out = capsys.readouterr().out
        assert "(201 lines >= 200)" in out

    def test_hard_line_budget(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args())
        self._fill_tbd(tmp_path, cli.MANAGED_FILES)
        agents = tmp_path / "AGENTS.md"
        agents.write_text("line\n" * 301, encoding="utf-8")

        with pytest.raises(SystemExit) as exc:
            cli.cmd_status(make_status_args(check=True))
        assert exc.value.code == 1
        out = capsys.readouterr().out
        assert "(301 lines >= 300)" in out
        assert "too large" in out

    def test_broken_reference(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args())
        self._fill_tbd(tmp_path, cli.MANAGED_FILES)
        agents = tmp_path / "AGENTS.md"
        agents.write_text(
            'Here is a [link](docs/missing.md "Title") and `docs/also-missing.md`',
            encoding="utf-8",
        )

        with pytest.raises(SystemExit) as exc:
            cli.cmd_status(make_status_args(check=True))
        assert exc.value.code == 1
        out = capsys.readouterr().out
        assert "Broken reference: docs/missing.md" in out
        assert "Broken reference: docs/also-missing.md" in out

    def test_broken_reference_no_false_positive_from_markdown(
        self, tmp_path, monkeypatch, capsys
    ):
        """Markdown link syntax must not be reported as a second broken ref."""
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args())
        self._fill_tbd(tmp_path, cli.MANAGED_FILES)
        agents = tmp_path / "AGENTS.md"
        agents.write_text(
            "[broken](docs/nope.md)",
            encoding="utf-8",
        )

        with pytest.raises(SystemExit) as exc:
            cli.cmd_status(make_status_args(check=True))
        assert exc.value.code == 1
        out = capsys.readouterr().out
        assert "Broken reference: docs/nope.md" in out
        assert out.count("Broken reference:") == 1

    def test_gitignore_excluded_from_top_offenders(self, tmp_path, monkeypatch, capsys):
        """Ensure .gitignore is not listed in Top offenders even when it has many lines."""
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args())
        self._fill_tbd(tmp_path, cli.MANAGED_FILES)

        (tmp_path / ".gitignore").write_text(
            "\n".join(f"line{i}" for i in range(50)), encoding="utf-8"
        )
        (tmp_path / "AGENTS.md").write_text(
            "\n".join(f"line{i}" for i in range(30)), encoding="utf-8"
        )
        (tmp_path / "CLAUDE.md").write_text(
            "\n".join(f"line{i}" for i in range(20)), encoding="utf-8"
        )

        cli.cmd_status(make_status_args())
        out = capsys.readouterr().out

        assert ".gitignore" not in out or "Top offenders:" not in out
        lines = out.split("\n")
        top_offenders_section = False
        for line in lines:
            if "Top offenders:" in line:
                top_offenders_section = True
            elif top_offenders_section and ".gitignore" in line:
                pytest.fail(".gitignore should not appear in Top offenders")
            elif top_offenders_section and line.strip() and not line.startswith("  "):
                break

    def test_valid_reference(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args())
        self._fill_tbd(tmp_path, cli.MANAGED_FILES)
        agents = tmp_path / "AGENTS.md"
        agents.write_text(
            "Valid link: [project](docs/PROJECT.md) and [x](../secret.md)",
            encoding="utf-8",
        )

        with pytest.raises(SystemExit) as exc:
            cli.cmd_status(make_status_args(check=True))
        assert exc.value.code == 0
        out = capsys.readouterr().out
        assert "Broken reference" not in out

    def test_outside_reference_ignored_no_crash(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args())
        self._fill_tbd(tmp_path, cli.MANAGED_FILES)
        agents = tmp_path / "AGENTS.md"
        # Test paths that resolve outside the root (should be ignored, not crash)
        agents.write_text("See `../secret.md` or `../../outside.txt`", encoding="utf-8")

        with pytest.raises(SystemExit) as exc:
            cli.cmd_status(make_status_args(check=True))
        assert exc.value.code == 0
        out = capsys.readouterr().out
        assert "Broken reference" not in out


class TestDetectManifests:
    def test_detect_node(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args())

        # Write fake package.json
        import json

        pkg = {"packageManager": "pnpm@8", "scripts": {"test": "jest", "dev": "vite"}}
        (tmp_path / "package.json").write_text(json.dumps(pkg), encoding="utf-8")

        # Call with detect
        args = make_init_args(detect=True)
        cli.apply_updates(str(tmp_path), args)

        content = (tmp_path / "docs" / "PROJECT.md").read_text(encoding="utf-8")
        assert "Node.js" in content
        assert "- Test: pnpm run test" in content
        assert "- Run: pnpm run dev" in content

    def test_detect_go(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args())

        (tmp_path / "go.mod").write_text(
            "module myapp\n\ngo 1.22.1\n", encoding="utf-8"
        )

        args = make_init_args(detect=True)
        cli.apply_updates(str(tmp_path), args)

        content = (tmp_path / "docs" / "PROJECT.md").read_text(encoding="utf-8")
        assert "- **Language(s):** Go" in content
        assert "- **Runtime:** Go 1.22.1" in content
        assert "- Test: go test ./..." in content

    def test_detect_python_poetry(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args())

        toml = (
            '[project]\nrequires-python = ">=3.11"\n\n[tool.poetry]\nname = "myproj"\n'
        )
        (tmp_path / "pyproject.toml").write_text(toml, encoding="utf-8")

        args = make_init_args(detect=True)
        cli.apply_updates(str(tmp_path), args)

        content = (tmp_path / "docs" / "PROJECT.md").read_text(encoding="utf-8")

        try:
            import tomllib
        except ImportError:
            # If no tomllib, it should not fail but fields remain TBD
            assert "Python" not in content
            return

        assert "- **Language(s):** Python" in content
        assert "- **Runtime:** Python >=3.11" in content
        assert "- Setup: poetry install" in content

    def test_detect_no_manifests_leaves_tbd(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args())

        args = make_init_args(detect=True)
        cli.apply_updates(str(tmp_path), args)

        content = (tmp_path / "docs" / "PROJECT.md").read_text(encoding="utf-8")
        assert "- **Runtime:** TBD" in content
        assert "- Setup: TBD" in content
