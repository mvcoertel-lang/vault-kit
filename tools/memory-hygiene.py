#!/usr/bin/env python3
"""Read-only Hygiene-Check des Vault-Memory-Verzeichnisses.
Gibt bei Handlungsbedarf eine kurze Erinnerung auf stderr aus (die Claude Code
am SessionEnd anzeigt), sonst nichts. Exit-Code immer 0 — blockiert nie.

Aufruf: python3 memory-hygiene.py [memory-verzeichnis] [--hook]
Ohne Argument: `autoMemoryDirectory` aus ~/.claude/settings.json, sonst aus dem Arbeitsverzeichnis
abgeleitet, wie Claude Code es tut (~/.claude/projects/<slug>/memory). Wird vom SessionEnd-Hook der
Vault-settings.json mit --hook aufgerufen: dann still bei `claude -p`-Läufen (CLAUDE_CODE_ENTRYPOINT sdk-*).

Prüft (seit server-kit 2026-09-21, BEWERTUNG_Vault-Struktur_vs_Evidenz Nr. 6): Indexlänge, Dateien ohne
Indexzeile, tote Indexzeilen, isolierte Dateien, fehlendes Ereignisdatum (`date:` oder `metadata.date:`),
Ablöseverweise (`superseded_by`) auf nicht vorhandene Dateien.
"""
import json, os, pathlib, re, sys

INDEX_MAX = 40
ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
if "--hook" in sys.argv and os.environ.get("CLAUDE_CODE_ENTRYPOINT", "").startswith("sdk"):
    sys.exit(0)
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")   # Windows-Konsole ist sonst cp1252
    except (AttributeError, ValueError):
        pass


def derive_memdir() -> pathlib.Path:
    try:
        d = json.loads((pathlib.Path.home() / ".claude" / "settings.json").read_text(encoding="utf-8")).get("autoMemoryDirectory")
        if d:
            return pathlib.Path(d).expanduser()
    except (OSError, ValueError):
        pass
    cwd = pathlib.Path(os.getcwd()).resolve()
    slug = re.sub(r"[^A-Za-z0-9]", "-", str(cwd))
    return pathlib.Path.home() / ".claude" / "projects" / slug / "memory"


MEM = pathlib.Path(ARGS[0]).expanduser() if ARGS else derive_memdir()


def frontmatter(text: str) -> str:
    if not text.startswith("---"):
        return ""
    end = text.find("\n---", 3)
    return text[3:end] if end > 0 else ""


def main():
    if not MEM.is_dir():
        return
    files = sorted(p for p in MEM.glob("*.md") if p.name != "MEMORY.md")
    idx = MEM / "MEMORY.md"
    idx_text = idx.read_text(encoding="utf-8") if idx.is_file() else ""
    idx_lines = [l for l in idx_text.splitlines() if l.strip().startswith("- [")]

    referenced = set(re.findall(r"\]\(([^)]+\.md)\)", idx_text))
    stems = {p.name for p in files}
    # abgelöste Dateien (superseded_by) verlieren laut memory-write Regel 7 ihre Indexzeile
    orphans = sorted(p.name for p in files if p.name not in referenced
                     and "superseded_by:" not in frontmatter(p.read_text(encoding="utf-8", errors="ignore")))
    dead = sorted(r for r in referenced if r not in stems)

    linked = set()
    bodies = {}
    for p in files:
        bodies[p] = p.read_text(encoding="utf-8", errors="ignore")
        for t in re.findall(r"\[\[([^\]]+)\]\]", bodies[p]):
            linked.add(t.strip().lower())

    def isolated(p):
        return "[[" not in bodies[p] and p.stem.lower() not in linked

    iso = sorted(p.name for p in files if isolated(p))

    # Ereignisdatum und Ablösung
    no_date = []
    bad_super = []
    for p in files:
        fm = frontmatter(bodies[p])
        if not re.search(r"^\s*date:\s*\d{4}-\d{2}-\d{2}", fm, re.M):
            no_date.append(p.name)
        for target in re.findall(r"superseded_by:\s*\[?\[?([^\]\n]+)\]?\]?", fm):
            t = target.strip().strip('"').strip("'")
            if t and not t.endswith(".md"):
                t += ".md"
            if t and t not in stems:
                bad_super.append(f"{p.name} → {t}")

    issues = []
    if len(idx_lines) > INDEX_MAX:
        issues.append(f"MEMORY.md hat {len(idx_lines)} Index-Zeilen (>{INDEX_MAX}) — kürzen/archivieren")
    size = len(idx_text.encode("utf-8"))
    if size > 25000:
        issues.append(f"MEMORY.md hat {size} Bytes (> 25 000): das Ende wird beim Sitzungsstart nicht geladen")
    if orphans:
        issues.append(f"{len(orphans)} Memory-Datei(en) ohne Index-Zeile: {', '.join(orphans)}")
    if dead:
        issues.append(f"{len(dead)} tote Index-Zeile(n) (Datei fehlt): {', '.join(dead)}")
    if iso:
        issues.append(f"{len(iso)} isolierte Datei(en) (kein [[wikilink]]): {', '.join(iso)}")
    if no_date:
        shown = ", ".join(no_date[:6]) + (" …" if len(no_date) > 6 else "")
        issues.append(f"{len(no_date)} von {len(files)} Datei(en) ohne Ereignisdatum `date:` im Frontmatter: {shown}")
    if bad_super:
        issues.append(f"{len(bad_super)} Ablöseverweis(e) ins Leere: {', '.join(bad_super)}")

    if issues:
        print(f"🧹 Memory-Hygiene fällig ({MEM}) — `/memory-review` ausführen:", file=sys.stderr)
        for i in issues:
            print("   • " + i, file=sys.stderr)


try:
    main()
except Exception as ex:          # Hygiene darf eine Sitzung nie stören
    print(f"memory-hygiene: {ex}", file=sys.stderr)
