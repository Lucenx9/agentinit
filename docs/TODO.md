# TODO Template

## In Progress

- (none)

## Next

- Add `agentinit status` command (show present/missing/TBD files, `--check` for CI).
- Add `--json` output mode for scripting and CI.
- Add `agentinit build` command (validate pointers, enforce line limits, sanity-check structure).

## Blocked

- (none)

## Done

- Added ANSI colored output (respects NO_COLOR, TERM=dumb, non-TTY).
- Made interactive wizard default on TTY (npm-init pattern); `--yes` skips it.
- Added `--yes`/`-y` flag to `init` and `minimal` subcommands.
- Added "next steps" guidance after successful init/new.
- Aligned template files to on-demand loading best practices (token efficiency).
- Scaffolded agent router and docs templates.
- Added `--minimal` mode to `agentinit init` and `agentinit new`.
- Added `agentinit minimal` convenience alias.
- Filled `docs/PROJECT.md` and `docs/CONVENTIONS.md` with real project details.
- Released v0.2.3.
- Fixed EOFError/KeyboardInterrupt handling in wizard (clean exit 130).
- Fixed `--yes` flag ignored in direct `cmd_new`/`cmd_init` calls.
- Fixed `--force` failing on read-only files (PermissionError).
- Fixed archive timestamp collision (added microseconds).
- Fixed stderr consistency for all warnings.
- Added edge case tests (unicode, spaces, read-only, archive collision).
- Released v0.2.4.
