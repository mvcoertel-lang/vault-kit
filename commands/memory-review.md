---
description: Memory-Hygiene — der librarian-Agent räumt das Memory-Verzeichnis auf
argument-hint: [fokus]
---

Beauftrage den `librarian`-Agent (Read/Write/Grep/Glob) mit einer Hygiene-Runde über das Vault-Memory.

Memory-Verzeichnis: `__MEMDIR__/` (+ `MEMORY.md`).
Als Orientierung zuerst `__PY__ __TOOLS__/memory-hygiene.py __MEMDIR__` laufen lassen und die Befunde übergeben.

Auftrag an den librarian:
- **Dubletten** zusammenführen (ein Fakt = eine Datei), Querverweis `[[..]]` setzen.
- **Veraltetes/Widersprüche** melden (Datei/Tool/Preis/Pfad prüfen, ob noch gültig).
- **Verwaiste Dateien** (keine `MEMORY.md`-Zeile / kein `[[wikilink]]`) anbinden.
- **Tote Index-Zeilen** (Datei fehlt) entfernen.
- `MEMORY.md` unter ~40 Zeilen halten; Format gegen den `memory-write`-Skill prüfen.
- **Vertraulichkeit:** nie Zugangsdaten/Secrets oder wörtliche `06_Restricted`-Passagen; Zahlen und Kundenfakten nur mit Quelldatei im Vault. Fehlt die Quelle oder steht ein Secret drin, melden.

Regeln: nichts löschen ohne Bestätigung; Vorschläge klar von durchgeführten Korrekturen trennen. **Nur Delta-Operationen**: `MEMORY.md` und Memory-Dateien nie als Ganzes neu schreiben; beim Zusammenführen gehen keine Zahlen, Quellpfade oder Begründungen verloren.
Danach den Index-Graph neu bauen: `__PY__ __TOOLS__/vault-index.py __VAULT__`.

Fokus (optional): $ARGUMENTS
