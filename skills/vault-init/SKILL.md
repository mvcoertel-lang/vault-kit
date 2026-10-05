---
name: vault-init
description: Ein neues Projekt im Vault anlegen (scaffold new project). Nutzen, wenn neue Arbeit ein Deliverable erzeugt, die Session überdauert oder aufhebenswerte Dateien produziert und kein bestehendes Projekt passt. Erzeugt Projektordner, die zutreffenden nummerierten Unterordner, eine Projekt-CLAUDE.md und ein passendes Command. Trigger: "neues Projekt", "Projekt anlegen", "vault-init", "scaffold", "neuen Kunden anlegen".
---

# vault-init

Legt ein neues Projekt im Vault an, ohne leeres Gerüst.

## Hard rules
- **Nie in die Vault-Wurzel schreiben.** Alles gehört in `<vault>/<projekt>/`.
- **Nur Ordner anlegen, die etwas halten werden.** Leeres Gerüst ist Rauschen. Ein Research-Projekt braucht meist 03/05/08, ein Build-Projekt 01/07/09. Den Rest weglassen.
- **Nichts überschreiben.** Existiert der Projektordner schon, anhalten und fragen.

## Procedure
1. Projektnamen und -typ erfragen (research | build | gemischt), falls nicht genannt.
2. Ordner `__VAULT__/<projekt>/` anlegen plus die zutreffenden aus dieser Karte:
   | Nr | Ordner | Zweck |
   |---|---|---|
   | 01 | Architecture | Struktur, Entscheidungen, Begründung |
   | 02 | DataModel | Felder, Definitionen, Quelllogik |
   | 03 | Subject | die Sache selbst: Kunde, Asset, Frage |
   | 04 | Output | Deliverables |
   | 05 | Data | projektspezifische Inputs |
   | 06 | Restricted | vertraulich erhaltenes Material (Herkunft, kein Gefühl) |
   | 07 | Build | Code, Skripte |
   | 08 | Reference | Quellen, Zitate, PDFs |
   | 09 | Rules | Vorlagen und Formatregeln für dieses Projekt |
3. `__VAULT__/<projekt>/CLAUDE.md` schreiben, kurz halten: **Zweck**, **Stand** in wenigen Zeilen, Regeln, Fallen, Entscheidungen, Ablage ("Wo was liegt"). Tagesberichte gehören nicht hinein, sondern nach `08_Reference/CHRONIK_<Thema>.md`; die `CLAUDE.md` verweist darauf.
4. `__VAULT__/.claude/commands/<projekt>.md` als Arbeitsmodus-Command anlegen (siehe /method als Muster).
5. Die Routing-Zeile in `__VAULT__/CLAUDE.md` ergänzen (eine Zeile).

## Pitfalls
- 06_Restricted meint **Herkunft** ("vertraulich erhalten"), nicht ein Gefühl. Sonst landet alles darin und der Ordner wird nutzlos.
- Einen Ordner, in dem gearbeitet wird, nie unter `deny` stellen — Handhabungsregel gehört in die Projekt-CLAUDE.md.
