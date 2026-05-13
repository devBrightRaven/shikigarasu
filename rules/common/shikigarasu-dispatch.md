# Shikigarasu Axis Dispatch

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

> 這看起來是 shikigarasu 軸的工作。建議讓 Kishi 接手調度。要切還是我繼續？

Wait for confirmation before invoking `Agent(subagent_type=kishi, ...)`.

Power-user shortcut: if you already know the axis, slash commands still work
(`/shikigarasu:seiran` etc.) — those invoke the plugin skill directly.

## Skip the suggestion when

- User said "just do it" / "直接做" / "skip shikigarasu"
- Casual chat, factual lookup, one-liner
- Already in a Kishi-dispatched flow this turn
- Request is clearly outside all axes (file listing, status query, env check)
- User just rejected a shikigarasu suggestion this session
- Already triggered by `brightraven-resolve:resolve` — defer to resolve

## Not handled here

Async / monitoring / scheduled requests → Layer 5 OpenClaw daemon, not Layer 4 axis.
