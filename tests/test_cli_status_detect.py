"""Tests for status, detect, and template packaging."""

import json
import os
import sys

import pytest

import agentinit.cli as cli
from tests.helpers import (
    fill_tbd,
    make_args,
    make_init_args,
    make_status_args,
)


class TestCmdStatus:
    def test_all_present_and_filled(self, tmp_path, monkeypatch, capsys):
        """When all files exist and none contain TBD, reports 'Ready'."""
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args())
        fill_tbd(tmp_path, cli.MANAGED_FILES)
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
        (tmp_path / "AGENTS.md").write_text(
            "# Agents\n\nSetup: TBD\n", encoding="utf-8"
        )
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

    def test_check_exits_1_when_contextlint_unavailable(
        self, tmp_path, monkeypatch, capsys
    ):
        """--check should fail closed when contextlint cannot be loaded."""
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args())
        fill_tbd(tmp_path, cli.MANAGED_FILES)

        def _boom():
            raise RuntimeError("simulated contextlint failure")

        monkeypatch.setattr("agentinit.contextlint_adapter.get_checks_module", _boom)

        with pytest.raises(SystemExit) as exc:
            cli.cmd_status(make_status_args(check=True))
        assert exc.value.code == 1
        err = capsys.readouterr().err
        assert "contextlint checks unavailable" in err

    def test_check_exits_0_when_ready(self, tmp_path, monkeypatch, capsys):
        """--check should exit with code 0 when everything is filled."""
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args())
        fill_tbd(tmp_path, cli.MANAGED_FILES)
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
        """--minimal only checks the minimal core files."""
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args(minimal=True))
        fill_tbd(tmp_path, cli.MINIMAL_MANAGED_FILES)
        with pytest.raises(SystemExit) as exc:
            cli.cmd_status(make_status_args(minimal=True, check=True))
        assert exc.value.code == 0
        out = capsys.readouterr().out
        assert "Ready" in out
        assert "Broken reference" not in out

    def test_minimal_status_ignores_non_core_contextlint_errors(
        self, tmp_path, monkeypatch, capsys
    ):
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args(minimal=True))
        fill_tbd(tmp_path, cli.MINIMAL_MANAGED_FILES)
        (tmp_path / "docs" / "GUIDE.md").write_text(
            "See [missing](missing.md)\n",
            encoding="utf-8",
        )

        with pytest.raises(SystemExit) as exc:
            cli.cmd_status(make_status_args(minimal=True, check=True))

        assert exc.value.code == 0
        out = capsys.readouterr().out
        assert "docs/GUIDE.md" not in out
        assert "Ready" in out

    def test_minimal_profile_auto_detected_without_flag(
        self, tmp_path, monkeypatch, capsys
    ):
        """A scaffolded minimal project should not require repeating --minimal."""
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args(minimal=True))
        fill_tbd(tmp_path, cli.MINIMAL_MANAGED_FILES)

        with pytest.raises(SystemExit) as exc:
            cli.cmd_status(make_status_args(check=True))
        assert exc.value.code == 0
        out = capsys.readouterr().out
        assert "Profile: minimal (auto-detected)" in out
        assert "Ready" in out

    def test_core_only_files_without_minimal_markers_still_fail_full_check(
        self, tmp_path, monkeypatch, capsys
    ):
        """Auto-detection should rely on scaffold markers, not just missing files."""
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args(minimal=True))
        fill_tbd(tmp_path, cli.MINIMAL_MANAGED_FILES)

        agents = tmp_path / "AGENTS.md"
        llms = tmp_path / "llms.txt"
        agents.write_text(
            agents.read_text(encoding="utf-8")
            .replace("<!-- agentinit:profile=minimal -->\n", "")
            .replace(
                "Primary entry point for coding agents in minimal mode.",
                "Primary entry point.",
            ),
            encoding="utf-8",
        )
        llms.write_text(
            llms.read_text(encoding="utf-8")
            .replace(" (missing in this profile)", "")
            .replace(
                "[docs/STATE.md](docs/STATE.md): Current State & Focus",
                "[docs/STATE.md](docs/STATE.md): State",
            ),
            encoding="utf-8",
        )

        with pytest.raises(SystemExit) as exc:
            cli.cmd_status(make_status_args(check=True))
        assert exc.value.code == 1
        out = capsys.readouterr().out
        assert "Profile: minimal" not in out
        assert "Action required" in out

    def test_full_project_note_with_minimal_phrase_does_not_trigger_auto_detect(
        self, tmp_path, monkeypatch, capsys
    ):
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args())

        agents = tmp_path / "AGENTS.md"
        agents.write_text(
            agents.read_text(encoding="utf-8")
            + "\nNote: string (minimal profile) for docs example.\n",
            encoding="utf-8",
        )
        (tmp_path / "GEMINI.md").unlink()

        with pytest.raises(SystemExit) as exc:
            cli.cmd_status(make_status_args(check=True))
        assert exc.value.code == 1
        out = capsys.readouterr().out
        assert "Profile: minimal" not in out
        assert "GEMINI.md (missing)" in out

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
        fill_tbd(tmp_path, cli.MANAGED_FILES)
        agents = tmp_path / "AGENTS.md"
        agents.write_text("line\n" * 201, encoding="utf-8")

        with pytest.raises(SystemExit) as exc:
            cli.cmd_status(make_status_args(check=True))
        assert exc.value.code == 0
        out = capsys.readouterr().out
        assert "(201 lines >= 200)" in out

    def test_contextlintrc_above_300_is_warning_only(
        self, tmp_path, monkeypatch, capsys
    ):
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args())
        fill_tbd(tmp_path, cli.MANAGED_FILES)
        config = tmp_path / ".contextlintrc.json"
        config.write_text("line\n" * 301, encoding="utf-8")

        with pytest.raises(SystemExit) as exc:
            cli.cmd_status(make_status_args(check=True))
        assert exc.value.code == 0
        out = capsys.readouterr().out
        assert ".contextlintrc.json (301 lines >= 200)" in out
        assert "too large" not in out

    def test_hard_line_budget(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args())
        fill_tbd(tmp_path, cli.MANAGED_FILES)
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
        fill_tbd(tmp_path, cli.MANAGED_FILES)
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
        fill_tbd(tmp_path, cli.MANAGED_FILES)
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
        fill_tbd(tmp_path, cli.MANAGED_FILES)

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
        fill_tbd(tmp_path, cli.MANAGED_FILES)
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
        fill_tbd(tmp_path, cli.MANAGED_FILES)
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
        "minimal/AGENTS.md",
        "minimal/CLAUDE.md",
        "minimal/llms.txt",
        "skeletons/fastapi/pyproject.toml",
        "skeletons/fastapi/main.py",
        "skeletons/fastapi/tests/conftest.py",
        "skeletons/fastapi/tests/test_todos.py",
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
            import tomllib  # noqa: F401
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

    def test_detect_from_purpose_fastapi_sqlite_prefills_project_and_conventions(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args())

        args = make_init_args(
            detect=True,
            purpose="Build a REST API for todos with FastAPI and SQLite",
        )
        cli.apply_updates(str(tmp_path), args)

        project = (tmp_path / "docs" / "PROJECT.md").read_text(encoding="utf-8")
        assert "- **Language(s):** Python" in project
        assert "- **Runtime:** Python 3.12" in project
        assert "- **Framework(s):** FastAPI + Uvicorn" in project
        assert "- **Storage/Infra:** SQLite" in project
        assert "- Run: uvicorn main:app --reload" in project

        conventions = (tmp_path / "docs" / "CONVENTIONS.md").read_text(encoding="utf-8")
        assert "Ruff (`ruff check .` + `ruff format .`)" in conventions
        assert "pytest" in conventions

    def test_detect_from_purpose_prefers_uv_setup(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args())

        args = make_init_args(
            detect=True,
            purpose="FastAPI moderno con uv e uvicorn",
        )
        cli.apply_updates(str(tmp_path), args)

        project = (tmp_path / "docs" / "PROJECT.md").read_text(encoding="utf-8")
        assert "- Setup: uv sync" in project

    def test_detect_from_purpose_prefers_poetry_setup(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args())

        args = make_init_args(
            detect=True,
            purpose="Python service with poetry and FastAPI",
        )
        cli.apply_updates(str(tmp_path), args)

        project = (tmp_path / "docs" / "PROJECT.md").read_text(encoding="utf-8")
        assert "- Setup: poetry install" in project


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
        (tmp_path / "go.mod").write_text("module myapp\n\ngo 1.22\n", encoding="utf-8")
        args = make_init_args(detect=True)
        cli.apply_updates(str(tmp_path), args)

        content = (tmp_path / "docs" / "PROJECT.md").read_text(encoding="utf-8")
        assert "<!-- agentinit:commands:start -->" in content
        assert "<!-- managed by agentinit --detect / --prompt -->" in content
        assert "- Test: go test ./..." in content
        assert "<!-- agentinit:commands:end -->" in content
