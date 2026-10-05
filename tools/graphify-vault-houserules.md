<!-- ===================== VAULT-HAUSREGELN ===================== -->
<!-- Lokale Anpassung für den Vault unter __VAULT__. Gilt VOR allem anderen in
     diesem Skill. Diese Datei ist die KANONISCHE Quelle des Blocks
     (~/.claude/tools/graphify-vault-houserules.md) und wird nach jedem
     `graphify install` automatisch neu injiziert (zsh-graphify-Wrapper ruft
     ~/.claude/tools/graphify-reapply-houserules.py). Dauerhafte Fassung der
     Regeln zusätzlich in __VAULT__/CLAUDE.md. -->

## Vault-Hausregeln (gelten vor allem anderen)

Dieser Rechner betreibt einen Vault mit einer **Zwei-Ebenen**-Graphenarchitektur. `/graphify` ist ausschließlich **Ebene 2** (Container-Graphen über Code).

1. **Nie an der Vault-Wurzel (`__VAULT__`) und nie über ein ganzes Projekt laufen.** Ein Lauf über gemischte Ordner erzeugt eine Markdown-Flut, die den Code übertönt (gemessen: 1.585 Markdown- gegen 350 Code-Knoten, unbrauchbar). Wird `/graphify` ohne Pfad oder mit einem Projekt-/Wurzelpfad aufgerufen, **nicht** auf `.` defaulten: anhalten und nach dem konkreten **Code-Ordner** fragen.
2. **Ebene 1 (Index-Graph über den ganzen Vault) gehört NICHT zu `/graphify`.** Der wird mit `__PY__ __TOOLS__/vault-index.py __VAULT__` gebaut. `/graphify` niemals dafür verwenden.
3. **Default ist der lokale Weg:** für Code-Ordner `graphify update <ordner>` (rein tree-sitter-AST, keine API, nichts verlässt den Rechner). Die volle Pipeline mit semantischem Doc-Pass nur, wenn ausdrücklich verlangt.
4. Betrachter/Abfragen bleiben lokal: `graphify query/path/explain/god-nodes` gegen das jeweilige `graphify-out/graph.json` des Code-Ordners.
5. **Abfrage-Tipps (aus dem Benchmark 2026-08-19, 9 Agenten):**
   - **Symbol → Datei immer auflösen**, bevor du einen Knoten/Hub zitierst: `god-nodes` gibt nur den nackten Funktionsnamen (das führte zu Fehl-Verortung, z. B. `query_stock` fälschlich in `inventory.py`). Die Datei über `explain`/`query` (Feld `src=…`) bestätigen.
   - **Bei bekannter Zeilennummer nur den Ausschnitt lesen**, nie die ganze Datei — `query`/`explain` liefern `at=datei:Lzeile`.
   - **Konnektivitäts-, Hub- und Impact-Fragen immer über den Graphen** (`god-nodes`, `query`, `path`) beantworten, nie aus „den offensichtlich relevanten Dateien" schätzen — genau dort irrt bloßes Lesen (2 von 3 Nur-Lesen-Agenten lagen bei der Hub-Frage falsch).

<!-- =================== ENDE VAULT-HAUSREGELN =================== -->
