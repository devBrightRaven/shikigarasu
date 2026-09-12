---
name: shikigarasu
description: 'Coordinate parallel workstreams or independent reviews with native Codex agents. Skip simple single-task work.'
---

# Shikigarasu for Codex

Coordinate an authorized outcome with native Codex agents only when its shape requires delegation or independent review. Keep a simple bounded outcome in the main session and do the substantive work there; Shikigarasu supplies routing, queue, authority, and evidence rules without forcing a worker-shaped process.

## Trigger boundary

Activate this contract when Shikigarasu is named or when any automatic trigger below applies. Naming Shikigarasu selects this contract; asking to continue until done, requesting repeated execution and verification, or naming a persistent goal activates it only when the outcome needs coordination. Selection never by itself requires a child agent.

- The outcome contains multiple substantive independent workstreams.
- The work has disjoint write sets, dependency handoffs, meaningful fan-out, or another reason the main session cannot safely keep the work together.
- The user asks for agents, subagents, parallel work, delegation, or coordination.
- The work needs producer plus independent reviewer separation.
- The user asks to continue until done, perform repeated execution and verification, or run a persistent goal and the outcome genuinely needs queue or review coordination.

Do not dispatch merely because a keyword, role name, explicit Shikigarasu invocation, or continue request appears. A one bounded task or a purely mechanical check stays in the main session when no independent review is required; if the frozen policy requires an independent reviewer, or the user explicitly requests a native worker, use `spawn_agent` for that bounded ticket.

## Outcome-based routing

Classify the requested outcome before deciding whether to spawn. A role describes
the mode of work; it is not a mandatory agent, stage, persona, or six-step
process. The main session may perform one bounded role inline.

- **Explore** only when an unknown or blind spot is consequential and could
  change the outcome. Plain factual lookup, generic domain curiosity, and
  document-only analysis stay inline. Spawn only when the exploration is a
  substantive disjoint workstream or needs independent investigation.
- **Experiment** only when an empirical answer, benchmark, or hypothesis test
  is required. Before execution, state the question, method, pass/fail
  criterion, time/resource and cost limit, data boundary, and stop condition.
  Do not spend money, use production data, call an external service, or create
  a paid-model test without explicit authorization. Missing setup is a
  boundary, not permission to improvise.
- **Compare** when existing viable alternatives have material tradeoffs. Keep
  the evidence and recommendation separate from a material human-owned choice;
  do not silently select a provider, threshold, architecture, or priority when
  that choice would change the outcome, scope, cost, or data handling.
- **Implement** only an authorized chosen goal with observable acceptance
  criteria. A diagnosis-only, plan-only, or review-only request does not
  authorize edits.
- **Review** only an available artifact against a stated requirement or risk
  boundary. Apply the frozen tier 0/1/2 review policy; do not audit every
  trivial mechanical change, and never use the producer as its own independent
  reviewer.

Mode and delegation are separate decisions. Use native `spawn_agent` only when
the outcome genuinely needs multiple substantive disjoint workstreams,
dependency handoffs, meaningful fan-out, an independent reviewer required by
the frozen policy, or a native worker explicitly requested by the user. Do not
manufacture work to fill a queue. There is no fixed
six-stage sequence or six-agent/persona requirement. The Codex delegation
boundary is native-only: do not load or import another runtime's agent role,
host rules, or CLI, and do not use detached processes to simulate native
workers. A separately authorized read-only external adapter may supplement
evidence under its own bounded reference, but it is never a Codex worker or
coordinator.

## Run the queue

1. Translate the authorized outcome into tickets with explicit acceptance evidence and dependencies. Keep newly discovered in-scope work in the same queue.
2. For each ready ticket that genuinely needs a separate native worker, dispatch
   it with `spawn_agent` within currently available capacity and refill freed capacity
   as work completes; keep a simple bounded ticket in the main session
   and do not wait for a whole wave to finish.
3. Apply no fixed cap to total ticket count. When the queue is unusually large, notify the user of its size and expected batching without blocking authorized work.
4. Use Codex-native agent coordination. Do not simulate workers with detached processes or provision a separate tool stack per worker.

Track each ticket as `READY`, `IN_PROGRESS`, `REVIEW_1`, `REVIEW_2`, `FIX`, `CLOSED`, or `BLOCKED`, plus producer, reviewers, attempts, findings, and evidence.

## Spec-driven work and test execution

For an authorized spec-driven implementation, read [references/spec-driven-closure.md](references/spec-driven-closure.md). Keep the approved spec authoritative and map its requirement IDs to tickets, behavioral TDD receipts, and integration evidence. OpenSpec task checkboxes are a projection of the execution queue, not a second completion authority. Workers must return material spec conflicts to the coordinator rather than changing requirements to make tests pass.

Before closing a spec-driven ticket or integration, run `scripts/closure_gate.py` against its frozen contract and evidence. A `BLOCKED` result prevents closure; `CLOSABLE` only permits the coordinator to close after inspecting raw evidence and every independent review required by the frozen policy. The checker validates declared requirement receipts; the coordinator separately verifies ticket-to-requirement coverage, dependencies, and authoritative queue state. This is a coordinator protocol and evidence checker, not an unbypassable runtime or proof of evidence authenticity. Inventory must include relevant staged, unstaged, and untracked changes.

Freeze the review decision before work and record it in the manifest's
`review_policy`: tier `0` (mechanical) requires zero reviewers, tier `1`
(standard) requires one, and tier `2` (high) requires two. `count` must match
the tier, `reason` must be non-empty, and `frozen` must be JSON `true`.
Explicit tiered manifests must be checked with a separately supplied
`--review-baseline` JSON input or `--review-baseline-digest`; the manifest is
not an authority for lowering its own review requirement. Legacy manifests
without `review_policy` retain the previous two-reviewer requirement. A
`high_risk` or `gate_change` policy always uses tier 2, including changes to
the closure gate itself. The checker reports that it cannot prove baseline
authenticity or chronology.

For tests that may outlive a short tool call, read [references/test-execution.md](references/test-execution.md) and use `scripts/test_runner.py` to obtain a durable run handle before polling. Assign one execution owner; when child tools are unreliable, the coordinator runs tests while the producer edits. Never relaunch an uncertain run solely because a tool turn was interrupted. Missing results and environment failures are not behavioral RED or passing evidence.

## Dispatch natively

- Use `spawn_agent` for producers and independent reviewers. Use functional task roles rather than persona names.
- For every independent reviewer, call `spawn_agent` with `fork_turns="none"`; do not omit this argument or use `"all"`. Supply the review scope, acceptance criteria, applicable instructions, and artifact paths in the task message without producer conclusions or another reviewer's verdict.
- Use `send_message` for context that belongs to active work and `followup_task` for a new turn by an existing agent.
- Use `wait_agent` only while agents are working. Count the coordinator against the runtime's available collaboration capacity, fill only free slots, and refill them as agents finish.
- Give each ticket the smallest sufficient context: its contract, acceptance criteria, applicable instructions, dependencies, and evidence destination.
- If native coordination or enough distinct agents for the closure gate is unavailable, report the harness limitation instead of simulating independence.

## Gate closure

Require the number of review passes declared by the frozen tier for every
completed ticket, including when a pass reports no findings; high-risk work
still requires the old two-pass protocol (two review passes).

- Assign each pass to a fresh-context independent reviewer. The producer and
  every required reviewer must be different agents.
  For tier 2/high-risk work, the producer and both reviewers must be different agents.
- Give reviewers the ticket, acceptance criteria, applicable instructions, and raw diff or test evidence; do not leak the producer's conclusions or another reviewer's verdict.
- Treat producer tests and acceptance claims as evidence only. They never close a ticket.
- Send every Critical or Important finding back for a fix, then independently re-review the changed result.
- Enforce a collective ticket ceiling of two fix rounds after the initial reviews. All findings share that ceiling, and newly introduced findings do not reset it.
- Close only after every review pass required by the frozen tier has evaluated
  the final result and no Critical or Important finding remains. At the
  ceiling, mark remaining Critical or Important findings `BLOCKED`, preserve
  the evidence, and report the non-convergence.
- For tier 0 or tier 1, apply the same independent-review and finding rules to
  the number of reviewers required by the frozen tier. A reviewer re-reviewing
  narrowed changes supplies evidence bound to the new artifact digest; valid
  unrelated requirement/TDD evidence is retained rather than rerun.

## Route models portably

Follow the host's model-routing policy when one exists. Otherwise use capability-based routing:

- Keep the current coordinator for scope, user intent, queue state, integration, and routine arbitration.
- Use available lower-cost models for clear bounded worker tickets when they can satisfy the ticket contract.
- Use the strongest available model for consequential judgment, security-sensitive review, conflicting final arbitration, irreversible external action, publication, release, or final completion.
- Give independent reviewers fresh minimum context. Prefer model diversity when available, but never substitute model diversity for distinct agents and independent context.
- If requested capabilities or model diversity are unavailable, use supported models and disclose the degraded evidence. Do not launch detached sessions to manufacture a routing tier.

No worker or external model may redefine scope, negotiate user intent, choose the canonical source, make public commitments, commit, push, publish, or declare the overall outcome complete.

## Respect authority

Stay within the user's existing authority. Pause before external actions, irreversible changes, or scope expansion that need new authorization. Runtime persistence must not exceed the mechanism the user explicitly authorized.

Call `get_goal` when Shikigarasu starts to inspect whether a persistent goal already exists. Call `create_goal` only when the user explicitly requests a new persistent goal. If one is active, let it own cross-turn continuation. Call `update_goal` only to mark the objective complete after it is achieved, or blocked after the same blocking condition persists for at least three consecutive goal turns. Never use it to pause, resume, or control a budget. Without an active goal, own convergence only within the current turn and report unfinished queue state without claiming future continuation.

## Route bounded external review

External tools may supplement the queue only as bounded read-only workers or reviewers; they never inherit coordinator authority. Record requested and reported model identities, artifacts actually accessed, timeouts, fallbacks, refusals, and any loss of model diversity. Treat unverified identity, unverified artifact access, safety refusal, or same-model review as degraded evidence rather than a pass.

Read [references/agy-routing.md](references/agy-routing.md) before assigning work to agy. For presentation or document final-artifact review, also read [references/final-artifact-review.md](references/final-artifact-review.md). Use `scripts/agy_adapter.py` for bounded model discovery, read-only JSON calls, or the local-image vision gate.

## Report evidence

Finish with the authorized outcome, ticket states, producer/reviewer separation,
all required review results, acceptance evidence, fix attempts, blocked work,
notifications, and remaining limitations. Never report success for a ticket
that has not passed its required closure gates.
