# Shared contract reconciliation: Claude native adapter (2026-11-09)

Five shared capabilities compared across the shared contract, the Codex adapter
and the Claude adapter, with the gap closed in Claude adapter source only.
Baselines: shared `shikigarasu-common` at dotcodex `675e8c8` (`SKILL.md`
`8681fae2…`, `references/execution-selection.md` `e2a96235…`, contract ID
`shikigarasu-execution-selection` v1); Codex adapter and Claude adapter at this
repository `e31c4dd`. Nothing from the Codex adapter's runtime (`spawn_agent`,
`fork_turns`, `test_runner.py`, its SKILL trigger text) was copied; the one
script reused, `closure_gate.py`, is a runtime-neutral read-only checker that
ships in the same plugin checkout.

| Capability | Shared contract | Codex adapter (native) | Claude adapter before | Gap closed in this change |
|---|---|---|---|---|
| 自主選路 execution selection | Path table Direct/Skill/Playbook/Delegated/Parallel/Iterative/Dynamic/Durable; adapt from evidence; infra vs acceptance failure; compact consequential record; cost `unknown` unless reported | Outcome-based mode routing (Explore/Experiment/Compare/Implement/Review); mode and delegation separate; native-only | Outcome-shaped axis routing in `rules/common/shikigarasu-dispatch.md`; capacity-aware waves in kishi; no mention of the shared path table, Durable, or infra-vs-acceptance retry | Dispatch rule gains "Execution selection and adaptation": each shared path mapped to a Claude form (`Agent`, slash command, background Bash), Durable declared not native, one retry for infrastructure failure, narrower ticket for acceptance failure, compact record, cost `unknown` |
| 驗證 verification | Acceptance evidence; producer tests are evidence only; source/tests/publication/deployment/loading/behavior/outcome kept separate; read target and receipt before repeating side effects | `test_runner.py` durable run handle; `closure_gate.py` RED/GREEN receipts, artifact hashes, integration evidence | genen "run test, show output"; kishi "verify from artifacts, diffs, test output"; no evidence record shape, no red/green rule, no long-run handling | kishi "Verification evidence" (command, exit code, failures, observed; red-before/green-after; background Bash handle is not a pass; seven layers separate); genen records the same |
| 獨立審查 independent review | Fresh-context reviewer ≠ producer/author/coordinator; frozen native policy or legacy two-pass; high-risk and gate change two passes; collective two fix rounds | Frozen tier 0/1/2 with external baseline digest, checked by `closure_gate.py`; `fork_turns="none"` for reviewers | Two passes always (legacy), hakuso fresh context, veto rules, ceiling; no definition of fresh context on Claude, no statement of which policy Claude runs, no reuse path for a frozen manifest | kishi: fresh-context = separately dispatched `Agent`, `fork` and main session excluded, reviewer identity recorded; Claude policy = shared legacy fallback; frozen manifests validated with the existing `closure_gate.py`, no second checker. hakuso states its own eligibility on all three surfaces (agent, command, skill); a manifest tier never lowers Claude below two passes |
| 狀態接續 state continuation | Durable needs real persistent state and resume; prompt loop is not crash recovery; unknown result is not success or permission to replay | `test_runner.py` metadata/result files; `uncertain` state | Task list in session; `/goal` or explicit request for cross-turn; report paths in OS temp; nothing on resume or lost responses | kishi "State and continuation": Task state dies with the session, survivors go to report path or handoff, read target and receipt before repeating side effects, Monitor/wake-up is not queue persistence |
| 改善循環 improvement loop | Capture reusable failure through the existing Hirameki/auto-improve writer within authority; preserve event/candidate/proposal identities; no permanent change from a temporary workflow; dream exchange via existing proposal/experiment links | dotcodex auto-improve capture-handoff and proposal contract (shared skill, not adapter) | "Do not offer memory writeback"; no link from BLOCKED/ceiling/slip to a capture candidate | kishi "Improvement loop": BLOCKED, surviving findings, recurring slips and availability disclosures become capture candidates reported in the final output (item 7); no rule/memory writes by workers; Akegarasu identities for dream exchange; no permanent adapter change from a lesson |

## What was reused, not rebuilt

- Queue, review and evidence contract: `shikigarasu-common` (unchanged).
- Path semantics: shared `execution-selection.md` (referenced by contract ID, not copied).
- Spec-driven closure checker: `codex/skills/shikigarasu/scripts/closure_gate.py`.
- Capture and promotion: Hirameki/auto-improve writer and the human gate; dream
  exchange: Akegarasu existing records (see its `docs/harness-exchange.md`).
- Long-running tests: Claude Code's own background Bash and task notification.

## Not done here

No orchestrator, dispatcher, tier registry, second checker or durable runtime was
added. No Codex runtime setting was copied. Installed state, host loading of the
dispatch rule and model behaviour under the new text are not exercised by this
change; `tests/test_axis_routing_contract.py` pins the source anchors only.
