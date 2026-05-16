# Shikigarasu Axis Dispatch

**Guard**: this rule only applies if the kishi agent is installed (i.e. `~/.claude/agents/kishi.md` exists, or kishi appears in the session's available agent list). If kishi is NOT installed, treat this entire file as inactive — do not surface Kishi suggestions in a session without the agent that backs them.

When a user request matches a shikigarasu-flavored task (strategy / scout / execution /
audit / research), **suggest** invoking Kishi rather than executing directly. Kishi is
the dispatcher; she will route to the right worker (seiran/shuen/genen/hakuso/soen)
and synthesize results.

## When to suggest Kishi

| Intent in user prompt | Worker Kishi will route to |
|---|---|
| Bounded decision with options (scope, positioning, roadmap, priorities) | seiran (策略) |
| Code writing, refactor, build, implementation, "make it work" | genen (執行) |
| Code review, audit, PR gate, security check | hakuso (審判) |
| Research, exploration, blind-spot scan, debugging, "why is this weird" | shuen (探路) |
| Hypothesis-driven experiment, benchmark, "what happens if" | soen (蒼炎) |
| Multi-axis (e.g., "review then refactor") | Kishi orchestrates the sequence |

## Phrasing

> 這看起來是 shikigarasu 多軸工作。建議讓 Kishi 接手調度 — 我會用 `claude --agent kishi -p "<task>"` 起一個獨立 process。要切還是我繼續？

Wait for confirmation, then invoke via Bash:

```bash
claude --agent kishi -p "<task description>"
```

**DO NOT invoke as a subagent** (i.e. do not use `Agent(subagent_type=kishi, ...)`). Subagents have no `Agent` tool in Claude Code, so kishi-as-subagent cannot dispatch and will either abort or self-execute. Kishi must run as a main-thread agent. Verified 2026-05-15; see memory `kishi-must-run-as-main-agent`.

For pre-review of routing without dispatching, append ` [plan only]` to the task:

```bash
claude --agent kishi -p "<task description> [plan only]"
```

Power-user shortcut: if you already know the axis, slash commands still work
(`/shikigarasu:seiran` etc.) — those invoke the plugin skill directly.

## Force-check token: `?ki`

If the summoner's message contains `?ki` (anywhere), **override all skip conditions below**. Perform the axis-check regardless and offer one axis (or explicitly say "no match").

Why this exists: skip conditions are conservative; `brightraven-resolve` auto-trigger can silently pre-empt this rule; the summoner sometimes knows a turn is axis-worthy when surface cues don't show it.

When `?ki` fires:
1. State the matching axis + quote the bit of the task that matches.
2. Note what would have happened without `?ki` (e.g. "Would have skipped because: continuation of prior turn"). This helps the summoner learn when the token is load-bearing vs redundant.
3. Wait for `yes` / axis override / `no`.

Example:
> Summoner: `?ki 我想搞清楚 migration script 為什麼掛在 Postgres`
> You: `?ki → shuen (research). Match: "搞清楚 X 為什麼掛". (Without ?ki, would have suggested anyway.) Proceed with claude --agent shuen -p "..."? (yes / pick axis / no)`

## Skip the suggestion when

(Override: `?ki` in the summoner's message bypasses everything below.)

- User said "just do it" / "直接做" / "skip shikigarasu"
- Casual chat, factual lookup, one-liner
- Already in a Kishi-dispatched flow this turn
- Request is clearly outside all axes (file listing, status query, env check)
- User just rejected a shikigarasu suggestion this session
- Already triggered by `brightraven-resolve:resolve` — defer to resolve

## Not handled here

Async / monitoring / scheduled requests → Layer 5 OpenClaw daemon, not Layer 4 axis.
