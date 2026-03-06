"""Tests for agentinit.cli."""

import json
import sys

import pytest

import agentinit.cli as cli
from tests.helpers import (
    make_add_args,
    make_init_args,
    make_lint_args,
    make_status_args,
)


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

    def test_lint_invalid_config_does_not_crash(self, tmp_path, monkeypatch):
        """Invalid numeric values in config should fall back to defaults."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
        (tmp_path / ".contextlintrc.json").write_text(
            '{"line_budget": {"default_warn": "abc", "per_file": {"AGENTS.md": "oops"}}}',
            encoding="utf-8",
        )

        with pytest.raises(SystemExit) as exc:
            cli.cmd_lint(make_lint_args())
        assert exc.value.code == 0

    def test_lint_invalid_list_config_types_do_not_ignore_everything(
        self, tmp_path, monkeypatch
    ):
        """String-valued list settings should be ignored, not expanded character-by-character."""
        from agentinit._contextlint.checks import discover_context_files, load_config

        monkeypatch.chdir(tmp_path)
        (tmp_path / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
        (tmp_path / "CLAUDE.md").write_text("See AGENTS.md\n", encoding="utf-8")
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "GUIDE.md").write_text("# Guide\n", encoding="utf-8")
        (tmp_path / ".contextlintrc.json").write_text(
            json.dumps({"ignore": {"paths": "docs/*.md"}}),
            encoding="utf-8",
        )

        config = load_config(tmp_path)
        discovered = discover_context_files(tmp_path, config)

        assert sorted(config.ignore_paths) == []
        assert sorted(str(path.relative_to(tmp_path)) for path in discovered) == [
            "AGENTS.md",
            "CLAUDE.md",
            "docs/GUIDE.md",
        ]

    def test_lint_resolves_relative_links_from_current_file(
        self, tmp_path, monkeypatch
    ):
        """A docs file can link to ../README.md without being flagged as escaping root."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
        (tmp_path / "CLAUDE.md").write_text("See AGENTS.md\n", encoding="utf-8")
        (tmp_path / "README.md").write_text("# Readme\n", encoding="utf-8")
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "GUIDE.md").write_text(
            "See [README](../README.md)\n", encoding="utf-8"
        )

        with pytest.raises(SystemExit) as exc:
            cli.cmd_lint(make_lint_args())
        assert exc.value.code == 0


class TestRouterSanityFiltering:
    def test_router_sanity_respects_selected_paths(self, tmp_path, monkeypatch):
        """Router sanity should only check files within selected_paths."""
        from agentinit._contextlint.checks import run_checks

        monkeypatch.chdir(tmp_path)
        # Create AGENTS.md, CLAUDE.md (valid), and GEMINI.md (invalid — no pointer)
        (tmp_path / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
        (tmp_path / "CLAUDE.md").write_text(
            "See AGENTS.md and docs/\n", encoding="utf-8"
        )
        (tmp_path / "GEMINI.md").write_text(
            "This router has no pointer at all.\n", encoding="utf-8"
        )

        # Without selected_paths: GEMINI.md should be flagged
        result_all = run_checks(root=tmp_path)
        gemini_diags = [d for d in result_all.diagnostics if d.path == "GEMINI.md"]
        assert any("no pointer" in d.message for d in gemini_diags)

        # With selected_paths excluding GEMINI.md: no GEMINI.md diagnostics
        result_filtered = run_checks(
            root=tmp_path, selected_paths={"AGENTS.md", "CLAUDE.md"}
        )
        gemini_diags_filtered = [
            d for d in result_filtered.diagnostics if d.path == "GEMINI.md"
        ]
        assert gemini_diags_filtered == []

    def test_minimal_status_ignores_gemini_router_warnings(
        self, tmp_path, monkeypatch, capsys
    ):
        """Minimal status should not show router warnings for GEMINI.md."""
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args(minimal=True))

        # Create a leftover GEMINI.md with no pointer (would trigger router warning)
        (tmp_path / "GEMINI.md").write_text(
            "This file has no pointer to AGENTS.md or docs/.\n", encoding="utf-8"
        )

        # Fill TBD markers
        for rel in cli.MINIMAL_MANAGED_FILES:
            path = tmp_path / rel
            if path.is_file():
                content = path.read_text(encoding="utf-8")
                path.write_text(content.replace("TBD", "done"), encoding="utf-8")

        with pytest.raises(SystemExit) as exc:
            cli.cmd_status(make_status_args(minimal=True, check=True))
        assert exc.value.code == 0
        out = capsys.readouterr().out
        assert "GEMINI.md" not in out


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

    def test_add_mcp_updates_only_first_matching_heading(self, tmp_path, monkeypatch):
        """A repeated heading inside code blocks must not be modified."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".agents").mkdir()
        (tmp_path / "AGENTS.md").write_text(
            "## Tools & Integrations\n\nintro\n\n```md\n## Tools & Integrations\n```\n",
            encoding="utf-8",
        )

        cli.cmd_add(make_add_args(type="mcp", name="github"))

        content = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        assert content.count("- `.agents/mcp-github.md`") == 1

    def test_add_mcp_ignores_heading_mentions_inside_fenced_blocks_first(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".agents").mkdir()
        (tmp_path / "AGENTS.md").write_text(
            "```md\n## Tools & Integrations\n```\n\n"
            "Intro\n\n"
            "## Tools & Integrations\n\n"
            "Actual content\n",
            encoding="utf-8",
        )

        cli.cmd_add(make_add_args(type="mcp", name="github"))

        content = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        assert "```md\n## Tools & Integrations\n```" in content
        assert (
            "## Tools & Integrations\n\n- `.agents/mcp-github.md`\n\nActual content"
            in content
        )

    def test_add_skill_rejects_path_traversal_name(self, tmp_path, monkeypatch):
        """Traversal-like skill names must be rejected before touching the project."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".claude" / "skills").mkdir(parents=True)
        (tmp_path / ".claude" / "keep.txt").write_text("keep", encoding="utf-8")

        args = make_add_args(type="skill", name="..", force=True)
        with pytest.raises(SystemExit) as exc:
            cli.cmd_add(args)
        assert exc.value.code == 1
        assert (tmp_path / ".claude" / "keep.txt").exists()

    def test_add_mcp_rejects_path_traversal_name(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        args = make_add_args(type="mcp", name="../mcp/github")
        with pytest.raises(SystemExit) as exc:
            cli.cmd_add(args)
        assert exc.value.code == 1
        assert not (tmp_path / ".agents").exists()

    def test_add_skill_force_overwrites_existing_file(self, tmp_path, monkeypatch):
        """--force should replace a colliding file path with the skill directory."""
        monkeypatch.chdir(tmp_path)
        target = tmp_path / ".agents" / "skills" / "code-reviewer"
        target.parent.mkdir(parents=True)
        target.write_text("placeholder", encoding="utf-8")

        args = make_add_args(type="skill", name="code-reviewer", force=True)
        cli.cmd_add(args)

        assert target.is_dir()
        assert (target / "SKILL.md").is_file()

    def test_add_mcp_force_overwrites_existing_directory(self, tmp_path, monkeypatch):
        """--force should replace a colliding directory path with the MCP file."""
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args())

        target = tmp_path / ".agents" / "mcp-github.md"
        target.mkdir(parents=True)
        (target / "placeholder.txt").write_text("old", encoding="utf-8")

        args = make_add_args(type="mcp", name="github", force=True)
        cli.cmd_add(args)

        assert target.is_file()
        assert not (tmp_path / ".agents" / "mcp-github.md" / "github.md").exists()

    def test_add_security_force_overwrites_existing_directory(
        self, tmp_path, monkeypatch
    ):
        """--force should replace a colliding directory path with the security file."""
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args())

        target = tmp_path / ".agents" / "security.md"
        target.mkdir(parents=True)
        (target / "placeholder.txt").write_text("old", encoding="utf-8")

        args = make_add_args(type="security", name=None, force=True)
        cli.cmd_add(args)

        assert target.is_file()
        assert not (tmp_path / ".agents" / "security.md" / "security.md").exists()

    def test_add_soul_requires_name(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args())

        args = make_add_args(type="soul", name=None)
        with pytest.raises(SystemExit) as exc:
            cli.cmd_add(args)
        assert exc.value.code == 1
        assert "requires a persona name" in capsys.readouterr().err

    def test_add_soul_replaces_name_placeholder(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cli.cmd_init(make_init_args())

        args = make_add_args(type="soul", name="CodePilot")
        cli.cmd_add(args)

        content = (tmp_path / ".agents" / "soul.md").read_text(encoding="utf-8")
        assert "{{NAME}}" not in content
        assert "CodePilot" in content


class TestPrintNextSteps:
    def test_print_next_steps_with_tty_all_files(self, monkeypatch, capsys, tmp_path):

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

    def test_print_next_steps_with_tty_partial_files(
        self, monkeypatch, capsys, tmp_path
    ):

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

        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys.stdout, "isatty", lambda: False)
        from agentinit import cli

        (tmp_path / "AGENTS.md").touch()

        cli._print_next_steps(str(tmp_path))
        out, _ = capsys.readouterr()
        assert "Some agents only read tracked files." not in out
        assert "git add" not in out

    def test_print_next_steps_no_files(self, monkeypatch, capsys, tmp_path):

        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
        from agentinit import cli

        # Create no files
        cli._print_next_steps(str(tmp_path))
        out, _ = capsys.readouterr()
        assert "Some agents only read tracked files." not in out
        assert "git add" not in out
