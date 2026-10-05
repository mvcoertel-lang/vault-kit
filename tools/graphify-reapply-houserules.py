#!/usr/bin/env python3
"""Setzt die Vault-Hausregeln nach einem `graphify install` wieder in die
SKILL.md ein und entfernt doppelte graphify-Registrierungsblöcke in der
globalen CLAUDE.md. Idempotent: mehrfaches Ausführen ändert nichts.

Aufruf: python3 ~/.claude/tools/graphify-reapply-houserules.py
Wird vom zsh-graphify-Wrapper nach `graphify install` automatisch aufgerufen.
"""
import pathlib
import sys

for _s in (sys.stdout, sys.stderr):  # Windows-Konsole: UTF-8 statt cp1252
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

H = pathlib.Path.home()
skill = H / ".claude/skills/graphify/SKILL.md"
block_file = H / ".claude/tools/graphify-vault-houserules.md"
global_md = H / ".claude/CLAUDE.md"
MARKER = "VAULT-HAUSREGELN"
changed = []

# 1) SKILL.md: Block nach der Überschrift '# /graphify' injizieren, wenn er fehlt
if skill.is_file() and block_file.is_file():
    t = skill.read_text(encoding="utf-8")
    if MARKER not in t:
        block = block_file.read_text(encoding="utf-8").rstrip() + "\n"
        out, injected = [], False
        for ln in t.splitlines(keepends=True):
            out.append(ln)
            if not injected and ln.strip() == "# /graphify":
                out.append("\n" + block + "\n")
                injected = True
        if not injected:                       # Fallback: nach dem Frontmatter
            out = [block + "\n"] + t.splitlines(keepends=True)
        skill.write_text("".join(out), encoding="utf-8")
        changed.append("SKILL.md: Hausregel-Block neu injiziert")
    else:
        changed.append("SKILL.md: Hausregeln bereits vorhanden (keine Änderung)")
elif not skill.is_file():
    changed.append("SKILL.md nicht gefunden — graphify installiert?")

# 2) globale CLAUDE.md: doppelte '# graphify'-Blöcke auf einen reduzieren
if global_md.is_file():
    gt = global_md.read_text(encoding="utf-8")
    parts = gt.split("# graphify\n")
    if len(parts) > 2:                          # Preamble + >1 graphify-Block
        gt = (parts[0] + "# graphify\n" + parts[1]).rstrip() + "\n"
        global_md.write_text(gt, encoding="utf-8")
        changed.append(f"globale CLAUDE.md: {len(parts) - 2} doppelte graphify-Blöcke entfernt")

print("\n".join(changed) if changed else "nichts zu tun")
