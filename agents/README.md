# Shikigarasu User Agents

Six user agents for Claude Code. Drop these into `~/.claude/agents/` to enable all six axes.

## Installation

```bash
cp agents/*.md ~/.claude/agents/
```

Restart Claude Code session to activate.

## Vault configuration (optional)

Three agents (Kishi, Shuen, Soen) can write research artifacts and memory files to a vault.
Configure by creating `~/.claude/vault-local.md`:

```yaml
vault: /path/to/your/vault
agents_vault: /path/to/your/agents-vault
research: _yorozuya/research/          # relative to vault
```

If `vault-local.md` is absent, fallback paths are used (`~/.shikigarasu/`).

## Agents

| File | Name | Role | Model |
|------|------|------|-------|
| `kishi.md` | 鬼子 Kishi | Coordinator — dispatches workers, synthesizes | opus |
| `seiran.md` | 青嵐 Seiran | Strategy — bounded tradeoff analysis | opus |
| `shuen.md` | 朱焔 Shuen | Scout — blind spots, assumption stress-test | sonnet |
| `genen.md` | 玄淵 Genen | Execution — build, refactor, fix | sonnet |
| `hakuso.md` | 白霜 Hakuso | Audit — pass/block verdict | sonnet |
| `soen.md` | 蒼炎 Soen | Scientist — hypothesis-driven experiments | sonnet |

## Usage patterns

**Direct (power-user)**
Invoke a single axis via `/shikigarasu:<axis>` slash command (requires plugin).

**Orchestrated (recommended for multi-axis tasks)**
Invoke Kishi: `use the kishi agent to...` — Kishi routes to the right workers and synthesizes.

**Plugin slash commands**
Install the shikigarasu plugin for `/shikigarasu:seiran`, `/shikigarasu:shuen`, etc.
The `agents/` here are the underlying definitions the plugin relies on.
