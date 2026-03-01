"""Tests for agentinit.cli."""

import argparse
import json
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
        assert conventions_idx < safe_defaults_idx < style_idx, \
            f"Safe Defaults should be between # Conventions and ## Style, got positions: " \
            f"Conventions={conventions_idx}, SafeDefaults={safe_defaults_idx}, Style={style_idx}"

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
        # No purpose provided → template placeholder text stays as-is
        assert "Describe what this project is for and expected outcomes." in content
        assert "TBD" not in content

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

    def test_yes_acts_as_force(self, tmp_path, monkeypatch):
        """--yes implies --force and overwrites existing files."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "AGENTS.md").write_text("old content")
        parser = cli.build_parser()
        args = parser.parse_args(["init", "--yes"])
        
        # Test the direct mapping in argparse
        assert args.yes is True
        
        # Test behavior inside cmd_init
        cli.cmd_init(args)
        assert "old content" not in (tmp_path / "AGENTS.md").read_text()
        assert args.force is True
        assert args.prompt is False

    def test_y_alias_acts_as_force(self, tmp_path, monkeypatch):
        """-y implies --force via argparse and cmd_init."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "AGENTS.md").write_text("old content")
        parser = cli.build_parser()
        args = parser.parse_args(["init", "-y"])
        
        # Test the alias mapping in argparse
        assert args.yes is True
        
        # Test behavior inside cmd_init
        cli.cmd_init(args)
        assert "old content" not in (tmp_path / "AGENTS.md").read_text()
        assert args.force is True
        assert args.prompt is False


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
        # Inject TBD manually (templates no longer contain TBD by default)
        (tmp_path / "AGENTS.md").write_text("# Agents\n\nSetup: TBD\n", encoding="utf-8")
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


class TestTemplatePackaging:
    """Verify that all expected template files ship with the package."""

    REQUIRED_TEMPLATES = [
        ".claude/rules/coding-style.md",
        ".claude/rules/testing.md",
        ".claude/rules/repo-map.md",
        ".contextlintrc.json",
        "AGENTS.md",
        "CLAUDE.md",
        "docs/PROJECT.md",
        "docs/CONVENTIONS.md",
    ]

    def test_template_files_exist(self):
        for rel in self.REQUIRED_TEMPLATES:
            path = os.path.join(cli.TEMPLATE_DIR, rel)
            assert os.path.isfile(path), f"Template file missing: {rel}"

    def test_new_templates_have_no_tbd(self):
        """None of the shipped templates should contain the literal string TBD."""
        for rel in cli.MANAGED_FILES:
            path = os.path.join(cli.TEMPLATE_DIR, rel)
            if not os.path.isfile(path):
                continue
            content = open(path, encoding="utf-8").read()
            assert "TBD" not in content, f"Template {rel} still contains TBD"


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
            # If no tomllib, it should not fail but fields remain as placeholders
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
        assert "- **Runtime:** (not configured)" in content
        assert "- Setup: (not configured)" in content


# ---------------------------------------------------------------------------
# cmd_lint
# ---------------------------------------------------------------------------


def make_lint_args(**kwargs):
    defaults = {"config": None, "format": "text", "no_dup": False, "root": None}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


class TestCmdLint:
    def _fill_tbd(self, root, files):
        for rel in files:
            path = root / rel
            if path.is_file():
                content = path.read_text(encoding="utf-8")
                path.write_text(content.replace("TBD", "done"), encoding="utf-8")

    def test_lint_clean_project_exits_0(self, tmp_path, monkeypatch):
        """agentinit init → agentinit lint returns 0 on a clean project."""
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args())
        self._fill_tbd(tmp_path, cli.MANAGED_FILES)
        # Rewrite AGENTS.md without broken refs
        (tmp_path / "AGENTS.md").write_text(
            "# Agents\n\nSee [project](docs/PROJECT.md).\n", encoding="utf-8"
        )
        with pytest.raises(SystemExit) as exc:
            cli.cmd_lint(make_lint_args())
        assert exc.value.code == 0

    def test_status_check_exits_1_on_broken_ref(self, tmp_path, monkeypatch, capsys):
        """Inject broken ref in .claude/rules/, verify status --check exits 1."""
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args())
        self._fill_tbd(tmp_path, cli.MANAGED_FILES)
        # Clean AGENTS.md of broken refs
        (tmp_path / "AGENTS.md").write_text(
            "# Agents\n\nSee [project](docs/PROJECT.md).\n", encoding="utf-8"
        )
        # Inject broken ref into a rules file
        rules_file = tmp_path / ".claude" / "rules" / "coding-style.md"
        rules_file.write_text(
            "# Style\n\nSee [missing](docs/NOPE.md) for details.\n",
            encoding="utf-8",
        )
        with pytest.raises(SystemExit) as exc:
            cli.cmd_status(make_status_args(check=True))
        assert exc.value.code == 1
        out = capsys.readouterr().out
        assert "contextlint" in out.lower() or "ERROR" in out

    def test_lint_format_json_valid(self, tmp_path, monkeypatch, capsys):
        """agentinit lint --format json produces valid JSON with expected keys."""
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args())
        self._fill_tbd(tmp_path, cli.MANAGED_FILES)
        (tmp_path / "AGENTS.md").write_text(
            "# Agents\n\nSee [project](docs/PROJECT.md).\n", encoding="utf-8"
        )
        # Flush init output before capturing lint output
        capsys.readouterr()
        with pytest.raises(SystemExit):
            cli.cmd_lint(make_lint_args(format="json"))
        out = capsys.readouterr().out
        data = json.loads(out)
        assert "diagnostics" in data
        assert "summary" in data
        assert "file_sizes" in data
        assert isinstance(data["diagnostics"], list)
        assert isinstance(data["summary"]["total"], int)


# ---------------------------------------------------------------------------
# cmd_add
# ---------------------------------------------------------------------------


def make_add_args(**kwargs):
    defaults = {"type": "skill", "name": "code-reviewer", "list": False, "force": False}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


class TestCmdAdd:
    def test_add_skill_fallback_dedup(self, tmp_path, monkeypatch, capsys):
        """add skill fallback/dedup works when a skill exists in .claude/skills/ but .agents/ exists too."""
        monkeypatch.chdir(tmp_path)
        # Create .agents dir
        (tmp_path / ".agents").mkdir()
        # Create existing skill in .claude
        skill_dir = tmp_path / ".claude" / "skills" / "code-reviewer"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("existing skill")

        args = make_add_args()
        cli.cmd_add(args)
        
        out = capsys.readouterr().err
        assert "already exists" in out
        
        # ensure it didn't create in .agents/
        assert not (tmp_path / ".agents" / "skills" / "code-reviewer").exists()

    def test_add_mcp_github_updates_agents_md_once(self, tmp_path, monkeypatch):
        """add mcp github updates AGENTS.md with a link only once."""
        monkeypatch.chdir(tmp_path)
        # Init base structure
        cli.cmd_init(make_init_args())
        
        # Add mcp github
        args = make_add_args(type="mcp", name="github")
        cli.cmd_add(args)
        
        # Read content
        content1 = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        assert "- `.agents/mcp-github.md`" in content1
        
        # Count occurrences
        count1 = content1.count("- `.agents/mcp-github.md`")
        assert count1 == 1

        # Delete the created file to force it to run again
        (tmp_path / ".agents" / "mcp-github.md").unlink()
        
        # Add mcp github again
        cli.cmd_add(args)
        
        # Read content again
        content2 = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        count2 = content2.count("- `.agents/mcp-github.md`")
        
        # Still only 1
        assert count2 == 1


class TestPrintNextSteps:
    def test_print_next_steps_with_tty_all_files(self, monkeypatch, capsys, tmp_path):
        import sys
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
        from agentinit import cli
        
        # Create all dummy files/dirs
        (tmp_path / "AGENTS.md").touch()
        (tmp_path / "CLAUDE.md").touch()
        (tmp_path / "GEMINI.md").touch()
        (tmp_path / "docs").mkdir()
        (tmp_path / ".agents").mkdir()
        
        cli._print_next_steps(str(tmp_path))
        out, _ = capsys.readouterr()
        assert "Some agents only read tracked files." in out
        assert "git add AGENTS.md CLAUDE.md GEMINI.md docs/ .agents/" in out

    def test_print_next_steps_with_tty_partial_files(self, monkeypatch, capsys, tmp_path):
        import sys
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
        from agentinit import cli
        
        # Create only some dummy files/dirs
        (tmp_path / "AGENTS.md").touch()
        (tmp_path / "CLAUDE.md").touch()
        (tmp_path / "docs").mkdir()
        # Missing GEMINI.md and .agents/
        
        cli._print_next_steps(str(tmp_path))
        out, _ = capsys.readouterr()
        assert "Some agents only read tracked files." in out
        assert "git add AGENTS.md CLAUDE.md docs/" in out
        assert ".agents" not in out
        assert "GEMINI.md" not in out

    def test_print_next_steps_without_tty(self, monkeypatch, capsys, tmp_path):
        import sys
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys.stdout, "isatty", lambda: False)
        from agentinit import cli
        
        (tmp_path / "AGENTS.md").touch()
        
        cli._print_next_steps(str(tmp_path))
        out, _ = capsys.readouterr()
        assert "Some agents only read tracked files." not in out
        assert "git add" not in out

    def test_print_next_steps_no_files(self, monkeypatch, capsys, tmp_path):
        import sys
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
        from agentinit import cli

        # Create no files
        cli._print_next_steps(str(tmp_path))
        out, _ = capsys.readouterr()
        assert "Some agents only read tracked files." not in out
        assert "git add" not in out


# ---------------------------------------------------------------------------
# Version fallback
# ---------------------------------------------------------------------------


class TestVersionFallback:
    def test_version_fallback_when_not_installed(self, monkeypatch):
        """build_parser should not crash when package is not installed."""
        import importlib.metadata

        original = importlib.metadata.version

        def fake_version(name):
            if name == "agentinit":
                raise importlib.metadata.PackageNotFoundError(name)
            return original(name)

        monkeypatch.setattr(importlib.metadata, "version", fake_version)
        parser = cli.build_parser()
        assert parser is not None
        # --version should show "dev"
        with pytest.raises(SystemExit) as exc:
            parser.parse_args(["--version"])
        assert exc.value.code == 0


# ---------------------------------------------------------------------------
# TOML detection warning on Python 3.10
# ---------------------------------------------------------------------------


class TestDetectTomlWarning:
    def test_warns_when_tomllib_unavailable(self, tmp_path, monkeypatch, capsys):
        """Print warning when tomllib is missing and TOML manifests exist."""
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args())
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "test"\n', encoding="utf-8"
        )

        # Simulate tomllib not being available
        import builtins

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "tomllib":
                raise ImportError("no tomllib")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)

        args = make_init_args(detect=True)
        cli.apply_updates(str(tmp_path), args)

        err = capsys.readouterr().err
        assert "TOML detection" in err
        assert "pyproject.toml" in err
        assert "3.11" in err

    def test_no_warning_without_toml_files(self, tmp_path, monkeypatch, capsys):
        """No warning when no TOML manifests exist."""
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args())

        import builtins

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "tomllib":
                raise ImportError("no tomllib")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)

        args = make_init_args(detect=True)
        cli.apply_updates(str(tmp_path), args)

        err = capsys.readouterr().err
        assert "TOML detection" not in err


# ---------------------------------------------------------------------------
# Commands section markers
# ---------------------------------------------------------------------------


class TestCommandsMarkers:
    def test_wizard_commands_replace_between_markers(self, tmp_path, monkeypatch):
        """Wizard commands should replace content between markers."""
        cli.copy_template(str(tmp_path))
        args = make_args(prompt=True, purpose="Test project")
        inputs = iter(["", "", "make build, make test, make run"])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        cli.apply_updates(str(tmp_path), args)

        content = (tmp_path / "docs" / "PROJECT.md").read_text(encoding="utf-8")
        assert "- make build" in content
        assert "- make test" in content
        assert "- make run" in content
        # Between markers should have no "(not configured)"
        start = content.index("<!-- agentinit:commands:start -->")
        end = content.index("<!-- agentinit:commands:end -->")
        between = content[start:end]
        assert "(not configured)" not in between

    def test_markers_survive_whitespace_changes(self, tmp_path):
        """Commands replacement works even with extra whitespace in template."""
        cli.copy_template(str(tmp_path))
        project_path = tmp_path / "docs" / "PROJECT.md"
        content = project_path.read_text(encoding="utf-8")
        # Add extra whitespace around the commands section
        content = content.replace("## Commands\n", "## Commands\n\n")
        project_path.write_text(content, encoding="utf-8")

        new_body = "- npm install\n- npm test"
        result = cli._replace_commands_section(content, new_body)
        assert "- npm install" in result
        assert "- npm test" in result
        assert "<!-- agentinit:commands:start -->" in result
        assert "<!-- agentinit:commands:end -->" in result

    def test_detect_updates_within_markers(self, tmp_path, monkeypatch):
        """--detect should update individual command lines within markers."""
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args())
        (tmp_path / "go.mod").write_text(
            "module myapp\n\ngo 1.22\n", encoding="utf-8"
        )
        args = make_init_args(detect=True)
        cli.apply_updates(str(tmp_path), args)

        content = (tmp_path / "docs" / "PROJECT.md").read_text(encoding="utf-8")
        assert "<!-- agentinit:commands:start -->" in content
        assert "- Test: go test ./..." in content
        assert "<!-- agentinit:commands:end -->" in content


# ---------------------------------------------------------------------------
# Wizard skip with --purpose
# ---------------------------------------------------------------------------


class TestWizardPurposeSkip:
    def test_purpose_skips_wizard_on_tty(self, tmp_path, monkeypatch):
        """--purpose should not trigger the wizard even on a TTY."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        monkeypatch.setattr(sys, "argv", ["agentinit", "init", "--purpose", "My project"])
        # If wizard ran, it would call input() and fail since we don't mock it
        cli.main()
        content = (tmp_path / "docs" / "PROJECT.md").read_text(encoding="utf-8")
        assert "My project" in content

    def test_hint_when_fields_missing(self, tmp_path, monkeypatch, capsys):
        """Print hint about --prompt when wizard is skipped and fields remain."""
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args(purpose="My project"))
        out = capsys.readouterr().out
        assert "Run with --prompt to fill interactively." in out

    def test_no_wizard_no_purpose_no_tty(self, tmp_path, monkeypatch):
        """Without TTY and without --purpose, wizard should not run."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
        monkeypatch.setattr(sys, "argv", ["agentinit", "init"])
        cli.main()
        assert (tmp_path / "AGENTS.md").exists()
