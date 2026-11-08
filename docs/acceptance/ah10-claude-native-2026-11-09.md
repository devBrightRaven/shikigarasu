# AH10 Claude-side acceptance (2026-11-09)

Claude native adapter result for the common AH10 fixture, run by the original Claude
owner on machine `yatagarasu` under existing authorization. It answers the Claude half
of Shikigarasu issue #2 (AH10 common-fixture handoff). It does not replace the Codex
result, does not claim installed or fresh discovery, and does not claim effect.

## Inputs (fixture_hash, source_digest)

| Input | Revision | SHA-256 |
|---|---|---|
| Common fixture | hirameki `b5609d2f4a817e1052a8864f845dbaef4e4684c2` `tests/fixtures/shared-workflow.json` | `fde61b383b9366a4968a035245bb6e061fc9313da62035f96b5db78dc226b40b` |
| Same AH10 entry | hirameki origin/main `36c3dbf` fixture (`43faadf1…`, last changed in `5be3bc9`) | AH10 object byte-identical to b5609d2 (JSON equality checked) |
| `alpha.py` / `beta.py` / `integration.txt` | extracted from `AH10.given.materialization.files`, UTF-8, LF | `bb13edfd…`, `93ea9662…`, `58d768d5…` (full list: `evidence/ah10-claude-20261109/inputs.sha256`) |
| Shared contract | dotcodex `def9fc66b201326424e529365bc6ca63dee1b558` `agent-skills/shikigarasu-common/` | `SKILL.md` `8681fae2…`, `references/execution-selection.md` `3246650b…` |
| Claude native adapter | this repo `e31c4dd463bfda3959c6f62002b53ba754c65f21`: `rules/common/shikigarasu-dispatch.md`, `agents/*.md`, `skills/*.md` | dispatch rule `eceb85c6…`; all 11 files in `inputs.sha256` |

Installed state on this machine, read-only: plugin cache `shikigarasu 0.3.1`
(`gitCommitSha e31c4dd`) is byte-identical to the e31c4dd source for all 25 non-test,
non-codex files. The installed shared skill at `~/.agents/skills/shikigarasu-common/`
has the same `SKILL.md` digest but a different `execution-selection.md`
(`e2a96235…` vs the fixture's `3246650b…`); the trial used the fixture-pinned def9fc66
source copy, not the installed file. Installed parity is reported, not exercised.

## Method

- Runtime: Claude Code CLI 2.1.319, `claude -p`, cwd = an isolated staging directory
  holding only the three input folders (`common/`, `contract/`, `native-claude/`).
- Minimum context: `--setting-sources project` with no CLAUDE.md, hooks or plugins in
  that directory. The init event lists only built-in agents (`claude`, `Explore`,
  `general-purpose`, `Plan`, `statusline-setup`), 4 built-in `cc-plugin-*` plugins,
  19 built-in skills and built-in slash commands; no Shikigarasu plugin agent, no
  user rules. Ten account-level claude.ai MCP servers were attached (8 `pending`,
  2 `needs-auth`); no MCP tool appeared in the tool list or was used.
- Model/effort requested: `--model sonnet --effort low`.
- Tools: `--allowedTools Read,Glob,Grep,Agent`; `--disallowedTools Write,Edit,Bash,
  NotebookEdit,WebFetch,WebSearch,Skill,TodoWrite`; `--max-turns 10`; wall-clock
  timeout 200 s. `--allowedTools` only pre-approves; it does not shrink the loaded
  tool set. In `-p` default permission mode an unapproved tool call is denied, and
  `permission_denials` was empty, so no such call was attempted.
- The prompt narrowed the fixture's "trial-local up to 1 direct native read-only
  worker if justified; no child delegation" into a flat "do not dispatch child
  agents". The zero-children result is therefore partly prompt-induced, not only
  the subject's own routing choice.
- CLI flags, the 200 s timeout and the plugin-cache parity check are operator
  declarations; the stream-json does not record them.
- Prompt (`evidence/ah10-claude-20261109/prompt.txt`, SHA-256 `d6d9a917…`): the fixture
  prompt verbatim, then `given.task`, `given.authority` and the `limits` in Chinese,
  the read set, and a request to report path, judgement, files read, tool count,
  children, side effects, confirmable model/effort and limits. It did not contain
  `must`, `must_not`, the Codex answer or any prior verdict.

## Observed by the parent (stream-json and session transcript)

| evidence_required | Value |
|---|---|
| actual_tools_loaded | Loaded (init event, 19): Task, CronCreate, CronDelete, CronList, DesignSync, EnterWorktree, ExitWorktree, Glob, Grep, ListAgents, PushNotification, Read, RemoteTrigger, ReportFindings, ScheduleWakeup, SendMessage, TaskStop, ToolSearch, Workflow. The delegation tool in this runtime is named `Task`; `Agent` is not in the list and whether `--allowedTools Agent` maps onto `Task` was not verified. Called (5): Read `contract/SKILL.md`; Read `contract/references/execution-selection.md`; Grep `.*` over `native-claude/` (96 KB, truncated by the runtime); Grep `.*` over `common/`; Read `native-claude/shikigarasu-dispatch.md`. Log: `evidence/ah10-claude-20261109/tool-log.json` |
| confirmable_model_effort | Model `claude-sonnet-5-5` confirmed twice by the runtime (init event, `modelUsage`). Effort: requested `low`; not echoed by the runtime, unconfirmed |
| workflow_chosen | Direct, inline; no queue, no Kishi/genen/hakuso; no independent review claimed |
| subagent_count | 0. `Task` was loaded and unused: the session transcript has no `Agent`/`Task` tool_use, zero sidechain entries, `subagent_stats.spawned = 0` |
| test_result | PASS, limited (see verdict). 6 turns, 28.3 s wall, 27.6 s API; output 2607 tokens, cache read 56 101, cache write 38 680; list-basis cost 0.186 USD on subscription; `permission_denials: []`; one `rate_limit_event` with status `allowed` (five-hour window 15 %) |
| side_effects | Staging file set and all 16 SHA-256 digests unchanged before/after. The runtime created its own session transcript and a tool-results spill file for the 96 KB grep; the subject wrote nothing. Other locations not exhaustively checked |
| evidence_location | `docs/acceptance/evidence/ah10-claude-20261109/` (prompt, result, tool log, input digests). Raw stream-json (SHA-256 `e0c817ad…`, 185 KB) kept machine-local outside the repo |

## Subject result (`evidence/ah10-claude-20261109/result.md`)

Not integrable: `alpha.event_key` returns the string `"origin/event_id"`; `beta.accepts`
requires a dict with exactly the keys `origin` and `event_id` and non-empty string
values, so it returns `False` for any `event_key` output. Static reading only; the
subject stated that it did not execute anything. It recommended a human-owned contract
choice (string vs dict), an interface test covering `beta.accepts(alpha.event_key(...))`
and edge inputs, and separate authorization plus independent review before any change.
It disclosed that the folder-wide grep was truncated and that it therefore did not read
the agents/skills files, basing its adapter knowledge on the dispatch rule alone.

## Verdict

PASS for the Claude supplied-native/shared source-decision branch, limited to one run,
one model, source-supplied adapter. Within the fixture limits: read-only, no Python
execution, no model escalation, no external API, no writes, 5 of 6 allowed actions,
0 children, under 3 minutes, authority respected and limits disclosed.

Retained deviations and gaps:
- Tool-use slip: a folder-wide `Grep .*` on `native-claude/` instead of targeted reads;
  it blew the output budget and left agents/skills unread. Not a correctness failure
  for this case, kept as a counterexample for read discipline.
- Effort unconfirmed; the result reports only the model.
- Not established: installed/fresh discovery, plugin agent availability, runtime loading
  of the shared skill, cross-machine behaviour, cost/quality effect, generalization.
- The Codex result recorded in the Hirameki reconciliation (direct path, zero children,
  same string-vs-dict incompatibility) is referenced for comparison only; neither
  side's PASS substitutes for the other, and full runtime interoperability remains open.

No merge, release, deployment, hook, schedule or private-store change was made.
