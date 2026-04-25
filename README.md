# shikigarasu

> 四季烏 meta-harness Layer 4 — four-axis sync personas for Claude Code.

A persona-based skill plugin that decomposes a single Claude Code session into four specialized roles (axes), each with its own tool whitelist, output structure, and accumulated cross-session memory. Inspired by the 四靈 (Four Symbols) elemental framework, mapped to seasonal crow personas.

## The four axes

| Skill | Crow | Element | Role |
|-------|------|---------|------|
| `shikigarasu:seiran` | 青嵐 (Azure Tempest) | 青龍 · 春 · 木 | Strategy / option generation / tradeoff framing |
| `shikigarasu:shuen` | 朱焔 (Crimson Flame) | 朱雀 · 夏 · 火 | Scout / blind-spot hunter / assumption stress-test |
| `shikigarasu:hakuso` | 白霜 (White Frost) | 白虎 · 秋 · 金 | Audit / gatekeeping / pass-block verdict |
| `shikigarasu:genen` | 玄淵 (Black Abyss) | 玄武 · 冬 · 水 | Execution / build / refactor / artifact production |

Each axis has:

- **A tool whitelist** that limits its scope (e.g., Seiran cannot Edit files, Gen'en cannot WebSearch)
- **A mandatory three-section output structure** for consistency
- **Identity continuity via dated memory file** in `agents-vault/shikigarasu/<name>.md` (always loaded) plus `<name>-observations.md` (loaded on demand)
- **Handoff protocol** suggesting the next axis when the current one's work is done

## Why personas instead of a generic agent

A single all-purpose Claude session tends to drift across roles within one task — strategizing while implementing, auditing while exploring. The shikigarasu structure forces explicit role-switching, which:

- Keeps each turn's reasoning bounded to its proper scope
- Accumulates role-specific memory (Seiran's strategic stances vs. Hakusō's audit cautions)
- Makes handoffs explicit rather than silent context drift
- Pairs naturally with cross-vendor consultation (the same axis can run on Claude or GPT for bias detection)

## Design notes

- **Thin framing**: Empirical testing (n=32, 2026-04-24) showed that thick mythology / archetype priming had no measurable effect on Opus 4.7 or GPT-5.4 output quality on either execution or strategic tasks. The plugin therefore uses minimal framing — focus + tool whitelist + handoff protocol — and lets the model's native task understanding do the work.
- **Skill priority**: All four axes are designed to take precedence over generic competitor skills (e.g., `superpowers:brainstorming`, `hirameki:frame`) when a clear axis match exists. When auto-trigger competition fails, slash commands (`/shikigarasu:<axis>`) provide forced invocation.
- **Memory split**: Identity files (Stance + Cautions) load every time the skill is invoked. Observation logs are kept in separate files and only loaded on demand to prevent context rot.

## Install

```sh
/plugin marketplace add devBrightRaven/shikigarasu
/plugin install shikigarasu@shikigarasu
/reload-plugins
```

After install, the four axes are available as auto-triggered skills (when the request clearly matches an axis) and as slash commands (`/shikigarasu:seiran`, `/shikigarasu:shuen`, `/shikigarasu:hakuso`, `/shikigarasu:genen`).

## Memory files

The plugin reads identity and writeback to files at `D:/Obsidian/agents-vault/shikigarasu/` (currently hardcoded; cross-platform path resolution planned for future revisions). Each axis has:

- `<axis>.md` — identity, stance, cautions (always loaded)
- `<axis>-observations.md` — dated observation log (Grep on demand)

Memory writeback is opt-in: the skill offers updates at session end and only writes after explicit user confirmation.

## Layer model

This plugin implements **Layer 4** of the four-season-crow harness architecture (sync, Claude-side). Layer 5 (async, OpenAI-side, Telegram bot daemons) is a separate stack at `agents-vault/openclaw/` with its own naming (Omoikane / Sarutahiko / Kotodama / Ishikori). Cross-vendor consultation maps Layer 4 axis ↔ Layer 5 daemon by function, not by name.

## License

MIT
