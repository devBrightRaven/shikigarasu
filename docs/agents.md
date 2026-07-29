# Shikigarasu User Agents

Six user agents for Claude Code. Drop these into `~/.claude/agents/` to enable all six axes.

## Installation

```bash
cp agents/*.md ~/.claude/agents/
```

Restart Claude Code session to activate.

## Vault configuration (optional)

Soen can write research artifacts to a configured vault. Shuen may read configured optional memory but writes reports only to the coordinator-provided path or OS temp. Kishi coordinates only and does not write vault or memory artifacts.
Configure by creating `~/.claude/vault-local.md`:

```yaml
vault: /path/to/your/vault
agents_vault: /path/to/your/agents-vault
shikigarasu: shikigarasu/             # ski_dir under agents_vault
research: _yorozuya/research/          # relative to vault
```

For Shuen, `shikigarasu:` maps to `ski_dir`; both `agents_vault` and `shikigarasu` must resolve or Shuen skips optional memory. Soen's separate research artifact falls back to OS temp.

## Agents

| File | Name | Role | Model |
|------|------|------|-------|
| `kishi.md` | 鬼子 Kishi | Coordinator — dispatches workers, synthesizes | sonnet |
| `seiran.md` | 青嵐 Seiran | Strategy — bounded tradeoff analysis | opus |
| `shuen.md` | 朱焔 Shuen | Scout — blind spots, assumption stress-test | sonnet |
| `genen.md` | 玄淵 Genen | Execution — build, refactor, fix | sonnet |
| `hakuso.md` | 白霜 Hakuso | Audit — pass/block verdict | opus |
| `soen.md` | 蒼炎 Soen | Scientist — hypothesis-driven experiments | sonnet |

## Usage patterns

**Direct (power-user)**
Invoke an axis through its user agent, or use a slash command when available.

**Orchestrated (recommended for multi-axis tasks)**
In an interactive session, the main session applies Kishi's coordinator protocol using its Agent tool. For detached work, start one `claude --agent kishi -p "..."` parent coordinator; do not start one CLI process per ticket.

**Plugin slash commands**
Install the shikigarasu plugin for the four slash commands: `/shikigarasu:seiran`, `/shikigarasu:shuen`, `/shikigarasu:genen`, and `/shikigarasu:hakuso`. Soen is Agent-only; there is no `/shikigarasu:soen` slash command.
The `agents/` here are the underlying definitions the plugin relies on.
