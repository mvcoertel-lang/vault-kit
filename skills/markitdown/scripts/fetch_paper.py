#!/usr/bin/env python3
"""DOI -> Open-Access-PDF (wenn es eines gibt) -> Markdown mit Seitenankern.

Aufruf:
    python3 fetch_paper.py <DOI oder URL> --raw <ordner> --md <ordner> [--name kurzname]

Weg: OpenAlex (`open_access.oa_url`, `best_oa_location.pdf_url`, `locations[].pdf_url`),
dann Europe PMC (PMCID -> Render-PDF), dann Unpaywall (E-Mail nur als API-Hoeflichkeit,
Umgebungsvariable UNPAYWALL_EMAIL, sonst uebersprungen). Kein Sci-Hub, kein Scraping
hinter Paywalls. Ergebnis: <raw>/<name>.pdf und <md>/<name>.md; bei Fehlschlag Exit 2
und die Kandidaten-URLs auf stderr, damit der Aufrufer sie im Browser holen kann.
"""
from __future__ import annotations
import argparse, json, os, re, subprocess, sys, urllib.parse, urllib.request
from pathlib import Path

for _s in (sys.stdout, sys.stderr):  # Windows-Konsole: UTF-8 statt cp1252
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError): pass

UA = "vault-fetch-paper/1 (mailto:%s)" % os.environ.get("UNPAYWALL_EMAIL", "none@example.org")
HERE = Path(__file__).resolve().parent


def get(url: str, timeout=40) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def candidates(doi: str) -> list[str]:
    urls: list[str] = []
    try:
        w = json.loads(get(f"https://api.openalex.org/works/https://doi.org/{doi}"))
        oa = w.get("open_access") or {}
        if oa.get("oa_url"):
            urls.append(oa["oa_url"])
        best = w.get("best_oa_location") or {}
        for k in ("pdf_url", "landing_page_url"):
            if best.get(k):
                urls.append(best[k])
        for loc in w.get("locations") or []:
            if loc.get("pdf_url"):
                urls.append(loc["pdf_url"])
        ids = w.get("ids") or {}
        if ids.get("pmcid"):
            pmc = ids["pmcid"].rsplit("/", 1)[-1]
            urls.append(f"https://europepmc.org/api/fulltextRepo?pprId={pmc}&type=FILE&fileName={pmc}.pdf")
            urls.append(f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmc}/pdf/")
    except Exception as e:  # noqa
        print(f"openalex: {e}", file=sys.stderr)
    if os.environ.get("UNPAYWALL_EMAIL"):
        try:
            u = json.loads(get(f"https://api.unpaywall.org/v2/{doi}?email={os.environ['UNPAYWALL_EMAIL']}"))
            b = u.get("best_oa_location") or {}
            for k in ("url_for_pdf", "url"):
                if b.get(k):
                    urls.append(b[k])
        except Exception as e:  # noqa
            print(f"unpaywall: {e}", file=sys.stderr)
    seen, out = set(), []
    for u in urls:
        if u and u not in seen:
            seen.add(u); out.append(u)
    return out


def looks_like_pdf(b: bytes) -> bool:
    return b[:5] == b"%PDF-"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("doi")
    ap.add_argument("--raw", type=Path, required=True)
    ap.add_argument("--md", type=Path, required=True)
    ap.add_argument("--name")
    a = ap.parse_args()
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", a.doi.strip())
    name = a.name or re.sub(r"[^A-Za-z0-9]+", "_", doi).strip("_").lower()
    a.raw.mkdir(parents=True, exist_ok=True); a.md.mkdir(parents=True, exist_ok=True)
    pdf = a.raw / f"{name}.pdf"
    if not pdf.exists():
        urls = candidates(doi) if not doi.startswith("http") else [doi]
        got = False
        for u in urls:
            try:
                b = get(u)
                if looks_like_pdf(b):
                    pdf.write_bytes(b); got = True
                    print(f"pdf: {u}")
                    break
                # Landingpage: nach einem PDF-Link suchen
                m = re.search(rb'(?:citation_pdf_url"\s+content="|href=")([^"]+\.pdf[^"]*)"', b)
                if m:
                    u2 = urllib.parse.urljoin(u, m.group(1).decode())
                    b2 = get(u2)
                    if looks_like_pdf(b2):
                        pdf.write_bytes(b2); got = True
                        print(f"pdf: {u2}")
                        break
            except Exception as e:  # noqa
                print(f"  {u}: {e}", file=sys.stderr)
        if not got:
            print("kein OA-PDF gefunden. Kandidaten:", file=sys.stderr)
            for u in urls:
                print("  " + u, file=sys.stderr)
            return 2
    out = a.md / f"{name}.md"
    r = subprocess.run(["uv", "run", "-q", "--with", "pymupdf", "python", str(HERE / "pdf2md.py"), str(pdf), "-o", str(out)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    sys.stdout.write(r.stdout); sys.stderr.write(r.stderr)
    return r.returncode


if __name__ == "__main__":
    raise SystemExit(main())
