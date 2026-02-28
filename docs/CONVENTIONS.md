# Conventions

## Style

- Formatting standard: PEP 8, no external formatter enforced.
- Documentation tone/language: English.
- Commenting: only where logic is non-obvious; no docstrings on trivial helpers.

## Naming

- Files/directories: lowercase, underscores (e.g. `cli.py`, `test_cli.py`).
- Variables/functions: snake_case. Private helpers prefixed with `_`.
- Constants: UPPER_SNAKE_CASE (e.g. `MANAGED_FILES`, `TEMPLATE_DIR`).
- Branch naming: `feature/<slug>`, `fix/<slug>`.

## Testing

- Framework: pytest >=8.
- Tests live in `tests/` at repo root.
- Use `tmp_path` + `monkeypatch.chdir` for filesystem tests; no mocking of shutil/os.
- Catch `sys.exit` with `pytest.raises(SystemExit)`.

## Git Workflow

- Commit message format: conventional-ish (`fix:`, `feat:`, `docs:`, `ci:`).
- PR requirements: CI green (tests + markdownlint + lychee).
- Merge strategy: squash-merge to main; tag releases as `vX.Y.Z`.
