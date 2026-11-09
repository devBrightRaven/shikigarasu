# Validation Contract

Shikigarasu is a released Tier 1 asset. A change is releasable only when its
behavior contract, local test battery, and repository CI agree.

## Contract

- The Claude and Codex adapters keep separate authority and runtime surfaces.
- The Codex plugin is self-contained, portable, and implicitly invokable only
  for the positive trigger cases documented in its skill.
- Queue state, tiered independent review, convergence ceilings, authority
  boundaries, and evidence reporting remain explicit and testable.
- Codex closure review policy is frozen before work: tier 0/1/2 requires
  0/1/2 reviewers, while legacy manifests without a tier remain on the old
  dual-review requirement. Explicit policies must match a separately supplied
  trusted baseline; invalid shapes or mismatches fail closed. High-risk and
  closure-gate changes remain tier 2.
- Machine-coupled runtime checks may be skipped in CI, but must pass locally
  before a release or plugin update.
- The Claude adapter states in its own source how the shared execution-selection
  paths, verification evidence, fresh-context review, state continuation and
  improvement capture map onto Claude-native tools (`Agent`, slash commands,
  background Bash, Task list). It reuses the shared contract, the existing
  `closure_gate.py` checker and the existing capture writer; it adds no second
  orchestrator, checker or tier registry and copies no Codex runtime setting.

## Mapped tests

- `tests/check-shikigarasu-contract.ps1`: Claude adapter and shared-contract
  behavior; `-RepoOnly` excludes machine runtime checks in CI.
- `tests/check-codex-authority.ps1`: Codex ownership, installation surface,
  trigger boundary, and self-contained contract.
- `tests/test_axis_routing_contract.py`: Claude axis boundaries, dispatch-rule
  guards and the shared-capability mapping anchors above; plus the native-host
  acceptance fixture's coverage checks (static only, not host behaviour).
- `tests/test_agy_routing.py`: bounded external-review routing.
- `tests/test_probe_shikigarasu_contract.py`: source-bound fresh-process probe
  validation.
- `codex/skills/shikigarasu/scripts/probe_shikigarasu_contract.py`: optional
  live Codex discovery probe; run when the installed plugin or discovery
  mechanism changes.

## Gates

- `tests/test_closure_gate.py`: reusable spec, behavioral TDD, artifact and independent-review closure checks; negative evidence must block without mutating a queue.
- `tests/test_test_runner.py`: durable test launch/status, output capture, failures, timeout and run-directory collision handling. Terminal results are published after final lifecycle metadata; metadata alone is not completion. A run handle is not success; inspect its terminal result.
- Spec-driven integration must map the approved requirements to tickets and raw evidence. The checker cannot establish receipt authenticity, actual model identity, crash recovery, or OS containment.

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
