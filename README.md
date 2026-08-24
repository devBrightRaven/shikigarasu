# shikigarasu

> 四季烏 meta-harness Layer 4 — six-axis sync personas for Claude Code.

A persona-based plugin that decomposes a Claude Code session into six specialized roles (axes), each with its own tool whitelist and output structure. Configured optional memory is used only by axes whose contracts explicitly support it.

---

## The six axes

| Axis | Kanji | Role | Model |
|------|-------|------|-------|
| `kishi` | 鬼子 | Coordinator — dispatches workers, synthesizes | sonnet |
| `seiran` | 青嵐 | Strategy — bounded tradeoff analysis | opus |
| `shuen` | 朱焔 | Scout — blind spots, assumption stress-test | sonnet |
| `genen` | 玄淵 | Execution — build, refactor, fix | sonnet |
| `hakuso` | 白霜 | Audit — pass/block verdict | opus |
| `soen` | 蒼炎 | Scientist — hypothesis-driven experiments | sonnet |

Kishi is the recommended entry point for multi-axis tasks. Single-axis tasks can invoke directly via slash command or user agent.

---

## Installation

<!-- CODEX_INSTALL_START -->
### Codex

From a downloaded checkout, add this repository as a local marketplace and install its self-contained Codex plugin:

```sh
codex plugin marketplace add .
codex plugin add shikigarasu@shikigarasu-codex
```

After pulling an update, run the `codex plugin add` command again, then start a new thread so Codex discovers the refreshed skill. The Codex plugin does not require personal `AGENTS.md` changes or the Claude shared contract.
<!-- CODEX_INSTALL_END -->

While enabled, the plugin supplies namespaced agents, commands, and rules. The copying steps below are optional and create unnamespaced personal entrypoints.

### 1. Plugin (slash commands)

```sh
/plugin marketplace add devBrightRaven/shikigarasu
/plugin install shikigarasu@shikigarasu
/reload-plugins
```

Provides `/shikigarasu:seiran`, `/shikigarasu:shuen`, `/shikigarasu:genen`, and `/shikigarasu:hakuso` as slash commands. Soen is Agent-only; there is no `/shikigarasu:soen` slash command.

### 2. Optional unnamespaced user agents

Copy the six agent definitions into your Claude Code agents directory:

```sh
cp agents/*.md ~/.claude/agents/
```

Restart your Claude Code session. This enables unnamespaced personal agent entrypoints for the `kishi` coordinator and all five workers.

### 3. Optional unnamespaced dispatch rule

Copy the dispatch rule into your Claude Code rules directory:

```sh
mkdir -p ~/.claude/rules/common
cp rules/common/shikigarasu-dispatch.md ~/.claude/rules/common/
```

This instructs the main Claude session to route multi-axis work directly to Kishi and single-axis work to the matching worker, without an extra suggestion/confirmation round.

**Lifecycle note**: Disabling the plugin removes its namespaced components; copied personal agents remain independently, as does any copied dispatch rule. Remove those personal copies manually when no longer wanted.

---

## Confirming installation

After setup, verify each part:

```sh
# 1. Plugin slash commands
/shikigarasu:seiran    # Should activate the strategy axis

# 2. User agents
# In an interactive Claude Code session, the main session applies the Kishi protocol using its Agent tool.
# For detached work, start one `claude --agent kishi -p "..."` parent coordinator.

# 3. Dispatch rule
# In a Claude Code session, describe a multi-step task.
# Claude should route directly and complete the local batch before returning.
```

---

## Vault configuration

Soen can write research artifacts to a configured vault. Shuen may read configured optional memory but writes durable reports only to the coordinator-provided path or OS temp. Configure by creating `~/.claude/vault-local.md`:

```yaml
vault: /path/to/your/vault          # root of your knowledge vault
agents_vault: /path/to/agents-vault # where agent memory files live
shikigarasu: shikigarasu/           # ski_dir under agents_vault
research: _subfolder/research/      # relative to vault, for Soen artifacts
```

For Shuen, `shikigarasu:` maps to `ski_dir`; both `agents_vault` and `shikigarasu` must resolve or optional memory is skipped.

**Fallback behavior when `vault-local.md` is absent or a key is missing:**

| Axis | Artifact type | Fallback path |
|------|--------------|---------------|
| Shuen | Optional memory | Skip when `vault-local.md`, `agents_vault`, or `ski_dir` is unresolved; durable reports use the coordinator-provided path or OS temp. |
| Soen | Research artifacts | `$TEMP/soen-<topic>-<date>.md` (Windows) or `/tmp/soen-<topic>-<date>.md` (Unix) — vault path preferred when `vault-local.md` resolves `{vault}/{research}/`. Never under `~/.claude/` (deny-list). |

Ordinary task artifacts use the requested project/output path without another confirmation. Optional memory writeback happens only when explicitly requested.

---

## Memory system

Each axis that maintains cross-session memory uses two files:

| File | Content | When loaded |
|------|---------|-------------|
| `<axis>.md` | Identity, Stance, Cautions | Always, at skill invocation |
| `<axis>-observations.md` | Dated observation log | On demand only — Grep when user references past work |

**Stance** accumulates stable preferences the axis has developed. **Cautions** are actionable lessons learned. **Observations** are a running log of session findings.

The observation file is intentionally excluded from default loading to prevent context rot as it grows. It is only Grep'd when the user references prior work ("上次", "之前") or when the current topic matches an existing Stance or Caution.

**Writeback is opt-in.** Axes do not offer it after every run; request memory writeback explicitly when wanted.

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

Describe the full outcome in natural language. If the dispatch rule is installed, the interactive main session applies Kishi's coordinator protocol with its Agent tool and returns once. Detached mode uses one `claude --agent kishi -p` parent, never one CLI process per ticket:

> "Review this PR and fix the critical issues."
> → Kishi dispatches Hakuso (audit), Genen (fix), then Hakuso reviewer 1 and Hakuso reviewer 2 independently review after the final change

**Direct single-axis**

Invoke a specific axis when you know which one you need:

```sh
/shikigarasu:seiran   # strategy / decision framing
/shikigarasu:shuen    # scouting / blind spots
/shikigarasu:genen    # execution / build / fix
/shikigarasu:hakuso   # audit / code review
```

Or via user agent: "use the seiran agent to frame this decision." Soen is available through its user agent only.

**Skip shikigarasu entirely**

Say "just do it" / "直接做" / "skip shikigarasu" to bypass axis routing for the current task.

---

## Design notes

- **Shared contract**: REQUIRED SUB-SKILL `shikigarasu-common` (shared portable contract; Claude runtime path `~/.claude/skills/shikigarasu-common/`) supplies the queue, independent-review, convergence, and evidence contract. This plugin owns only Claude-native coordination: Agent / SendMessage / Task* tooling, model routing, commands, and dispatch rules.
- **Thin framing**: Empirical testing (n=32, 2026-04-24) showed thick mythology / archetype priming had no measurable effect on Opus 4.7 or GPT-5.4 output quality on execution or strategic tasks. Axes use minimal framing — tool whitelist + output structure + handoff protocol.
- **Memory split**: Identity (Stance + Cautions) loads every invocation. Observations are a separate file, Grep'd only when relevant. This prevents unbounded context growth as observation logs accumulate.
- **Kishi as coordinator**: Kishi dispatches workers via the Agent tool. It cannot edit files, run commands, or browse the web — it only reads context and routes. This keeps the coordination layer free of side effects.
- **Batch handoff**: Kishi sequences worker handoffs automatically inside the requested local outcome. It interrupts only for irreversible external action, new authority, material scope expansion, or an outcome-changing fork.
- **Queue and review gates**: Kishi refills available worker slots from its ready queue and requires two fresh-context independent review passes before closing each ticket. Producer evidence cannot close its own ticket.
- **Persistence boundary**: Kishi owns convergence for the current turn only. Cross-turn continuation happens only when a `/goal` is confirmed active in the session or the user explicitly requests persistent continuation; never infer an equivalent mechanism or create persistence on Kishi's own initiative. Without that confirmation, finish the turn and stop.
- **Plugin lifecycle**: The enabled plugin supplies namespaced agents, commands, and rules. Optional copied personal agents and rules remain after the plugin is disabled.

---

## Layer model

This plugin implements **Layer 4** of the four-season-crow harness (sync, Claude-side). Layer 5 (async, OpenAI-side, Telegram bot daemons) is a separate stack with its own naming convention. Cross-vendor consultation maps Layer 4 axis to Layer 5 daemon by function.

---

## License

MIT
