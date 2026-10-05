---
name: memory-write
description: Einen Fakt als eine Memory-Datei plus eine Indexzeile schreiben. Nutzen, wenn etwas Nicht-Offensichtliches festgehalten werden soll, das über diese Session hinaus gilt und nirgends sonst steht. Trigger: "merk dir", "remember", "als Memory speichern", "festhalten", "note to self".
---

# memory-write

Schreibt genau einen Fakt in genau eine Datei im Memory-Verzeichnis des Vaults und ergänzt eine Indexzeile in `MEMORY.md`.

Memory-Verzeichnis (aus dem Vault-Pfad abgeleitet): `__MEMDIR__/`.

**Diese Datei ist die Format-Autorität** — sie gilt für manuell geschriebene Memory UND für Claude Codes **native Auto-Memory** (standardmäßig an; Claude schreibt selbst Dateien nach eigenem Ermessen). Vor dem Anlegen prüfen, ob — auch nativ — schon eine Datei den Fakt abdeckt (Dubletten vermeiden).

## Hard rules
1. **Ein Fakt, eine Datei.** Keine Sammeldateien. Was in zwei Kontexten gebraucht wird, wird zwei Dateien mit Querverweis `[[name]]`.
2. **Die Indexzeile ist Routing, keine Zusammenfassung.** Sie entscheidet allein, ob die Datei geladen wird — ein Haken, der die Abfrage entscheidbar macht, keine Nacherzählung.
3. **Grund mitschreiben, nicht nur die Regel.** Eine Regel ohne Grund wird an der ersten Ausnahme gebrochen.
4. **Nur absolute Daten.** "Nächste Woche" ist in einem Monat falsch.
5. **Nichts speichern, was ableitbar ist** aus den Vault-Dateien. Memory ist für das, was nirgends geschrieben steht.
6. **Memory altert.** Nennt ein Eintrag Datei/Tool/Preis/Pfad, vor Gebrauch prüfen, ob es noch existiert.
7. **Datum und Ablösung.** Jede Datei trägt `metadata.date` (Ereignisdatum). Wird ein Fakt abgelöst, bekommt die alte Datei `superseded_by` und ihre Indexzeile fällt weg; nie stumm überschreiben. Zwei widersprechende Einträge ohne Ablösung sind schlimmer als keiner.
8. **Vertraulichkeit.** Nie ins Memory: Zugangsdaten/Secrets und wörtliche Passagen aus `06_Restricted`-Dokumenten. Jede Memory mit einer Zahl oder einem Kundenfakt nennt die Quelldatei im Vault, damit sie prüfbar bleibt. Gilt auch für native Auto-Memory. Strengere Regeln deines Arbeitgebers oder Mandats gehen vor: dann Kundenfakten nur als Zeiger auf Projekt und Datei.
9. **`feedback` nur mit Prüfsignal.** Eine Lehre wird erst gespeichert, wenn sie belegt ist: ein Test oder Skript ist von rot auf grün, ein Diff oder Read-back bestätigt den Zustand, der `verifier` hat geurteilt, oder der Nutzer hat ausdrücklich korrigiert. Ohne Signal nicht speichern. Grund: gespeicherte Selbstreflexion ohne Prüfsignal fällt messbar unter die Baseline (Reflexion, Tab. 3: 0,52 ohne Tests gegen 0,60 Basis gegen 0,68 mit Tests).
10. **Der Fakt ergänzt die Quelle, er ersetzt sie nie.** Rohtext, Zahl und Quellpfad bleiben; die Memory-Datei ist die Verdichtung obendrauf, nicht der Ersatz (LongMemEval, Tab. 3: Fakt plus Rohtext 0,784 gegen Summary allein 0,252).
11. **Widerspruch vor dem Schreiben klären.** Nennt der Fakt eine Entität oder Zahl, die schon im Memory steht, wird nicht still überschrieben: Treffer nennen, die alte Datei als `superseded_by` verlinken oder abbrechen und fragen. Grund: Widersprüche beim späteren Lesen aufzulösen gelingt keinem getesteten System zuverlässig.

## Dateiformat
```markdown
---
name: <kurzer-kebab-slug>
description: <ein Aussagesatz mit Entität, Zahl und den Worten, die eine spätere Frage benutzen wird>
metadata:
  type: user | feedback | project | reference
  date: JJJJ-MM-TT            # Ereignisdatum des Fakts, nicht das Schreibdatum (Pflicht)
  superseded_by: <name>       # nur bei Ablösung: Slug der neueren Datei
---

<der Fakt. Bei feedback/project danach **Warum:** und **Wie anwenden:**. Verwandtes mit [[name]] verlinken.>
```

## Procedure
1. Prüfen, ob eine Datei den Fakt schon abdeckt — dann die aktualisieren statt duplizieren. Dazu Entität **und** Zahl im Memory-Verzeichnis greppen, nicht nur den Dateinamen; bei Widerspruch Regel 11.
2. Datei schreiben, `[[verweise]]` auf Verwandtes setzen (auch auf noch nicht existierende Slugs — markiert Nachholenswertes).
3. Eine Zeile in `MEMORY.md` ergänzen: `- [Titel](datei.md) — Haken`. Index unter ~40 Zeilen halten.
4. Nach neuen Memory-Dateien den Index-Graph auffrischen: `__PY__ __TOOLS__/vault-index.py __VAULT__`.

## Pitfalls
- Der Index veraltet mit jeder neuen Datei — daher Schritt 4 nicht vergessen.
- Eine isolierte Memory-Datei (kein `[[verweis]]` von/zu ihr) taucht im Graph gestrichelt auf: entweder überflüssig oder falsch benannt.
