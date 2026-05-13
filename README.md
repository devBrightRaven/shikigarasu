# shikigarasu

> 四季烏 meta-harness Layer 4 — six-axis sync personas for Claude Code.

A persona-based plugin that decomposes a Claude Code session into six specialized roles (axes), each with its own tool whitelist, output structure, and cross-session memory. Explicit role-switching prevents context drift and accumulates role-specific knowledge over time.

---

## The six axes

| Axis | Kanji | Role | Model |
|------|-------|------|-------|
| `kishi` | 鬼子 | Coordinator — dispatches workers, synthesizes | opus |
| `seiran` | 青嵐 | Strategy — bounded tradeoff analysis | opus |
| `shuen` | 朱焔 | Scout — blind spots, assumption stress-test | sonnet |
| `genen` | 玄淵 | Execution — build, refactor, fix | sonnet |
| `hakuso` | 白霜 | Audit — pass/block verdict | sonnet |
| `soen` | 蒼炎 | Scientist — hypothesis-driven experiments | sonnet |

Kishi is the recommended entry point for multi-axis tasks. Single-axis tasks can invoke directly via slash command or user agent.

---

## Installation

Shikigarasu has three independent parts. Install all three for full functionality.

### 1. Plugin (slash commands)

```sh
/plugin marketplace add devBrightRaven/shikigarasu
/plugin install shikigarasu@shikigarasu
/reload-plugins
```

Provides `/shikigarasu:seiran`, `/shikigarasu:shuen`, `/shikigarasu:genen`, `/shikigarasu:hakuso`, `/shikigarasu:soen` as slash commands.

### 2. User agents

Copy the six agent definitions into your Claude Code agents directory:

```sh
cp agents/*.md ~/.claude/agents/
```

Restart your Claude Code session. This enables the `kishi` coordinator and all five workers as user agents — usable without slash commands, and required for Kishi to dispatch workers.

### 3. Dispatch rule

Copy the dispatch rule into your Claude Code rules directory:

```sh
mkdir -p ~/.claude/rules/common
cp rules/common/shikigarasu-dispatch.md ~/.claude/rules/common/
```

This instructs the main Claude session to proactively suggest routing to Kishi when a request matches a shikigarasu axis. Without this file, Claude will not suggest axis dispatch — you would need to invoke slash commands or agents manually.

**Lifecycle note**: The dispatch rule and agents are personal dotfiles — they persist independently of the plugin. Disabling the plugin removes slash commands but leaves agents and the dispatch rule intact. To fully remove shikigarasu, delete the dispatch rule and agent files manually.

---

## Confirming installation

After setup, verify each part:

```sh
# 1. Plugin slash commands
/shikigarasu:seiran    # Should activate the strategy axis

# 2. User agents
# In a Claude Code session, ask: "use the kishi agent to..."
# Kishi should respond and offer to dispatch workers.

# 3. Dispatch rule
# In a Claude Code session, describe a multi-step task.
# Claude should proactively suggest: "這看起來是 shikigarasu 軸的工作。建議讓 Kishi 接手調度。"
```

---

## Vault configuration

Three axes (Kishi, Shuen, Soen) can write memory and research artifacts to a vault. Configure by creating `~/.claude/vault-local.md`:

```yaml
vault: /path/to/your/vault          # root of your knowledge vault
agents_vault: /path/to/agents-vault # where agent memory files live
research: _subfolder/research/      # relative to vault, for Soen artifacts
```

**Fallback behavior when `vault-local.md` is absent or a key is missing:**

| Axis | Artifact type | Fallback path |
|------|--------------|---------------|
| Kishi | Dispatch transcripts | `~/.shikigarasu/` |
| Shuen | Scout memory | `~/.shikigarasu/` |
| Soen | Research artifacts | `~/.claude/sessions/research-<topic>-<date>.md` |

The axes always show the target path before writing and require explicit confirmation. Nothing is written silently.

---

## Memory system

Each axis that maintains cross-session memory uses two files:

| File | Content | When loaded |
|------|---------|-------------|
| `<axis>.md` | Identity, Stance, Cautions | Always, at skill invocation |
| `<axis>-observations.md` | Dated observation log | On demand only — Grep when user references past work |

**Stance** accumulates stable preferences the axis has developed. **Cautions** are actionable lessons learned. **Observations** are a running log of session findings.

The observation file is intentionally excluded from default loading to prevent context rot as it grows. It is only Grep'd when the user references prior work ("上次", "之前") or when the current topic matches an existing Stance or Caution.

**Writeback is opt-in.** At the end of a substantive session, the axis offers to update its memory files. Nothing is written without explicit user confirmation.

Create stub memory files for each axis you use:

```sh
mkdir -p /path/to/agents-vault/shikigarasu
touch /path/to/agents-vault/shikigarasu/seiran.md
touch /path/to/agents-vault/shikigarasu/shuen.md
touch /path/to/agents-vault/shikigarasu/genen.md
touch /path/to/agents-vault/shikigarasu/hakuso.md
touch /path/to/agents-vault/shikigarasu/soen.md
```

If a memory file is missing when an axis invokes, the axis notes the gap and proceeds with defaults.

---

## Usage patterns

**Orchestrated (recommended for multi-axis tasks)**

Describe your task in natural language. If the dispatch rule is installed, Claude will suggest routing to Kishi. Confirm, and Kishi dispatches the right workers:

> "Review this PR and fix the critical issues."
> → Claude suggests Kishi → Kishi dispatches Hakuso (audit), then Genen (fix)

**Direct single-axis**

Invoke a specific axis when you know which one you need:

```sh
/shikigarasu:seiran   # strategy / decision framing
/shikigarasu:shuen    # scouting / blind spots
/shikigarasu:genen    # execution / build / fix
/shikigarasu:hakuso   # audit / code review
/shikigarasu:soen     # hypothesis-driven research
```

Or via user agent: "use the seiran agent to frame this decision."

**Skip shikigarasu entirely**

Say "just do it" / "直接做" / "skip shikigarasu" to bypass dispatch suggestions for the current task.

---

## Design notes

- **Thin framing**: Empirical testing (n=32, 2026-04-24) showed thick mythology / archetype priming had no measurable effect on Opus 4.7 or GPT-5.4 output quality on execution or strategic tasks. Axes use minimal framing — tool whitelist + output structure + handoff protocol.
- **Memory split**: Identity (Stance + Cautions) loads every invocation. Observations are a separate file, Grep'd only when relevant. This prevents unbounded context growth as observation logs accumulate.
- **Kishi as coordinator**: Kishi dispatches workers via the Agent tool. It cannot edit files, run commands, or browse the web — it only reads context and routes. This keeps the coordination layer free of side effects.
- **Handoff protocol**: Each axis suggests the next appropriate axis at the end of its work. Handoffs are suggestions, not automatic triggers — the user confirms each transition.
- **Plugin lifecycle**: The plugin provides slash commands only. Agents and the dispatch rule are personal dotfiles managed independently. Disabling the plugin does not remove agents or rules.

---

## Layer model

This plugin implements **Layer 4** of the four-season-crow harness (sync, Claude-side). Layer 5 (async, OpenAI-side, Telegram bot daemons) is a separate stack with its own naming convention. Cross-vendor consultation maps Layer 4 axis to Layer 5 daemon by function.

---

## License

MIT
