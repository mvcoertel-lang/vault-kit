# Vault

**Zweck:** Datei-basierter Speicher- und Kontext-Layer für Claude Code. Alles mit Bestand lebt hier in Dateien, nicht im Chat.

## Arbeitsregeln
- Ergebnisse werden in Dateien geschrieben, nicht im Chat gelassen.
- Zahlen nie aus dem Gedächtnis nennen: eine Datei in `08_Reference` zitieren.
- Nichts verlässt diesen Rechner ohne ausdrückliche Bestätigung.
- `/clear` bei jedem Themenwechsel. Was bleiben soll, steht in einer Datei. Jeder Aufruf liest den ganzen Verlauf: lange Sitzungen werden teuer und ungenau. Ab etwa 250k Kontext `/clear` oder `/compact` mit Fokus; nach über einer Stunde Pause eine neue Sitzung (der Cache ist dann abgelaufen, der nächste Aufruf schreibt den ganzen Verlauf neu). Auto-Compact greift bei 300k (`CLAUDE_CODE_AUTO_COMPACT_WINDOW` in `~/.claude/settings.json`).
- Claude Code im Vault (`__VAULT__`) oder in einem Projektordner darunter starten, eine Sitzung je Thema. Die Memory liegt in jedem Startordner fest unter `__MEMDIR__` (`autoMemoryDirectory` in `~/.claude/settings.json`); `CLAUDE.md`, Agenten und Skills kommen aus den Elternordnern. Was überall gelten soll (Freigaben, Hooks), steht in `~/.claude/settings.json`, nicht in `__VAULT__/.claude/settings.json`: Projekt-Settings wirken nur beim Start genau im Vault-Ordner.
- Bilder, Screenshots und Folien-Renderings prüft der Agent `sichtpruefer`, nie der Hauptkontext: jedes Bild bleibt im Verlauf und wird bei jedem Aufruf erneut gesendet. Große Dateien nur mit Zeilenbereich lesen oder über `scout`.
- Widerspricht eine Angabe im Gespräch einer Memory-Datei oder einer Quelle in `08_Reference`, die Datei zitieren und nachfragen, nie still entscheiden.
- Kürzen darf nichts vernichten: Rohtext, Zahlen und Quellpfade bleiben, Verdichtung kommt obendrauf und verweist auf den Volltext.
- Projekt-`CLAUDE.md` enthält nur Zweck, Stand in wenigen Zeilen, Regeln, Fallen, Entscheidungen und Ablage. Tagesberichte gehen nach `08_Reference/CHRONIK_<Thema>.md`, die `CLAUDE.md` verweist darauf.

## Projekte (Routing, keine Doku: eine Zeile je Eintrag)
| Ordner | Was | Status |
|---|---|---|
| 00_Method | Standards, Vorlagen, Formate | living |
| 00_Sources | wiederverwendbare Inputs + Register | living |

## Operating protocol
**Route before writing.** Jede Datei gehört zu einem Projekt und einem nummerierten Ordner. Beides vor dem Anlegen bestimmen. Nie in die Vault-Wurzel schreiben. Ist der Zielordner echt unklar, eine Frage stellen, keine Diskussion.

**Propose structure for new work.** Wenn eine Anfrage ein Deliverable erzeugt, diese Session überdauert oder aufhebenswerte Dateien produziert und kein Projekt passt: `vault-init` anbieten, den Projektnamen nennen, dann so oder so weiterarbeiten. Einmal fragen; bei Ablehnung für diese Session fallenlassen. Nicht bei Einmalfragen, Lookups oder Arbeit in einem bestehenden Projekt.

**Capture at the end.** Wenn Arbeit abschließt, in einer Zeile anbieten, Dauerhaftes festzuhalten: eine Memory-Datei für einen nicht-offensichtlichen Fakt, einen Area-`CLAUDE.md`-Eintrag für eine gelernte Konvention oder Falle, eine `00_Sources`-Registerzeile für einen wiederverwendbaren Input. Nichts sagen, wenn nichts qualifiziert.

Nie auf einem dieser Punkte blockieren. Vorschlagen, Default nennen, weiterarbeiten.

## Skills und Agenten
- **Deliverables:** `dashboard` (KPI/Charts), `analysis` (belegte Auswertung, nutzt scout/verifier), `standalone-html` (Offline-Seiten ohne CDN), `automation` (lokale, idempotente Skripte).
- **Quellen:** `markitdown` (PDF/Office/HTML → Markdown, damit Claude Quellen als Text liest statt als Bild).
- **System:** `vault-init` (neues Projekt), `memory-write` (ein Fakt → eine Datei), `context-audit` (persistenten Kontext messen).
- **Agenten:** `scout` (breite, nur lesende Suche; gibt Fundstellen zurück), `verifier` (eine Behauptung gegen die Quelle prüfen), `librarian` (Register und Memory-Hygiene), `sichtpruefer` (Bilder ansehen, Befund als Text).

## Memory
Speicher: `__MEMDIR__`; `MEMORY.md` ist der Index (nur die ersten ~200 Zeilen/25 KB werden je Session geladen: **≤ ~40 Zeilen halten**). Native Auto-Memory ist an: Claude schreibt selbst Memory-Dateien, es gelten dieselben Regeln wie für den `memory-write`-Skill (die Format-Autorität).
- **Format:** Frontmatter `name`/`description`/`metadata.type` ∈ `user|feedback|project|reference`, `metadata.date` = Ereignisdatum (Pflicht, der SessionEnd-Hook meldet Fehlendes), `metadata.superseded_by` bei Ablösung; **ein Fakt = eine Datei**; bei feedback/project `**Warum:**`/`**Wie anwenden:**`; Verwandtes mit `[[wikilinks]]`.
- **Index-Disziplin:** jede Memory-Datei bekommt genau eine `MEMORY.md`-Zeile: ein Aussagesatz mit Entität, Zahl und den Worten einer späteren Frage, nicht nur ein Titel.
- **Prüfsignal:** `feedback`-Memories erst nach Test, Diff, Read-back, Verifier-Urteil oder ausdrücklicher Korrektur durch den Nutzer, nie auf Verdacht.
- **Delta statt Rewrite:** anfügen, lokal ändern, als abgelöst markieren; `MEMORY.md` und Memory-Dateien nie als Ganzes neu schreiben.
- **Vertraulichkeit:** Zugangsdaten und Secrets nie ins Memory. Inhalte aus `06_Restricted` nie wörtlich. Jede Memory mit einer Zahl nennt die Quelldatei im Vault, damit die Zahl prüfbar bleibt.
- **Hygiene:** `/memory-review` (librarian räumt auf), `/memory-benchmark` (Recall prüfen). Der SessionEnd-Hook erinnert, wenn Hygiene fällig ist.

## Wissensgraph: zwei Ebenen
- **Ebene 1, Index-Graph:** einmal für den ganzen Vault unter `_Index/`. Baut sich nach jeder Sitzung selbst neu (SessionEnd-Hook); von Hand: `__PY__ __TOOLS__/vault-index.py __VAULT__`. Bildet die Verbindungsschicht ab (Memory, `CLAUDE.md`-Kette, Projekte, Skills, Agenten), nicht den Inhalt. Betrachter: `_Index/graph.html` (standalone, offline) mit Erklärung je Knoten, Gruppen, Wachstum über die Zeit und, wenn eingerichtet, den gerade laufenden Sitzungen.
- **Ebene 2, Container-Graph:** je Ordner mit Code, nie über ein ganzes Projekt, nie an der Wurzel: `graphify update <ordner>` (rein lokal, tree-sitter-AST, keine API-Kosten). Eigener Betrachter: `__PY__ __TOOLS__/graph-viewer.py <ordner>` → `graph.viewer.html`.
- **Einstieg für `grep`, nicht Antwortquelle:** Wo ein `graphify-out/graph.json` existiert, liefert er bei Struktur- und Zusammenhangsfragen die Einstiegspunkte (Datei, Funktion, Aufrufkette); die Antwort kommt aus der gelesenen Datei. Graph-Ausgabe klein halten (1 Hop, ≤ 10 Nachbarn), nie `graph.json` roh in den Kontext.
- **Abfragen:** `graphify query "<Frage>" --budget N` · `graphify path "A" "B"` · `graphify explain "X"` · `graphify god-nodes`
- **Grenzen (gemessen):** HTML wird nicht geparst: Inline-JS vorher in eine `.js`-Datei ziehen. Konstanten nur flach erfasst, dafür weiter greppen; Funktionen und Aufrufketten sind zuverlässig.
