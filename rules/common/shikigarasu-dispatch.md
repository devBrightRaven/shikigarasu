# Shikigarasu Axis Dispatch

**Guard**: active only if kishi is installed (`~/.claude/agents/kishi.md`
exists or kishi appears in the session's agent list). Otherwise treat this
whole file as inactive.

Matching tasks route directly with no suggestion round-trip. Kishi completes
the authorized local, reversible batch and interrupts only for irreversible external action,
new authority, material scope expansion, or an
outcome-changing fork. `[plan only]` remains an explicit preview mode.

Authority precedence remains: current user instructions, applicable repository
instructions, current verified files/state, then memory. This dispatch rule
only selects an axis; it does not override that ordering or grant new authority.
Kishi owns convergence for the current turn only. Cross-turn continuation
happens only when a `/goal` is confirmed active in the session or the user
explicitly requests persistent continuation; never infer an equivalent
mechanism or create persistence on Kishi's own initiative. Without that
confirmation, finish the turn and stop.

## Routing

| Intent in user prompt | Route (dispatch directly) |
|---|---|
| Bounded decision with options (scope, positioning, roadmap, priorities) | seiran 策略 |
| Implement / refactor / fix / "make it work" | genen 執行 |
| Code review, audit, PR gate, security check | hakuso 審判 |
| Research, blind-spot scan, debugging recon, "why is this weird" | shuen 探路 |
| Hypothesis-driven experiment, benchmark, "what happens if" | soen 蒼炎 (Agent tool; no slash command by design) |
| Needs ≥2 axes (review→fix→verify, research→build, ...) | kishi orchestrates |

Single known axis → that worker directly through the Agent tool, or a slash command when available;
do not wrap one-axis jobs in kishi.

kishi invocation by weight:

- **Light/medium, interactive**: the current main session applies the Kishi coordinator protocol directly using its Agent tool. Do not invoke Kishi as a nested agent.
- **Heavy/detached**: start exactly one `claude --agent kishi -p "<task>"` parent coordinator. Append ` [plan only]` to preview routing without dispatching. Never start one CLI process per ticket; the parent uses native Agent coordination.

For multi-axis tasks, pass the full requested outcome to Kishi once. Do not
return to the user between scout, strategy, execution, and audit phases unless
the interruption policy above applies.

## Still skipped (relevance filter, not a confirmation gate)

- Casual chat, factual lookup, one-liner, or clearly outside all axes
- User said "直接做" / "skip shikigarasu" — handle inline/generic instead
- `brightraven-resolve:resolve` already triggered — defer to resolve
- Use capacity-aware waves bounded by currently available subagent slots.
  Refill freed slots immediately; do not launch hundreds of workers at once or
  stack several Kishi flows concurrently. There is no fixed cap on total
  tickets: notify unusually large queues and their expected batching without blocking authorized work.
  In short, do not stack Kishi flows.

`?ki` anywhere in the message now forces axis routing even inside the skip
zone: state the chosen axis + the matching fragment in one line, then
dispatch — no confirmation wait.

Async / monitoring / scheduled requests are not an axis job. Route to the
user's OpenClaw daemon or schedule/loop skills when available; otherwise report the unsupported persistence requirement
instead of assuming continuation.
