# Shikigarasu Axis Dispatch

**Availability guard**: evaluate each request independently. Kishi is not a
global precondition for routing. A matching single axis may be dispatched when
that axis is available even if Kishi is absent. Kishi (or the interactive main
session applying the coordinator protocol) is needed only when the requested
outcome genuinely spans multiple axes.

Before dispatching, verify that the selected axis is available in the current
session or through an enabled namespaced command/agent surface. If it is not
available, disclose the unavailable capability and do not simulate a call,
silently substitute another axis, or claim that the work ran. If no suitable
axis is available, the main session may answer within its own authority or
state the concrete block. An absent Kishi must not disable an available single axis.

Match the user's intent and requested authority, not an isolated keyword.
Naming a role, mentioning Shikigarasu, or asking to continue until the work
is done does not by itself require a subagent or the coordinator; the shape
of the requested outcome decides. The main session keeps only work that
states no acceptance criterion and finishes in a handful of tool calls. An
explicitly authorized goal with a stated observable acceptance criterion
(tests, lint, build) routes to genen even when it looks small; a general
inline exemption in personal rules does not override that row. Route a
direct single-axis task with no suggestion round-trip. Automatic
coordinator selection is outcome-shaped: when an authorized outcome genuinely
needs multiple substantive roles, dependency handoffs, or meaningful fan-out,
use the coordinator even if the user never names Kishi. Skip it for one-axis,
trivial, or explicitly inline work. The interactive main session applies the
Kishi protocol with its Agent tool; it does not invoke Kishi as a nested
coordinator. Kishi completes the authorized local, reversible batch and
interrupts only for irreversible external action, new authority, material
scope expansion, or an outcome-changing fork. `[plan only]` remains an explicit
preview mode.

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
| Concrete consequential unknown or blind spot that could change the outcome | shuen 探路 |
| Existing viable options with material tradeoffs that need a human-owned choice | seiran 策略 |
| Explicitly authorized selected bounded goal with observable acceptance criteria | genen 執行 |
| Existing artifact plus a request for independent review against requirements/risk | hakuso 審判 |
| Empirical answer, benchmark, or hypothesis test is required | soen 蒼炎 (Agent tool; no slash command by design) |
| Authorized outcome genuinely needs ≥2 substantive axes, dependency handoffs, or meaningful fan-out (for example review→fix→verify or scout→build) | coordinator orchestrates |

Single known available axis → that worker directly through the Agent tool, or a
slash command when available; do not wrap one-axis jobs in kishi. If the user
explicitly names an axis, honor it when available; otherwise disclose the
unavailable selected axis instead of fabricating a call.

Boundary rules:

- A plain factual lookup does not become Shuen merely because it says
  “research”. Route to Soen when the requested outcome needs empirical
  evidence from a test or benchmark within the authorized scope; the user need
  not use the word “benchmark”.
- Domain curiosity or document-only analysis alone does not trigger Soen. Soen
  may infer a narrow falsifiable question and run a minimal safe measurement
  when empirical evidence is required, but must predeclare method, pass/fail,
  time/resource limits, and a stop condition.
- Seiran requires existing viable choices and a material tradeoff; do not add a
  strategy stage to a settled choice.
- Genen requires implementation authority; a diagnosis-only question does not
  authorize a fix.
- Hakuso requires an available artifact and a review boundary; do not audit
  every trivial mechanical edit.
- An outcome with multiple substantive dependencies may use the coordinator,
  but there is no fixed six-axis sequence and no keyword/persona requirement.
  Workers do not spawn or dispatch other axes; boundary handoff stays with the
  coordinator.
- Preserve the applicable worker gates and evidence records. In particular, a
  security probe must retain its red-team authorization gate and raw evidence;
  the coordinator does not implement production changes or make a human-owned
  strategy choice.

kishi invocation by weight:

- **Light/medium, interactive**: the current main session applies the Kishi coordinator protocol directly using its Agent tool. Do not invoke Kishi as a nested agent.
- **Detached only when explicitly requested**: start exactly one `claude --agent kishi -p "<task>"` parent coordinator. Do not escalate an interactive task to detached mode merely because it is heavy. Append ` [plan only]` to preview routing without dispatching. Never start one CLI process per ticket; the parent uses native Agent coordination.

For multi-axis tasks, pass the full requested outcome to Kishi once. Do not
return to the user between scout, strategy, execution, and audit phases unless
the interruption policy above applies.

## Execution selection and adaptation

Axis routing picks the mode of work; execution selection picks the smallest
sufficient path for it. The shared reference `references/execution-selection.md`
in `shikigarasu-common` (contract ID `shikigarasu-execution-selection`, version 1)
owns the path table and the adapt-using-evidence rule. This rule only states what
each shared path means on the Claude host; it adds no dispatcher.

| Shared path | Claude native form | Boundary |
|---|---|---|
| Direct | the main session's own tools | no ticket, no routing report |
| Skill / Playbook | an installed skill or slash command, loaded on demand | respect its invocation metadata and prerequisites |
| Delegated | one `Agent` worker with an explicit file allowlist and acceptance | the owning axis when one exists |
| Parallel | several `Agent` calls in one turn, within available slots, disjoint writes | parallel tool reads are not parallel agents |
| Iterative | repeat inside the turn with a stated stop condition | shares the collective fix ceiling |
| Dynamic | compose existing steps for this task only | no new orchestrator, no saved pipeline |
| Durable | not provided natively: Task state and the queue live in the session; background Bash gives a run handle for one command only | report unsupported instead of promising survival |

Adapt from evidence, not from the failure count. An infrastructure failure with
no usable result (tool error, rate limit, timeout, missing capability) may be
retried once as a new invocation. An acceptance failure with a usable result
goes back as a strictly narrower ticket and shares the collective two-fix-round
ceiling. A change that has no effect or merely moves the error reopens the
premise, not the retry. For a consequential path choice keep the compact record
the shared reference names (reason, task/run identity, capabilities and
revisions, acceptance, limits, result, unresolved dependencies); simple tasks
need no routing report, and expected cost stays `unknown` unless the runtime
reports usage.

## Still skipped (relevance filter, not a confirmation gate)

- Casual chat, factual lookup, one-liner, or clearly outside all axes
- User explicitly said "skip shikigarasu", "inline", "不要分工", or otherwise
  directed the main session not to dispatch workers — handle inline/generic
  instead. Ordinary "直接做" / "just do it" still routes when a bounded axis
  owns the requested outcome.
- `brightraven-resolve:resolve` already triggered — defer to resolve
- Use capacity-aware waves bounded by currently available subagent slots.
  Refill freed slots immediately; do not launch hundreds of workers at once or
  stack several Kishi flows concurrently. There is no fixed cap on total
  tickets: notify unusually large queues and their expected batching without blocking authorized work.
  In short, do not stack Kishi flows.

`?ki` anywhere in the message is an explicit user override, not an inferred
keyword: it forces axis routing even inside the skip zone. State the chosen
axis + the matching fragment in one line, then dispatch — no confirmation wait.

Async / monitoring / scheduled requests are not an axis job. Route to the
user's OpenClaw daemon or schedule/loop skills when available; otherwise report the unsupported persistence requirement
instead of assuming continuation.
