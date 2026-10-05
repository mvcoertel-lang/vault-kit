#!/usr/bin/env python3
"""Live-Schicht für den Index-Graphen: woran laufende Claude-Code-Sitzungen gerade arbeiten.

Liest nur das Ende der Transkripte unter ~/.claude/projects, die in den letzten LIVE_MIN Minuten
geschrieben wurden (interaktive Sitzungen, keine `claude -p`-Läufe), und schreibt `_Index/aktiv.js`.
Die Graphseite lädt die Datei jede Minute nach. Heraus gehen nur Knoten-IDs, die Art (work = bearbeitet,
use = benutzt), die Ruhezeit und der Sitzungstitel; keine Pfade, keine Befehle, keine Inhalte.

Aufruf: python3 index-live.py <vault>   (jede Minute: macOS launchd com.vault.index-live,
Windows Aufgabenplanung „VaultIndexLive“; beides richtet der Installer mit --live / -Live ein)
Pfade werden vor dem Vergleich vereinheitlicht (Schrägstriche, Laufwerk klein, Git-Bash-Form /c/…),
damit dieselbe Logik unter Windows greift.
"""
import datetime as dt
import json
import os
import pathlib
import re
import sys
import time

H = pathlib.Path.home()
ARGS = [a for a in sys.argv[1:] if not a.startswith('-')]
VAULT = pathlib.Path(ARGS[0]).expanduser().resolve() if ARGS else H / 'Claude'
PROJ = H / '.claude/projects'
WIN = os.name == 'nt'


def norm(p):
    """Pfad vergleichbar machen: / statt \\, unter Windows /c/x -> c:/x und Laufwerk klein."""
    p = p.replace('\\', '/')
    if WIN:
        m = re.match(r'^/([A-Za-z])/(.*)$', p)
        if m:
            p = m.group(1) + ':/' + m.group(2)
        if re.match(r'^[A-Za-z]:/', p):
            p = p[0].lower() + p[1:]
    return p


def memdir():
    try:
        d = json.loads((H / '.claude/settings.json').read_text(encoding='utf-8')).get('autoMemoryDirectory')
        if d:
            return pathlib.Path(d).expanduser()
    except (OSError, ValueError):
        pass
    return PROJ / re.sub(r'[^A-Za-z0-9]', '-', str(VAULT)) / 'memory'


MEMDIR = norm(str(memdir())) + '/'
OUT = VAULT / '_Index/aktiv.js'
LIVE_MIN = 15          # Sitzung gilt als laufend, wenn ihr Transkript so frisch ist
USE_MIN = 30           # was sie in dieser Zeit angefasst hat, gilt als „gerade benutzt“
TAIL = 512 * 1024      # nur das Ende der Datei lesen
WRITE = {'Edit', 'Write', 'MultiEdit', 'NotebookEdit'}

vroot = norm(str(VAULT)) + '/'
_formen = [re.escape(vroot[:-1]), r'~/' + re.escape(VAULT.name)]
if WIN and re.match(r'^[a-z]:/', vroot):
    _formen.append(re.escape('/' + vroot[0] + vroot[2:-1]))          # Git Bash: /c/Users/…
PATH_RE = re.compile(r'(?:' + '|'.join(_formen) + r')/([^/\s\'"`]+)(/[^\s\'"`]*)?', re.I if WIN else 0)
MEM_RE = re.compile(r'/memory/([A-Za-z0-9_.-]+)\.md')
SKILL_RE = re.compile(r'/\.claude/skills/([A-Za-z0-9_.-]+)/')


def projekt_ok(name):
    return bool(name) and not name.startswith(('.', '_')) and (VAULT / name).is_dir()


def ts(s):
    try:
        return dt.datetime.fromisoformat(s.replace('Z', '+00:00')).timestamp()
    except Exception:
        return 0.0


def tail_records(f):
    size = f.stat().st_size
    with open(f, 'rb') as h:
        if size > TAIL:
            h.seek(size - TAIL)
        lines = h.read().decode('utf-8', 'ignore').splitlines()
    if size > TAIL:
        lines = lines[1:]                     # angeschnittene erste Zeile
    for line in lines:
        try:
            yield json.loads(line)
        except Exception:
            continue


def note(acc, nid, kind):
    if acc.get(nid) != 'work':
        acc[nid] = kind


def from_path(acc, p, kind):
    """Datei- oder Ordnerpfad -> Knoten."""
    if not p:
        return
    p = norm(os.path.expanduser(p))
    if p.startswith(MEMDIR):
        stem = pathlib.Path(p).stem
        if stem != 'MEMORY':
            note(acc, 'mem:' + stem, 'use')
        return
    if p == norm(str(H / '.claude/CLAUDE.md')):
        note(acc, 'anw:global', 'use')
        return
    m = SKILL_RE.search(p)
    if m:
        note(acc, 'skill:' + m.group(1), 'use')
        return
    if p.startswith(vroot):
        rest = p[len(vroot):]
        top = rest.split('/', 1)[0]
        if rest == 'CLAUDE.md':
            note(acc, 'anw:vault', 'use')
        elif projekt_ok(top):
            note(acc, 'projekt:' + top, kind)
            if rest == top + '/CLAUDE.md':
                note(acc, 'anw:' + top, 'use')


def from_text(acc, text):
    """Pfade in einem Befehl: nur lesend gewertet."""
    text = norm(text)
    for m in PATH_RE.finditer(text):
        if projekt_ok(m.group(1)):
            note(acc, 'projekt:' + m.group(1), 'use')
    for m in MEM_RE.finditer(text):
        if m.group(1) != 'MEMORY':
            note(acc, 'mem:' + m.group(1), 'use')
    for m in SKILL_RE.finditer(text):
        note(acc, 'skill:' + m.group(1), 'use')


def tool_use(acc, writes, name, inp):
    if not isinstance(inp, dict):
        return
    if name == 'Skill' and inp.get('skill'):
        s = str(inp['skill'])
        note(acc, 'skill:' + s.split(':')[-1], 'use')
    kind = 'work' if name in WRITE else 'use'
    for key in ('file_path', 'path', 'notebook_path'):
        if isinstance(inp.get(key), str):
            from_path(acc, inp[key], kind)
            p = norm(os.path.expanduser(inp[key]))
            if kind == 'work' and p.startswith(vroot):
                top = p[len(vroot):].split('/', 1)[0]
                if projekt_ok(top):
                    writes[top] = writes.get(top, 0) + 1
    for key in ('command', 'pattern'):
        if isinstance(inp.get(key), str) and name in ('Bash', 'Grep', 'Glob'):
            from_text(acc, inp[key])


def scan(files, since):
    """Werkzeugaufrufe ab `since` aus einer Liste von Transkripten (Sitzung samt Unteragenten)."""
    acc, writes = {}, {}
    for f in files:
        for r in tail_records(f):
            if r.get('type') != 'assistant' or ts(r.get('timestamp', '')) < since:
                continue
            content = (r.get('message') or {}).get('content')
            if not isinstance(content, list):
                continue
            for c in content:
                if isinstance(c, dict) and c.get('type') == 'tool_use':
                    tool_use(acc, writes, c.get('name'), c.get('input'))
    return acc, writes


def main():
    now = time.time()
    sessions = []
    for f in PROJ.glob('*/*.jsonl'):
        try:
            mt = f.stat().st_mtime
        except OSError:
            continue
        if now - mt > LIVE_MIN * 60:
            continue
        cwd = entry = title = None
        last = 0.0
        for r in tail_records(f):
            cwd = norm(r.get('cwd') or '') or cwd
            entry = r.get('entrypoint') or entry
            title = r.get('aiTitle') or title
            last = max(last, ts(r.get('timestamp', '')))
        if not entry or entry.startswith('sdk'):
            continue                      # nur interaktive Sitzungen, keine claude -p-Läufe
        sub = sorted((f.parent / f.stem / 'subagents').glob('*.jsonl'))
        sub = [s for s in sub if now - s.stat().st_mtime < USE_MIN * 60]
        acc, writes = scan([f] + sub, now - USE_MIN * 60)
        home = None
        if cwd and cwd.startswith(vroot):
            top = cwd[len(vroot):].split('/', 1)[0]
            if projekt_ok(top):
                home = 'projekt:' + top
                note(acc, home, 'work')
                if (VAULT / top / 'CLAUDE.md').is_file():
                    note(acc, 'anw:' + top, 'use')
        if cwd and (cwd + '/').startswith(vroot):
            note(acc, 'anw:vault', 'use')
            note(acc, 'anw:global', 'use')
        if not home and writes:
            home = 'projekt:' + max(writes, key=writes.get)
        if not home:
            home = 'anw:vault'
        sessions.append({'id': f.stem[:8], 'title': (title or '')[:70], 'home': home,
                         'idle_min': int((now - (last or mt)) // 60), 'nodes': dict(sorted(acc.items()))})
    sessions.sort(key=lambda s: (s['idle_min'], s['id']))
    data = {'at': dt.datetime.now().astimezone().isoformat(timespec='seconds'), 'live_min': LIVE_MIN,
            'use_min': USE_MIN, 'sessions': sessions}
    body = '/* index-live.py: laufende Sitzungen für den Index-Graphen */\n' \
           'window.__aktivDaten && window.__aktivDaten(' + json.dumps(data, ensure_ascii=False) + ');\n'
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_name('.aktiv.js.tmp')
    tmp.write_text(body, encoding='utf-8')
    os.replace(tmp, OUT)
    if '-v' in sys.argv:
        print(json.dumps(data, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
