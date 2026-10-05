# Vault-Kit: Feinschliff-Prompt

Der Installer (`install.ps1` unter Windows, `install.sh` auf dem Mac, beide rufen `install.py`) hat den
deterministischen Teil erledigt: Ordner, Werkzeuge, Skills/Agenten/Commands, `CLAUDE.md`, globale
Einstellungen mit Hooks und Freigaben, Starter, Index-Graph. Dieses Dokument ist der Rest, der **Urteil**
braucht. Alles unterhalb der Linie in eine Claude-Code-Sitzung einfügen, die im Vault geöffnet ist
(Desktop-App: Code, Ordner des Vaults; Terminal: `claude`).

---

Du richtest das per Installer gelegte Vault-System fertig ein. Arbeite die Phasen der Reihe nach ab, behaupte nichts als fertig, was du nicht geprüft hast.

## Phase 1: Audit (nur lesen)
1. Bestätige die Wurzel: In welchem Ordner läuft diese Sitzung? Steht dort eine `CLAUDE.md`? Wie viele Zeilen (Ziel < 100)?
2. Memory: Welchen Pfad nennt `autoMemoryDirectory` in `~/.claude/settings.json`? Wie viele Dateien, wie viele `MEMORY.md`-Zeilen (Ziel ≤ ~40)?
3. Skills, Agenten, Commands: liste, was unter `<vault>/.claude/` liegt. Gibt es Dateien `*.kit-neu` (neue Kit-Fassung neben einer selbst geänderten)? Dann den Unterschied zeigen und fragen.
4. Werkzeuge: Python-Version, `graphify --version`, `markitdown --version`, `claude --version` (fehlt `claude` im PATH, entstehen keine Erklärungen im Graphen).
Berichte in unter 10 Zeilen. Frage nur, was du nicht selbst ermitteln kannst.

## Phase 2: Domain-Skills an DEINE Deliverables anpassen
Das Kit liefert generische Skills (`dashboard`, `analysis`, `standalone-html`, `automation`). Frag den Nutzer nach seinen **drei häufigsten Deliverables** und passe die vorhandenen Skills an bzw. lege je Deliverable einen zu (Format-Standard, harte Regeln mit Grund, bekannte Fallen). Erfinde keinen generischen Satz, leite ihn aus den Antworten ab. Vorlagen (z. B. PowerPoint-Master) gehören nach `00_Method/` oder ins Projekt unter `09_Rules/`.

## Phase 3: Verankern und Abnahme
1. **Index-Graph:** den Neubau-Befehl aus dem Abschnitt „Wissensgraph“ der Vault-`CLAUDE.md` ausführen und die Kontrollzahlen nennen (Knoten, Kanten, je Abteilung, isolierte Knoten). `<vault>/_Index/graph.html` lädt ohne Netz.
2. **Memory-Regeln:** die Vertraulichkeitsregel und die Prüfsignal-Regel aus der Vault-`CLAUDE.md` zurück zitieren. Native Auto-Memory ist an; bestätige, dass sie an dieselben Regeln gebunden ist.
3. **Hooks und Freigaben:** in `~/.claude/settings.json` die beiden SessionEnd-Hooks (Index-Neubau, Hygiene) und die Freigaberegeln zeigen (valides JSON). Prüfe mit einem harmlosen `ls`, dass ohne Rückfrage ausgeführt wird. Fragt Claude trotzdem, kann eine Firmenrichtlinie (`allowManagedPermissionRulesOnly`) greifen; das melden, nicht umgehen.
4. **Hygiene:** `/memory-review` (librarian) einmal trocken laufen lassen; `/memory-benchmark` für den Recall.
5. **Graphify:** falls Code vorhanden, `graphify update <code-ordner>` (rein lokal) und eine echte `graphify query` zeigen.

## Phase 4: Betrieb erklären (unter 12 Zeilen)
Welchen Ordner öffnen (den Vault oder einen Projektordner darin, eine Sitzung je Thema), wann `/clear`, wohin neue Fakten (Memory-Regeln), wann ein neues Projekt (`vault-init`), die Zwei-Ebenen-Graph-Regel und dass `/memory-review` bei Bedarf aufräumt.

**Nicht enthalten (bewusst):** Mandanten-/Projektdaten und Memory-Inhalte des Ursprungsrechners. Dieses Kit ist die leere, geregelte Struktur; Inhalt entsteht beim Arbeiten.
