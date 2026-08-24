# Validation Contract

Shikigarasu is a released Tier 1 asset. A change is releasable only when its
behavior contract, local test battery, and repository CI agree.

## Contract

- The Claude and Codex adapters keep separate authority and runtime surfaces.
- The Codex plugin is self-contained, portable, and implicitly invokable only
  for the positive trigger cases documented in its skill.
- Queue state, independent two-pass review, convergence ceilings, authority
  boundaries, and evidence reporting remain explicit and testable.
- Machine-coupled runtime checks may be skipped in CI, but must pass locally
  before a release or plugin update.

## Mapped tests

- `tests/check-shikigarasu-contract.ps1`: Claude adapter and shared-contract
  behavior; `-RepoOnly` excludes machine runtime checks in CI.
- `tests/check-codex-authority.ps1`: Codex ownership, installation surface,
  trigger boundary, and self-contained contract.
- `tests/test_agy_routing.py`: bounded external-review routing.
- `tests/test_probe_shikigarasu_contract.py`: source-bound fresh-process probe
  validation.
- `codex/skills/shikigarasu/scripts/probe_shikigarasu_contract.py`: optional
  live Codex discovery probe; run when the installed plugin or discovery
  mechanism changes.

## Gates

- Local: `npm test -- --run` must pass before commit. The extra `--run` is
  accepted for compatibility with the Claude Code pre-commit hook. Codex must
  run the same command explicitly because that host does not execute Claude's
  hook.
- CI: `.github/workflows/validate.yml` runs the repository-only battery on
  every push and pull request.
- Release: both local and CI gates must pass; a process start is not a pass.

## Update rule

Any change to a contract item must update its mapped test in the same change.
If a command, path, runtime dependency, or gate changes, update this document,
`package.json`, and CI together.
