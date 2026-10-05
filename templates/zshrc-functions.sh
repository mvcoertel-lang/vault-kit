# === vault-kit: Claude-Code-Launcher (eingefügt von install.sh) ===
# claude          -> öffnet im Vault __VAULT__
# claude --here   -> öffnet im aktuellen Ordner
# (Optional: ein Modell erzwingen — hier bewusst NICHT gesetzt; per --model oder /model.)
claude() {
  local dir="__VAULT__"
  if [[ "$1" == "--here" ]]; then
    shift
    command claude "$@"
    return
  fi
  if [[ -d "$dir" ]]; then
    ( cd "$dir" && command claude "$@" )
  else
    echo "⚠️  $dir nicht gefunden — starte im aktuellen Ordner"
    command claude "$@"
  fi
}

# graphify: hält unsere Anpassungen bei JEDEM Graphify-Update in Sync.
#  - Selbstheilung: fehlt der Vault-Hausregel-Block in der (evtl. gerade
#    überschriebenen) SKILL.md, wird er nach dem Befehl automatisch neu eingesetzt
#    — egal ob durch `graphify install`, ein Upgrade oder eine Neuinstallation.
#  - nach `update`: baut den eigenen Betrachter (graph.viewer.html) gleich mit.
graphify() {
  command graphify "$@"
  local rc=$?
  local skill="$HOME/.claude/skills/graphify/SKILL.md"
  if [[ -f "$skill" ]] && ! grep -q "VAULT-HAUSREGELN" "$skill" 2>/dev/null; then
    __PY__ "__TOOLS__/graphify-reapply-houserules.py" 2>/dev/null \
      && echo "↳ Vault-Hausregeln nach Graphify-Update wieder eingesetzt"
  fi
  if [[ "$1" == "update" ]]; then
    local tgt="${2:-.}"; [[ "$tgt" == -* ]] && tgt="."
    __PY__ "__TOOLS__/graph-viewer.py" "$tgt" >/dev/null 2>&1 \
      && echo "↳ eigener Betrachter aktualisiert (graph.viewer.html)"
  fi
  return $rc
}
# === /vault-kit ===
