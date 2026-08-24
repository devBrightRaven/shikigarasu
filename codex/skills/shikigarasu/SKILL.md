---
name: shikigarasu
description: 'Use when Shikigarasu is invoked; work has multiple substantive independent workstreams; the user requests agents, subagents, parallel work, delegation, or coordination; producer plus independent reviewer separation is needed; or the user asks to continue until done, perform repeated execution and verification, or run a persistent goal. Do not auto-trigger for one bounded task or a purely mechanical check.'
---

# Shikigarasu for Codex

Coordinate the authorized outcome through native Codex agents. Decompose, dispatch, arbitrate findings, refill capacity, and synthesize evidence rather than producing substantive tickets yourself.

## Trigger boundary

Activate when Shikigarasu is named, or when any automatic trigger applies:

- The outcome contains multiple substantive independent workstreams.
- The user asks for agents, subagents, parallel work, delegation, or coordination.
- The work needs producer plus independent reviewer separation.
- The user asks to continue until done, perform repeated execution and verification, or run a persistent goal.

Do not auto-trigger for one bounded task or a purely mechanical check. An explicit Shikigarasu invocation still activates it.

## Run the queue

1. Translate the authorized outcome into tickets with explicit acceptance evidence and dependencies. Keep newly discovered in-scope work in the same queue.
2. Delegate every substantive ready ticket. Dispatch within currently available worker capacity and refill freed capacity as work completes; do not wait for a whole wave to finish.
3. Apply no fixed cap to total ticket count. When the queue is unusually large, notify the user of its size and expected batching without blocking authorized work.
4. Use Codex-native agent coordination. Do not simulate workers with detached processes or provision a separate tool stack per worker.

Track each ticket as `READY`, `IN_PROGRESS`, `REVIEW_1`, `REVIEW_2`, `FIX`, `CLOSED`, or `BLOCKED`, plus producer, reviewers, attempts, findings, and evidence.

## Dispatch natively

- Use `spawn_agent` for producers and independent reviewers. Use functional task roles rather than persona names.
- Use `send_message` for context that belongs to active work and `followup_task` for a new turn by an existing agent.
- Use `wait_agent` only while agents are working. Count the coordinator against the runtime's available collaboration capacity, fill only free slots, and refill them as agents finish.
- Give each ticket the smallest sufficient context: its contract, acceptance criteria, applicable instructions, dependencies, and evidence destination.
- If native coordination or enough distinct agents for the closure gate is unavailable, report the harness limitation instead of simulating independence.

## Gate closure

Require two review passes for every completed ticket, including when the first pass reports no findings.

- Assign each pass to a fresh-context independent reviewer. The producer and both reviewers must be different agents.
- Give reviewers the ticket, acceptance criteria, applicable instructions, and raw diff or test evidence; do not leak the producer's conclusions or another reviewer's verdict.
- Treat producer tests and acceptance claims as evidence only. They never close a ticket.
- Send every Critical or Important finding back for a fix, then independently re-review the changed result.
- Enforce a collective ticket ceiling of two fix rounds after the initial reviews. All findings share that ceiling, and newly introduced findings do not reset it.
- Close only after both passes have evaluated the final result and no Critical or Important finding remains. At the ceiling, mark remaining Critical or Important findings `BLOCKED`, preserve the evidence, and report the non-convergence.

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

Finish with the authorized outcome, ticket states, producer/reviewer separation, both review results, acceptance evidence, fix attempts, blocked work, notifications, and remaining limitations. Never report success for a ticket that has not passed both closure gates.
