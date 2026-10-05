#!/usr/bin/env python3
"""PDF -> Markdown mit Seitenankern, fuer zitierfaehige Auszuege.

Aufruf:
    uv run -q --with pymupdf python pdf2md.py <datei.pdf> [-o out.md] [--engine auto|pymupdf|markitdown]

Motor `auto` (Default): pymupdf mit Seitenankern `<!-- p.N -->`; danach Messung des
Wortsalat-Anteils (Woerter laenger als 18 Zeichen). Liegt pymupdf ueber 2 %, wird
zusaetzlich markitdown probiert und der bessere Text genommen. Der gewaehlte Motor und
die Messwerte stehen im Kopf der Ausgabe.

Gemessen 2026-09-14 (vier PDFs): markitdown 0.1.7 (pdfminer) verklebt bei zweispaltigen
Papers 13 bis 18 % der Woerter und erzeugt Phantomtabellen; pymupdf 0,0 %. Bei
einspaltigen Office-PDFs sind beide sauber. Darum pymupdf zuerst.
"""
from __future__ import annotations
import argparse, re, shutil, subprocess, sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):  # Windows-Konsole: UTF-8 statt cp1252
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError): pass

MARKITDOWN = Path.home() / ".local/bin/markitdown"


def long_word_ratio(text: str) -> float:
    words = re.findall(r"[A-Za-zÄÖÜäöüß]+", text)
    return sum(len(w) > 18 for w in words) / max(1, len(words))


def via_pymupdf(pdf: Path) -> tuple[str, int]:
    import pymupdf  # noqa
    doc = pymupdf.open(str(pdf))
    parts = []
    for i, page in enumerate(doc, start=1):
        txt = page.get_text("text")
        # Silbentrennung am Zeilenende zusammenziehen, Zeilen zu Absaetzen
        txt = re.sub(r"(\w)-\n(\w)", r"\1\2", txt)
        txt = re.sub(r"(?<!\n)\n(?!\n)", " ", txt)
        parts.append(f"\n<!-- p.{i} -->\n{txt.strip()}\n")
    return "".join(parts), len(doc)


def via_markitdown(pdf: Path) -> str:
    if not MARKITDOWN.exists():
        exe = shutil.which("markitdown")
        if not exe:
            raise SystemExit("markitdown nicht gefunden: uv tool install 'markitdown[pdf]'")
    else:
        exe = str(MARKITDOWN)
    out = subprocess.run([exe, str(pdf)], capture_output=True, text=True, encoding="utf-8", errors="replace", check=True)
    return out.stdout


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf", type=Path)
    ap.add_argument("-o", "--out", type=Path)
    ap.add_argument("--engine", choices=("auto", "pymupdf", "markitdown"), default="auto")
    a = ap.parse_args()
    if not a.pdf.exists():
        print(f"fehlt: {a.pdf}", file=sys.stderr)
        return 1
    head = [f"<!-- quelle: {a.pdf} -->"]
    text, engine = "", ""
    if a.engine in ("auto", "pymupdf"):
        try:
            text, pages = via_pymupdf(a.pdf)
            engine = "pymupdf"
            r = long_word_ratio(text)
            head.append(f"<!-- motor: pymupdf, seiten: {pages}, wortsalat: {r:.4f} -->")
            if a.engine == "auto" and (r > 0.02 or len(text.strip()) < 200):
                alt = via_markitdown(a.pdf)
                ra = long_word_ratio(alt)
                head.append(f"<!-- alternative markitdown, wortsalat: {ra:.4f} -->")
                if ra < r or len(text.strip()) < 200:
                    text, engine = alt, "markitdown"
        except ImportError:
            head.append("<!-- pymupdf fehlt, weiche auf markitdown aus -->")
    if a.engine == "markitdown" or not text:
        text = via_markitdown(a.pdf)
        engine = "markitdown"
        head.append(f"<!-- motor: markitdown, wortsalat: {long_word_ratio(text):.4f} -->")
    head.append(f"<!-- gewaehlt: {engine} -->")
    result = "\n".join(head) + "\n" + text
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(result, encoding="utf-8")
        print(f"{a.out}  ({engine}, {len(result):,} Zeichen)")
    else:
        sys.stdout.write(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
