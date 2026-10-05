---
name: markitdown
description: Dokumente (PDF, DOCX, PPTX, XLSX, HTML, CSV, EPUB, Bilder) in Markdown wandeln, mit Microsofts MarkItDown und, für Papers, pymupdf mit Seitenankern. Nutzen bei "PDF lesen", "in Markdown wandeln", "markitdown", "Paper auswerten", "Volltext holen", "DOI herunterladen". Liefert zitierfähige Auszüge mit Seitenzahl.
argument-hint: <datei-oder-doi> [-o ziel.md]
allowed-tools: Bash(*), Read, Write, Glob
---

# MarkItDown im Vault

**Installation:** `uv tool install 'markitdown[pdf,docx,pptx,xlsx]'` (macht der Installer mit, wenn `uv` vorhanden ist). pymupdf kommt je Aufruf über `uv run --with pymupdf`, ohne eigene Installation.

Warum überhaupt: Ein PDF, das Claude als Bild oder Rohdatei liest, kostet ein Vielfaches an Kontext und lässt Zahlen verrutschen. Als Markdown neben der Rohdatei abgelegt, ist die Quelle durchsuchbar, zitierbar und bei jedem späteren Zugriff billig.

## Welcher Motor wofür
| Eingabe | Motor | Grund |
|---|---|---|
| Wissenschaftliche Papers, zweispaltig | `scripts/pdf2md.py` (pymupdf, Seitenanker) | markitdown/pdfminer verklebt dort gemessen 13 bis 18 % der Wörter und baut Phantomtabellen; pymupdf 0,0 % |
| Einspaltige PDFs, Berichte, Office-Exporte | beide sauber; `pdf2md.py --engine auto` wählt selbst | |
| DOCX, PPTX, XLSX, HTML, EPUB, CSV | `markitdown <datei> -o <ziel.md>` | Struktur, Tabellen, Notizen aus Folien |
| Bilder mit Text | `markitdown` (EXIF, OCR nur mit Zusatzpaket) | |

## Aufrufe
```bash
# Paper mit Seitenankern <!-- p.N -->  (Standardweg für Zitate)
uv run -q --with pymupdf python __VAULT__/.claude/skills/markitdown/scripts/pdf2md.py paper.pdf -o extracts/paper.md

# DOI -> OA-PDF -> Markdown (OpenAlex, Europe PMC; nichts hinter Paywalls)
__PY__ __VAULT__/.claude/skills/markitdown/scripts/fetch_paper.py 10.1037/a0037559 --raw raw/ --md extracts/ --name rowland2014
# Exit 2 = kein OA-PDF; die Kandidaten-URLs stehen auf stderr für den Browserweg

# Office und Web
markitdown bericht.docx -o bericht.md
markitdown folien.pptx -o folien.md
markitdown seite.html -o seite.md
```

## Regeln
- **Rohdatei behalten:** PDF nach `<projekt>/raw/` oder `00_Sources/<thema>/raw/`, Markdown daneben nach `extracts/`. Nie nur den Auszug aufheben (Vault-Regel: Kürzen darf nichts vernichten).
- **Zitate tragen Seite und Motor.** Der Kopf jeder Ausgabe nennt Motor und Wortsalat-Anteil; ein Zitat aus einer Datei mit Wortsalat > 2 % gilt als ungeprüft.
- **Formelzeichen prüfen:** `=`, `−`, hoch- und tiefgestellte Zeichen fallen bei beiden Motoren teils weg. Zahlen im Zitat gegen die Rohseite lesen (`Read` kann PDF-Seiten anzeigen).
- **Kein Volltext aus `06_Restricted` in Memory.**
- Registerzeile in `00_Sources/SOURCE_REGISTER.md` für jede wiederverwendbare Quelle.

## Grenzen
- Gescannte PDFs ohne Textebene liefern leere Seiten; dann `markitdown` mit OCR-Zusatz.
- Tabellen aus Papers kommen bei pymupdf als Fließtext; bei Bedarf `page.find_tables()` (pymupdf) nachziehen.
- Landingpages hinter Cloudflare blocken Skripte; dann das PDF im Browser holen und lokal wandeln.
