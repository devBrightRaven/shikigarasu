# Shikigarasu Autonomous Harness Implementation Plan

> HISTORICAL PLAN (provenance only). Superseded 2026-07-20 by the shikigarasu-common consolidation; do not follow as current instructions.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore Shikigarasu as a subagent-first autonomous harness for Claude and add a Codex-native adapter with persistent queue replenishment, two independent review passes, and goal-aware convergence.

**Architecture:** Keep the behavioral contract in one agent-agnostic Codex/Agent Skill under this repository. Claude Kishi and dispatch rules remain platform adapters that carry the same load-bearing contract without depending on another agent's runtime. Deploy copies through the existing dotclaude/dotcodex personal-layer workflows; do not edit caches.

**Tech Stack:** Markdown Agent Skills, Claude Code agents/rules, Codex native collaboration tools, PowerShell verification.

## Global Constraints

- Every substantive task is executed by a subagent; the coordinator owns decomposition, arbitration, queue state, and synthesis.
- Every completed work item receives at least two independent fresh-context review passes, even if the first is clean.
- Producer and reviewer must differ; producer evidence alone never closes a ticket.
- Continue until acceptance is proven and no Critical/Important finding remains, subject to two fix rounds per surviving finding.
- Large queues have no fixed total cap; warn without blocking and process in capacity-aware waves.
- Do not implement fan-out as hundreds of detached CLI sessions or duplicate per-agent MCP servers.
- `/goal` owns cross-turn continuation; Shikigarasu owns within-turn queue replenishment and convergence.
- Do not modify plugin caches. Do not commit or push.

---

### Task 1: Agent-agnostic harness core

**Files:**
- Create: `agent-skills/shikigarasu/SKILL.md`
- Create: `agent-skills/shikigarasu/agents/openai.yaml`

**Interfaces:**
- Consumes: a user-authorized outcome, applicable repository/personal instructions, current agent capacity.
- Produces: a replenished ticket queue, two-pass independent review gates, bounded convergence, and a final evidence report.

- [ ] Preserve the three failing RED scenarios as acceptance cases.
- [ ] Initialize the skill with the system skill-creator script.
- [ ] Write the minimum platform-neutral contract covering queue, waves, review separation, retries, notification, and goal boundary.
- [ ] Validate with `quick_validate.py` and rerun all three scenarios against the new skill.

### Task 2: Claude adapter restoration

**Files:**
- Modify: `agents/kishi.md`
- Modify: `rules/common/shikigarasu-dispatch.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: the agent-agnostic harness contract plus Claude Agent/SendMessage semantics.
- Produces: Kishi behavior that cannot close after one/self review and can replenish capacity-aware work waves.

- [ ] Add the load-bearing review and queue contract to Kishi.
- [ ] Make common-rule precedence and the `/goal` boundary explicit in dispatch documentation.
- [ ] Keep external-action interruption gates and current-authority ordering intact.
- [ ] Validate the Claude plugin and rerun RED scenarios as GREEN.

### Task 3: Personal-layer deployment

**Files:**
- Create: `C:/Code/dotcodex/agent-skills/shikigarasu/`
- Create: `C:/Code/dotclaude/agent-skills/shikigarasu/`
- Modify: `C:/Code/dotclaude/agents/kishi.md`
- Modify: `C:/Code/dotclaude/rules/common/shikigarasu-dispatch.md`
- Deploy: `~/.agents/skills/shikigarasu/`, `~/.claude/agents/kishi.md`, `~/.claude/rules/common/shikigarasu-dispatch.md`

**Interfaces:**
- Consumes: verified canonical source artifacts.
- Produces: hash-identical runtime copies without symlink dependency.

- [ ] Back up every target before replacement.
- [ ] Copy only verified artifacts; do not copy Claude personal config into a project repository.
- [ ] Verify hashes across canonical, backup repos, and runtime.

### Task 4: Forward verification

**Files:**
- Test only; no new production files.

**Interfaces:**
- Consumes: deployed Claude and Codex adapters.
- Produces: evidence for double review, producer separation, large-queue waves, bounded non-convergence, goal boundary, and process cleanup.

- [ ] Run fresh-context Claude and Codex behavioral tests.
- [ ] Independently review the resulting traces against the contract.
- [ ] Confirm no detached-process or MCP multiplication.
- [ ] Report remaining limitations without commit or push.
