# Contributing

## Development setup

```sh
git clone https://github.com/Lucenx9/agentinit.git
cd agentinit
python3 -m venv .venv
. .venv/bin/activate
pip install -e . --group dev
```

On distro-managed Python installs (PEP 668), the virtual environment is required.

## Running tests

```sh
# Full test suite
python3 -m pytest tests/ -v

# With coverage
python3 -m pytest tests/ -v --cov=agentinit --cov-report=term-missing

# Single test file
python3 -m pytest tests/test_cli_project_commands.py -v
```

The test suite (170+ tests) covers all CLI commands, template operations, profile detection, security checks, and edge cases.

## Linting and formatting

```sh
python3 -m ruff check agentinit tests cli
python3 -m ruff format --check agentinit tests cli
```

Both checks must pass before committing. CI runs these on every push.

## Project structure

```text
agentinit/
├── cli.py              # CLI entrypoint, color helpers, stable wrappers
├── _parser.py          # Argument parser builder
├── _scaffold.py        # Core scaffold and file operations
├── _status.py          # Status command implementation
├── _sync.py            # Router file sync logic
├── _add.py             # Resource installation (add command)
├── _doctor.py          # Diagnostic checks and fix suggestions
├── _llms.py            # llms.txt rendering
├── _project_detect.py  # Stack detection and language translation
├── _project_updates.py # Project doc updates and wizard logic
├── _profiles.py        # Profile detection (minimal vs full)
├── _contextlint/       # Vendored contextlint implementation
└── template/           # Template files copied to user projects
```

The CLI is a thin dispatch layer (`cli.py` + `_parser.py`). Each command's logic lives in a focused internal module.

## Adding a template file

1. Add the file to `agentinit/template/`
2. If it's a managed file, add its relative path to `MANAGED_FILES` in `cli.py`
3. If it should be removable, add it to `REMOVABLE_FILES`
4. If it has a minimal-profile variant, add an override in `template/minimal/`
5. Add test coverage
6. Run the full test suite

## Adding a modular resource

1. Add the resource file to `agentinit/template/add/<type>/`
2. If it's a new resource type, register it in `_add.py` (`ADD_RESOURCE_TYPES`)
3. Add test coverage
4. Run the full test suite

## CI pipeline

CI runs on every push and PR to `main`:

- **Lint** -- ruff check + format (Python 3.13)
- **Dependency audit** -- pip-audit
- **Unit tests** -- pytest with coverage (Python 3.10-3.13)
- **Package check** -- Build and validate wheel/sdist
- **Smoke tests** -- Install from wheel and run commands (Linux, macOS, Windows x Python 3.10-3.13)

## Submitting changes

1. Fork the repository
2. Create a branch for your change
3. Run `python3 -m pytest tests/ -v` and `python3 -m ruff check agentinit tests cli`
4. Open a pull request against `main`

Keep changes minimal and focused. Run tests before committing.
