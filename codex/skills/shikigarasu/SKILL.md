---
name: shikigarasu
description: Use when the user invokes Shikigarasu, asks Codex to continue until done across multiple tasks, requests autonomous repeated execution and verification, authorizes coordinated subagents, or starts a persistent goal.
---

# Shikigarasu for Codex

**REQUIRED SUB-SKILL:** Use `shikigarasu-common` for the queue, closure, authority, and evidence contract.

Coordinate rather than producing substantive tickets yourself. Decompose, dispatch, arbitrate findings, replenish the queue, and synthesize evidence.

## Preserve user-facing authority

**User-facing authority floor:** Run the main session and Shikigarasu coordinator on `gpt-5.6-sol` at `medium` effort or higher. Lower-tier models may execute bounded tickets, but must not redefine scope, negotiate user intent, arbitrate conflicting findings, or declare the overall goal complete.

- Use `gpt-5.6-luna` at `high` for clear, bounded worker tickets when the runtime exposes it.
- Keep intermediate judgment with the Sol coordinator at `medium`; do not add a separate Terra routing layer.
- Escalate consequential arbitration and final goal review to Sol at `xhigh`.
- Do not use `ultra` by default. Shikigarasu already owns subagent decomposition and concurrency; reserve Ultra for an exceptional task whose required decomposition cannot be handled by the existing queue.
- Pass model or effort overrides only with `fork_turns="none"` or a bounded history fork. A full-history fork inherits the parent configuration and does not accept overrides.
- If the runtime cannot route a requested lower-tier worker, keep the ticket on a supported model. Do not work around the limitation with detached sessions.
- After a Codex upgrade or model-routing change, run `python -X utf8 scripts/probe_luna_high.py` from the `dotcodex` repository for a live Luna High smoke test. Do not run the quota-consuming probe on every task.

## Use Codex-native coordination

- Treat explicit invocation or authorization of Shikigarasu as authorization to use subagents for the requested outcome. It does not authorize unrelated scope or external actions.
- Use `spawn_agent` for producers and independent reviewers. Use functional task roles; do not copy Claude persona names, fixed model routing, hooks, commands, or `Task*` syntax.
- Use `send_message` for context that belongs to active work and `followup_task` for a new turn by an existing agent. Use `wait_agent` only while live agents are doing work; do not poll when no work is running.
- Count the coordinator against the runtime's available collaboration capacity. Fill only free slots, then refill them as agents finish. Never hardcode a worker count or a total-ticket limit.
- Give reviewers fresh context with `fork_turns="none"` and only the ticket contract, applicable instructions, and raw evidence. Producer and both reviewers must be distinct agents.
- Do not launch detached `codex exec` sessions or one MCP stack per ticket. If native subagent coordination or enough distinct agents for the closure gate is unavailable, report the harness limitation instead of simulating independence.

## Route bounded agy work

Use agy only as a read-only external worker or reviewer inside this architecture; do not create a
second orchestrator. Discover its version and models at runtime. Keep Codex authority over scope,
canonical sources, public commitments, writes, publication, and completion.

Read [references/agy-routing.md](references/agy-routing.md) before assigning work to agy. For a
presentation or document final-artifact review, also read
[references/final-artifact-review.md](references/final-artifact-review.md) and enforce its
one-review/one-revision limit. Use `scripts/agy_adapter.py` for bounded model discovery, read-only
JSON calls, or the local-image vision gate.

## Bound continuation

Call `get_goal` when Shikigarasu starts to inspect whether a persistent goal already exists. Call `create_goal` only when the user explicitly requests a new persistent goal. If one is active, let it own cross-turn continuation. Call `update_goal` only to mark the objective complete after it is achieved, or blocked after the same blocking condition persists for at least three consecutive goal turns; never use it to pause, resume, or control a budget. Without an active goal, own convergence only within the current turn and report unfinished queue state without claiming future continuation.
