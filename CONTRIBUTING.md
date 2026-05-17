# Contributing

Thanks for your interest in `mcp-server-iterm2`. This guide covers local setup, the gates a change has to pass, and how to get a pull request reviewed.

Before contributing code, please review the [Code of Conduct](CODE_OF_CONDUCT.md). For security issues, follow the private flow in [SECURITY.md](SECURITY.md) instead of opening a public issue.

## Prerequisites

- macOS (iTerm2 is macOS-only)
- iTerm2 installed
- Python 3.12 or 3.13
- [`uv`](https://docs.astral.sh/uv/) for dependency management

## Development setup

```bash
git clone https://github.com/r6e/mcp-server-iterm2.git
cd mcp-server-iterm2
uv sync
```

Optional but recommended — install the pre-commit hook (runs ruff, ty, and unit tests on every commit):

```bash
uv run pre-commit install
```

## Quality gates

A change is ready when all four pass locally:

```bash
uv run pytest tests/unit       # unit tests, mocked SDK
uv run ruff check .            # lint
uv run ruff format --check .   # format check
uv run ty check src            # type check
```

CI runs these on macOS for Python 3.12 and 3.13.

### Integration tests (opt-in)

Integration tests exercise the live iTerm2 SDK. They mutate the badge, title, and tab color of the session they run in. CI does not run them.

```bash
uv run pytest -m integration   # from inside an iTerm2 session
```

### Manual smoke test

Before tagging a release:

```bash
uv run python scripts/smoke.py   # from inside an iTerm2 session
```

This calls every tool once and prints a pass/fail summary.

## How we work

### Test-driven

Write the failing test first, watch it fail, then implement the change. The existing test suite uses `pytest` with `asyncio_mode = "auto"` — async tests don't need `@pytest.mark.asyncio` decorators. Mocks come from `unittest.mock`. Fixtures for `App`/`Window`/`Tab`/`Session` mocks live in `tests/fixtures.py`; an autouse `iterm2.Transaction` stub lives in `tests/unit/conftest.py`.

When you touch a function, add a test for whatever you're changing. Coverage target is 80%+.

### Small, focused PRs

Each pull request should make one logical change. Bundle a test, an implementation, and a doc update for the same behavior — but don't pile unrelated cleanups into the same PR.

### Conventional commits

Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat: add X` — new feature or new tool
- `fix: handle Y` — bug fix
- `chore: bump dep Z` — non-functional change (deps, config, formatting)
- `docs: update README` — documentation only
- `test: cover edge case W` — test-only change
- `refactor: extract helper` — internal restructuring with no behavior change
- `fix(security): …` — security fix (used for severity-tier visibility in CHANGELOG)

Keep the subject under 72 characters and use the imperative mood ("add X", not "added X").

### Documentation lives next to behavior

If your change alters behavior, update the relevant docs in the same PR:

- New or changed tool → update the table in [README.md](README.md) and the relevant section.
- Architectural change → update [ARCHITECTURE.md](ARCHITECTURE.md).
- Security-relevant change → update [SECURITY.md](SECURITY.md).
- User-visible change → add a line to the `[Unreleased]` section in [CHANGELOG.md](CHANGELOG.md).

## Pull request process

1. Branch from `main`. Name branches descriptively (e.g., `fix-transaction-wrap`, `feat-buried-sessions`).
2. Push your branch and open a PR. The [PR template](.github/pull_request_template.md) prompts for a summary, test plan, and a security checklist.
3. CI must be green before review. If it's not, fix the failure rather than asking a reviewer to look past it.
4. Reviewers may push back on scope, naming, or style. Discuss in the PR thread; reach agreement before forcing through.
5. Squash-merge when approved. The PR title becomes the commit; make sure it follows the conventional-commits format above.

## Scope of changes that need extra care

These touch the security posture and warrant explicit reviewer attention:

- Anything in `cookie.py` or `tools/write.py` that runs `subprocess`.
- Any change to the tool surface — adding a new tool, broadening an existing tool's capability, or changing an error envelope.
- Anything that touches `os.environ` or the `_osascript_env()` helpers.
- Any new dependency. We minimize the dependency tree on purpose.

For these changes, call out the security implications in the PR description and confirm `SECURITY.md` is still accurate.

## Style notes

- Follow the existing patterns. The codebase uses `from __future__ import annotations`, `typing.Any` for SDK boundaries, keyword-only arguments for clarity on multi-string functions, and module-private constants in `_SCREAMING_SNAKE_CASE`.
- Error messages are user-facing. They live in `errors.py:to_error_text` or are passed directly to `InvalidArgument`. Keep them actionable.
- Ruff enforces formatting and lint. Don't fight it; configure it via `pyproject.toml` if a rule is genuinely wrong for our case.

## Questions

Open a [discussion](https://github.com/r6e/mcp-server-iterm2/discussions) for design questions, or a regular issue for bugs and feature requests. For security: see [SECURITY.md](SECURITY.md).
