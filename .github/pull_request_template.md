<!--
Thanks for the contribution. Fill in the sections below; delete any that don't apply.
For security fixes, see SECURITY.md before opening this PR — public PRs for security
issues should only land AFTER private coordination.
-->

## Summary

<!-- One or two sentences on what this PR changes and why. -->

## Changes

<!-- Bullet list of the specific changes. Link related issues with `Fixes #N` or `Refs #N`. -->

-
-

## Test plan

<!-- How did you verify this works? Mark each box. -->

- [ ] `uv run pytest tests/unit` — all green
- [ ] `uv run ruff check .` — clean
- [ ] `uv run ruff format --check .` — clean
- [ ] `uv run ty check src` — clean
- [ ] Manual testing in iTerm2 (describe below, if applicable)

<!-- For changes that touch the live SDK or notification path, integration testing matters: -->
- [ ] `uv run pytest -m integration` (if your change touches read/write impls)
- [ ] `uv run python scripts/smoke.py` (if your change might affect a release)

## Documentation

- [ ] README updated (if tool surface or rendering notes changed)
- [ ] ARCHITECTURE updated (if module layout, lifecycle, or data flow changed)
- [ ] CHANGELOG `[Unreleased]` entry added (if behavior changed)
- [ ] SECURITY updated (if threat model changed)

## Security review

<!-- Required for changes touching cookie.py, tools/write.py, subprocess calls, env handling, the tool surface, or error envelopes. Skip if not applicable. -->

- [ ] Not applicable
- [ ] This change does not broaden the agent-visible surface area
- [ ] No new subprocess invocations, or new ones use absolute paths, timeouts, minimal `env=`, and `asyncio.to_thread`
- [ ] No new error paths that could leak third-party messages to agents
- [ ] No new validation that echoes user input back without length bounds

## Breaking changes

<!-- If yes, describe what breaks and how callers should adapt. -->

- [ ] No breaking changes
- [ ] Breaking change (described above)

---

By submitting this PR I confirm I have read [CONTRIBUTING.md](../CONTRIBUTING.md) and the contribution follows the repo's conventions.
