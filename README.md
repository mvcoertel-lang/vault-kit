# vault-kit

**A file-based knowledge vault for Claude Code — on Windows, macOS and Linux, installed with one command.**

Turns the folder Claude Code opens into a structured, rule-governed knowledge base: numbered project
folders, a memory layer with a format and confidentiality rule, a local knowledge graph of everything the
vault knows, permission rules that stop the constant clicking, and a self-healing Graphify integration.

> **Local-first by design.** No cloud, no vector database, no hosted index. Everything is a readable
> file next to your vault, and it works offline.

**Step-by-step guide with before/after:** open [`docs/index.html`](docs/index.html) in a browser
(also shows an [example knowledge graph](docs/demo/graph.html)).

[Why](#why-it-exists) · [Requirements](#requirements) · [Install](#install) · [Architecture](#architecture) ·
[Knowledge graph](#knowledge-graph--two-levels) · [Memory](#memory-layer) · [Permissions](#permissions) ·
[Automation](#automation--self-healing) · [Updating](#updating) · [Daily use](#daily-use) ·
[Troubleshooting](#troubleshooting)

## Why it exists

Claude Code loads its context from files: a `CLAUDE.md` chain plus a memory directory, **both derived
from the working directory**. That is powerful and easy to get wrong: open a different folder once and
you land in an empty memory; let the root `CLAUDE.md` grow and every turn gets more expensive; leave
permissions at their defaults and you approve every `ls`.

vault-kit turns that mechanism into a system:

- **Knowledge accumulates instead of evaporating in chat.** Results go to files, facts go to memory, and both have rules.
- **One memory for every session.** `autoMemoryDirectory` pins memory to the vault, whichever project folder a session starts in.
- **You can see what the vault knows.** The index graph shows memory, skills, projects and instructions with their connections, a one-line explanation per node, and growth over time.
- **Less clicking, same guard rails.** Read-only commands and edits inside the vault run without asking; deleting, `curl` and `git push` still ask.
- **It survives updates.** Tool upgrades that would overwrite local customizations are detected and repaired.

## Requirements

| | Windows | macOS / Linux |
|---|---|---|
| **Claude Code** | Claude Desktop app (Code tab) or the CLI (`irm https://claude.ai/install.ps1 \| iex`) | CLI or desktop app |
| **Git** | [Git for Windows](https://git-scm.com/download/win) (Claude Code uses its Git Bash) | usually present |
| **Python 3.9+** | `winget install Python.Python.3.13` (tick *py launcher*) | macOS: `xcode-select --install` |
| **uv** (optional) | `winget install astral-sh.uv` | `brew install uv` |

`uv` installs [Graphify](https://github.com/safishamsi/graphify) (code graphs) and
[MarkItDown](https://github.com/microsoft/markitdown) (PDF/Office → Markdown). Without it, both are skipped.

## Install

**Windows (PowerShell):**

```powershell
git clone https://github.com/moaccenturestrategy/vault-kit.git $HOME\vault-kit
cd $HOME\vault-kit
powershell -ExecutionPolicy Bypass -File .\install.ps1          # vault: C:\Users\<you>\Claude
#   -Vault D:\MyVault   custom location
#   -Live               show running sessions in the graph (scheduled task, every minute)
#   -NoGraphify         skip Graphify and MarkItDown
```

Then open **Claude Desktop → Code → choose folder `C:\Users\<you>\Claude`**, or a new PowerShell
window → `claude`.

**macOS / Linux:**

```bash
git clone https://github.com/moaccenturestrategy/vault-kit.git ~/vault-kit
cd ~/vault-kit && ./install.sh          # vault: ~/Claude   (options: <path>, --live, --no-graphify)
```

Then a new terminal → `claude` (starts inside the vault).

Both entry points only locate Python and hand over to **`install.py`**, so all platforms run the same,
tested code. It is idempotent and does the deterministic work:

1. creates the vault skeleton (`00_Method`, `00_Sources`, `.claude/{skills,agents,commands}`) and the memory directory;
2. copies the tools to `~/.claude/tools/` and skills, agents and commands to `<vault>/.claude/`, substituting
   `__VAULT__`, `__MEMDIR__`, `__TOOLS__`, `__PY__`;
3. writes `<vault>/CLAUDE.md` **only if none exists**;
4. **merges** into `~/.claude/settings.json`: `autoMemoryDirectory`, permission rules, SessionEnd hooks. Only
   missing keys and list entries are added; a backup `settings.json.vor-vault-kit` is made first;
5. adds a two-line vault pointer to `~/.claude/CLAUDE.md` and the `claude` / `graphify` launchers to your
   PowerShell profile or `~/.zshrc` (between markers, replaced on re-run);
6. installs Graphify and MarkItDown via `uv` and applies the vault house rules to the Graphify skill;
7. optionally registers the live view (`launchd` on macOS, Task Scheduler on Windows);
8. builds the index graph.

Skills you changed yourself are never overwritten: the installer keeps checksums in
`<vault>/.claude/.vault-kit.json`, leaves your version in place and puts the new one next to it as
`<file>.kit-neu` (`--force-kit` / `-ForceKit` overwrites with a `.bak`).

Finally, paste the prompt from [`SETUP.md`](SETUP.md) into the first session for the judgement-dependent
part: tailoring the deliverable skills to your work and running acceptance checks.

## Architecture

**The `CLAUDE.md` chain** — context by proximity; each level loads only when relevant:

| Level | File | Loaded |
|---|---|---|
| Global | `~/.claude/CLAUDE.md` | always (just a pointer to the vault) |
| Vault | `<vault>/CLAUDE.md` | in every session inside the vault (work rules, routing, memory, graph) |
| Project | `<vault>/<project>/CLAUDE.md` | while working on it: purpose, status in a few lines, rules, pitfalls, decisions, layout |
| Chronicle | `<vault>/<project>/08_Reference/CHRONIK_<topic>.md` | on demand: day-by-day reports stay out of `CLAUDE.md` |

**Where things live:** tools in `~/.claude/tools/`; memory in the directory named by `autoMemoryDirectory`
(default `~/.claude/projects/<vault-slug>/memory/`); skills, agents and commands in `<vault>/.claude/`;
**settings that must apply everywhere** (permissions, hooks) in `~/.claude/settings.json`, because project
settings in `<vault>/.claude/settings.json` only take effect when a session starts exactly in the vault root.

Start Claude Code in the vault or in a project folder below it, one session per topic: memory, `CLAUDE.md`,
skills and agents resolve the same way.

Numbered project folders keep routing decidable: `01_Architecture`, `02_DataModel`, `03_Subject`,
`04_Output`, `05_Data`, `06_Restricted`, `07_Build`, `08_Reference`, `09_Rules`. Create only the ones a
project needs; `vault-init` does this for you, plus a project `CLAUDE.md`, a working-mode command and a
routing line.

## Knowledge graph — two levels

One graph over everything produces noise: a run across mixed folders drowns code in markdown nodes
(measured: 1,585 markdown vs. 350 code nodes). Hence two levels.

**Level 1 · index graph** — `<vault>/_Index/graph.html`, standalone and offline, rebuilt automatically at
the end of every session. It maps the *connective layer* of the vault (memory, skills, agents, projects, the
`CLAUDE.md` chain), not the content:

- **explanations per node and per topic**, written in the background by `index-zusammenfassen.py` via
  `claude -p` when the `claude` CLI is on the PATH (refreshed when the source changes);
- **groups and topics** per department, **hubs**, **isolated nodes** (memory nobody links to);
- **growth**: a daily snapshot (`_Index/verlauf.json`, 90 days) shows what has grown in the last month;
- **live view** (optional, `--live` / `-Live`): `index-live.py` marks the nodes that running sessions are
  touching right now.

Manual rebuild: `python3 ~/.claude/tools/vault-index.py <vault>` (Windows: `py -3 ...`).

**Level 2 · code graph** — `graphify update <code-folder>`, per folder that holds code. Purely local
(tree-sitter AST, no API). Themed viewer: `python3 ~/.claude/tools/graph-viewer.py <folder>`.

- **Entry point for `grep`, not the answer.** Where a `graphify-out/graph.json` exists it supplies the entry
  points (file, function, call chain); the answer comes from reading the file. Keep graph output small
  (1 hop, ≤ 10 neighbours); never load `graph.json` raw.
- Queries: `graphify query "<question>" --budget N` · `graphify path "A" "B"` · `graphify explain "X"` · `graphify god-nodes`

## Memory layer

- **Native auto-memory is on**; the `memory-write` skill is the **format authority** for both manual and automatic memory.
- `MEMORY.md` is the **index** (only the first ~200 lines / 25 KB load per session ⇒ keep it ≤ ~40 lines).
  Each line is a statement with entity, number and the words a later question will use.
- **Format:** front matter `name` / `description` / `metadata.type` / `metadata.date` (event date, required),
  `metadata.superseded_by` when replaced; **one fact = one file**; relate with `[[wikilinks]]`.
- **Evidence before feedback:** a lesson is stored only after a test, diff, read-back, verifier verdict or an
  explicit correction by the user.
- **Delta, not rewrite:** append, edit locally, mark as superseded; never rewrite `MEMORY.md` wholesale.
- **The fact supplements the source, never replaces it:** raw text, numbers and source paths stay.
- **Confidentiality:** no credentials or secrets; nothing verbatim from `06_Restricted`; every memory with a
  number names its source file in the vault. Stricter employer or engagement rules take precedence.
- **Hygiene:** `/memory-review` runs the `librarian` agent (duplicates, orphans, dead index lines, stale
  entries, delta edits only); `/memory-benchmark` measures recall. `memory-hygiene.py` runs at session end
  and reminds you when cleanup is due.

## Permissions

Merged into `~/.claude/settings.json` (so they hold in every project folder):

- `defaultMode: acceptEdits`; the vault is an `additionalDirectories` entry, so edits anywhere in the vault run without asking.
- **allow:** reading tools, `Skill`, `Agent`, `TodoWrite`, `WebSearch`, read-only shell commands (`ls`, `cat`,
  `grep`, `find`, `git status/diff/log`, …), `graphify`, `markitdown` and the kit's own tools.
- **ask:** `curl`, `wget`, `git push`, `rm`.
- **deny:** reading `.env*`, `~/.ssh`, `~/.aws`, Claude's credentials file.

Existing entries are kept; nothing is removed. If your organisation enforces managed settings with
`allowManagedPermissionRulesOnly`, these rules have no effect and Claude keeps asking.

## Automation & self-healing

- **SessionEnd hooks** (global settings) rebuild the index graph and check memory hygiene. They are plain
  `python "<path>" ... --hook` calls that run identically in Git Bash and PowerShell; the guard logic
  (skip for `claude -p`, never fail the session) lives in Python.
- **Graphify self-healing:** a Graphify update overwrites its `SKILL.md` and would strip the vault house
  rules. The `graphify` launcher (zsh and PowerShell) notices the missing marker after any call and
  re-applies them; after `graphify update` it rebuilds the themed viewer.
- **Re-running the installer** updates tools, unchanged skills and the launcher block, and leaves your
  `CLAUDE.md`, your own skills and your other settings alone. Kit 1.x hooks in `<vault>/.claude/settings.json`
  are moved to the global settings so they do not run twice.

## Updating

```bash
cd vault-kit && git pull && ./install.sh          # Windows: git pull; .\install.ps1
uv tool upgrade graphifyy markitdown               # tools themselves; house rules are restored automatically
```

## Daily use

- **Open the vault:** Claude Desktop → Code → vault folder, or `claude` in a new terminal (`claude --here` for the current folder).
- `/clear` on every topic change; whatever should persist is already in a file. Start a new session after a
  break of more than an hour (the prompt cache has expired).
- **Skills:** `dashboard`, `analysis`, `standalone-html`, `automation` (deliverables); `markitdown` (sources);
  `vault-init`, `memory-write`, `context-audit` (system).
- **Agents:** `scout` (broad read-only search), `verifier` (check one claim), `librarian` (memory and source
  hygiene), `sichtpruefer` (looks at screenshots and renderings so images stay out of the main context).
- **Commands:** `/method`, `/sources`, `/memory-review`, `/memory-benchmark`, plus one per project from `vault-init`.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Windows: `install.ps1` "cannot be loaded" | start it with `powershell -ExecutionPolicy Bypass -File .\install.ps1` |
| Windows: `claude` starts outside the vault | the profile is not loaded (ExecutionPolicy `Restricted`/`AllSigned`); use the desktop app or `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` if allowed |
| Windows: "Python 3.9 oder neuer fehlt" although installed | the Microsoft Store placeholder is first on PATH; install from python.org with the *py launcher* |
| Memory seems empty | check `autoMemoryDirectory` in `~/.claude/settings.json` points to the vault's memory |
| Claude still asks for every command | a managed policy may enforce `allowManagedPermissionRulesOnly`; nothing the kit can change |
| Graphify house rules gone after an upgrade | run any `graphify` command (the launcher repairs it) or `python3 ~/.claude/tools/graphify-reapply-houserules.py` |
| `graphify` / `markitdown` not found | `uv tool update-shell`, then a new terminal |
| Index graph looks stale | `python3 ~/.claude/tools/vault-index.py <vault>`; log in `~/.claude/tools/last-index.log` |
| No explanations in the graph | they need the `claude` CLI on the PATH; log in `~/.claude/tools/last-zusammenfassen.log` |

## What's not included

No client or project data and none of the originating machine's memory. vault-kit is the empty,
rule-governed structure; content appears as you work. The example graph in `docs/demo/` is built from a
fictitious vault.

## Layout

```
install.ps1 / install.sh   entry points: find Python, hand over to install.py
install.py                 the installer (all platforms, idempotent)
SETUP.md                   prompt for the judgement-dependent finishing steps
docs/                      index.html (installation guide, before/after), demo/graph.html
tools/                     vault-index.py, graph.template.html, index-zusammenfassen.py, index-live.py,
                           memory-hygiene.py, graph-viewer.py (+template), graphify-* (house rules)
templates/                 vault-CLAUDE.md, settings.json (merged globally), global-CLAUDE-pointer.md,
                           zshrc-functions.sh, powershell-profile.ps1
skills/                    vault-init, memory-write, context-audit, markitdown,
                           dashboard, analysis, standalone-html, automation
agents/                    scout, verifier, librarian, sichtpruefer
commands/                  method, sources, memory-review, memory-benchmark
```

## Teams

The repository is public and contains no client data. For team-specific skills, fork it into a private
repository. **Roadmap — team memory:** a shared, synchronised memory layer across several users (not included yet).

## Credits

Built around [Claude Code](https://claude.com/claude-code), [Graphify](https://github.com/safishamsi/graphify)
(`graphifyy` on PyPI) and [MarkItDown](https://github.com/microsoft/markitdown). The vault structure, memory
governance, hygiene tooling and viewers are this kit's own.
