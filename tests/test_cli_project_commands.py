"""Tests for agentinit.cli."""

import sys
from pathlib import Path

import pytest

import agentinit.cli as cli
from tests.helpers import (
    make_args,
    make_init_args,
    make_remove_args,
    make_sync_args,
)


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

    def test_empty_template_no_orphan_dir(self, tmp_path, monkeypatch):
        empty_template = tmp_path / "empty_template"
        empty_template.mkdir()
        monkeypatch.setattr(cli, "TEMPLATE_DIR", str(empty_template))
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
            "llms.txt",
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

    def test_new_with_fastapi_skeleton_copies_boilerplate(self, tmp_path):
        args = make_args(
            name="api-proj",
            dir=str(tmp_path),
            skeleton="fastapi",
            yes=True,
        )
        cli.cmd_new(args)
        proj = tmp_path / "api-proj"
        assert (proj / "pyproject.toml").exists()
        assert (proj / "main.py").exists()
        assert (proj / "tests" / "conftest.py").exists()
        assert (proj / "tests" / "test_todos.py").exists()

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
            "llms.txt",
        ]
        agents = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        llms = (tmp_path / "llms.txt").read_text(encoding="utf-8")
        assert "docs/STATE.md" not in agents
        assert "docs/TODO.md" not in agents
        assert "docs/DECISIONS.md" not in agents
        assert ".claude/rules/" not in agents
        assert "## Key Files" in llms
        assert "docs/STATE.md" in llms
        assert "docs/TODO.md" in llms
        assert "docs/DECISIONS.md" in llms
        assert "(missing in this profile)" in llms

    def test_minimal_with_purpose(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args(minimal=True, purpose="Init Purpose"))
        content = (tmp_path / "docs" / "PROJECT.md").read_text(encoding="utf-8")
        assert "Init Purpose" in content
        assert "Describe what this project is for" not in content

    def test_minimal_claude_router_uses_direct_imports(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args(minimal=True))

        claude = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")

        assert "@AGENTS.md" in claude
        assert "@docs/PROJECT.md" in claude
        assert "@docs/CONVENTIONS.md" in claude

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

    def test_full_routers_use_direct_imports(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args())

        claude = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
        gemini = (tmp_path / "GEMINI.md").read_text(encoding="utf-8")

        for text in (claude, gemini):
            assert "@AGENTS.md" in text
            assert "@docs/PROJECT.md" in text
            assert "@docs/CONVENTIONS.md" in text
            assert "@docs/TODO.md" in text
            assert "@docs/DECISIONS.md" in text
            assert "@docs/STATE.md" in text

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
            "llms.txt",
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


class TestCmdSync:
    def test_sync_updates_drifted_router_files(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args())

        (tmp_path / "CLAUDE.md").write_text("custom", encoding="utf-8")
        (tmp_path / ".github" / "copilot-instructions.md").unlink()

        cli.cmd_sync(make_sync_args())

        template_claude = (Path(cli.TEMPLATE_DIR) / "CLAUDE.md").read_text(
            encoding="utf-8"
        )
        template_copilot = (
            Path(cli.TEMPLATE_DIR) / ".github" / "copilot-instructions.md"
        ).read_text(encoding="utf-8")

        assert (tmp_path / "CLAUDE.md").read_text(encoding="utf-8") == template_claude
        assert (tmp_path / ".github" / "copilot-instructions.md").read_text(
            encoding="utf-8"
        ) == template_copilot

    def test_sync_check_exits_1_on_drift(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args())
        (tmp_path / "GEMINI.md").write_text("drift", encoding="utf-8")

        with pytest.raises(SystemExit) as exc:
            cli.cmd_sync(make_sync_args(check=True))
        assert exc.value.code == 1

    def test_sync_check_exits_0_when_in_sync(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args())

        with pytest.raises(SystemExit) as exc:
            cli.cmd_sync(make_sync_args(check=True))
        assert exc.value.code == 0

    def test_sync_requires_agents_md(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with pytest.raises(SystemExit) as exc:
            cli.cmd_sync(make_sync_args())
        assert exc.value.code == 1

    def test_sync_command_from_main_with_root(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args())
        (tmp_path / "CLAUDE.md").write_text("drift", encoding="utf-8")
        monkeypatch.setattr(
            sys, "argv", ["agentinit", "sync", "--root", str(tmp_path), "--check"]
        )

        with pytest.raises(SystemExit) as exc:
            cli.main()
        assert exc.value.code == 1


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

    def test_refresh_llms_command(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args(purpose="My project"))
        monkeypatch.setattr(sys, "argv", ["agentinit", "refresh-llms"])
        cli.main()
        out = capsys.readouterr().out
        assert "Regenerated llms.txt in " in out

    def test_refresh_alias_command(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args(purpose="My project"))
        monkeypatch.setattr(sys, "argv", ["agentinit", "refresh"])
        cli.main()
        out = capsys.readouterr().out
        assert "Regenerated llms.txt in " in out


class TestResolvesWithin:
    def test_inside(self, tmp_path):
        assert cli._resolves_within(str(tmp_path), str(tmp_path / "sub"))

    def test_outside(self, tmp_path):
        assert not cli._resolves_within(str(tmp_path), "/tmp")

    def test_symlink_escape(self, tmp_path):
        escape = tmp_path / "escape"
        escape.symlink_to("/tmp")
        assert not cli._resolves_within(str(tmp_path), str(escape))


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


class TestWizardPurposeSkip:
    def test_purpose_skips_wizard_on_tty(self, tmp_path, monkeypatch):
        """--purpose should not trigger the wizard even on a TTY."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        monkeypatch.setattr(
            sys, "argv", ["agentinit", "init", "--purpose", "My project"]
        )
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
