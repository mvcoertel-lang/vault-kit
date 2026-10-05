# Changelog

## 2.0.0 — 2026-10-05

Windows support, the current knowledge-graph design, global settings and the revised memory rules.

**Platforms**
- Windows with the Claude Desktop app or the CLI: `install.ps1` finds a real Python (py launcher first, rejects the Microsoft Store placeholder), checks Git for Windows and the ExecutionPolicy
- one installer for all platforms: `install.py`; `install.sh` and `install.ps1` only locate Python and hand over
- hooks are plain `python "<path>" ... --hook` calls that run in Git Bash and PowerShell; guard logic moved into Python
- tools write UTF-8 regardless of the console code page and start background work without console windows on Windows
- PowerShell launchers `claude` / `graphify` (profile block between markers, UTF-8 with BOM for Windows PowerShell 5.1)
- Graphify installs with `--platform windows` on Windows

**Settings**
- `autoMemoryDirectory`, permission rules and SessionEnd hooks are merged into `~/.claude/settings.json` (project settings only apply when a session starts exactly in the vault root); existing entries are kept, backup `settings.json.vor-vault-kit`
- permission allowlist for read-only commands and the kit's tools, `acceptEdits` with the vault as additional directory; `ask` on `curl`, `wget`, `git push`, `rm`; `deny` on secrets
- kit 1.x hooks in `<vault>/.claude/settings.json` are migrated so they do not run twice
- `CLAUDE_CODE_AUTO_COMPACT_WINDOW=300000`

**Knowledge graph**
- current viewer design: explanations per node and topic (`index-zusammenfassen.py`, via `claude -p`), groups and topics, hubs, growth over 90 days (`verlauf.json`)
- optional live view of running sessions (`index-live.py`; launchd on macOS, Task Scheduler on Windows, `--live` / `-Live`)
- rule change: the code graph is the entry point for `grep`, not the answer source

**Vault rules and memory**
- vault `CLAUDE.md`: one session per topic, images via `sichtpruefer`, large files via `scout`, quote and ask on contradictions, lossless shortening, project `CLAUDE.md` short with a `CHRONIK` file for daily reports
- memory: `metadata.date` required, `superseded_by`, evidence signal before `feedback`, fact supplements source, resolve contradictions before writing, delta edits instead of rewrites
- confidentiality: no secrets, nothing verbatim from `06_Restricted`, every number names its source file; stricter employer rules take precedence

**Skills and agents**
- new skill `markitdown` (PDF/Office → Markdown, papers with page anchors)
- new agent `sichtpruefer` (image review outside the main context)
- `librarian` gets `Edit` and the delta rule; `vault-init` writes the short project `CLAUDE.md`
- installer keeps skills you changed (checksum manifest, new version as `.kit-neu`, `--force-kit`)

**Docs**
- `docs/index.html`: installation guide for Windows and macOS with before/after
- `docs/demo/graph.html`: example index graph of a fictitious vault

## 1.0.0 — 2026-08-20

First release. Installable, portable setup for a file-based knowledge vault with Claude Code.

**Vault**
- `CLAUDE.md` chain with work rules, project routing table and operating protocol
- numbered project folders via the `vault-init` skill
- deliverable skills: `dashboard`, `analysis`, `standalone-html`, `automation`
- system skills: `vault-init`, `memory-write`, `context-audit`
- agents: `scout`, `verifier`, `librarian`
- commands: `/method`, `/sources`, `/memory-review`, `/memory-benchmark`
- egress guards in `settings.json` (`ask` on curl/wget/git push/WebFetch/rm; `deny` on `.env`/`~/.ssh`)

**Knowledge graph (two levels)**
- level 1: `vault-index.py` builds the vault index graph with a standalone, offline viewer
- level 2: Graphify code graphs per code folder, plus `graph-viewer.py` for a themed viewer that survives `graphify update`
- vault house rules for Graphify (two-level rule, local-only for client material)

**Memory layer**
- native auto-memory bound to the `memory-write` format authority
- hard confidentiality rule (no client / `06_Restricted` content in memory, auto-memory included)
- `memory-hygiene.py` + SessionEnd reminder; `/memory-review` (librarian) and `/memory-benchmark` (recall)

**Automation & portability**
- SessionEnd hooks rebuild the index graph and check memory hygiene
- self-healing `graphify()` wrapper re-applies the vault house rules after any Graphify update
- `install.sh` derives all paths, substitutes `__VAULT__`/`__MEMDIR__`, is idempotent, and never overwrites an existing `CLAUDE.md` / `settings.json`
