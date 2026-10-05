# === vault-kit: Claude-Code-Launcher (eingefügt von install.ps1) ===
# claude          -> öffnet Claude Code im Vault __VAULT__
# claude --here   -> öffnet im aktuellen Ordner
# graphify ...    -> wie graphify, setzt nach jedem Update die Vault-Hausregeln wieder ein
function claude {
    $exe = Get-Command claude -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $exe) { Write-Warning 'Claude Code (claude) nicht gefunden. Desktop-App nutzen oder CLI installieren.'; return }
    if ($args.Count -gt 0 -and $args[0] -eq '--here') {
        $rest = @($args | Select-Object -Skip 1)
        & $exe.Source @rest
        return
    }
    $dir = '__VAULT__'
    if (Test-Path -LiteralPath $dir -PathType Container) {
        Push-Location -LiteralPath $dir
        try { & $exe.Source @args } finally { Pop-Location }
    } else {
        Write-Warning "$dir nicht gefunden, starte im aktuellen Ordner"
        & $exe.Source @args
    }
}

function graphify {
    $exe = Get-Command graphify -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $exe) { Write-Warning 'graphify nicht gefunden (uv tool install graphifyy)'; return }
    & $exe.Source @args
    $rc = $LASTEXITCODE
    $skill = Join-Path $HOME '.claude/skills/graphify/SKILL.md'
    if ((Test-Path -LiteralPath $skill) -and -not (Select-String -LiteralPath $skill -Pattern 'VAULT-HAUSREGELN' -Quiet)) {
        __PY__ '__TOOLS__/graphify-reapply-houserules.py' | Out-Null
        if ($LASTEXITCODE -eq 0) { Write-Host '-> Vault-Hausregeln nach Graphify-Update wieder eingesetzt' }
    }
    if ($args.Count -gt 0 -and $args[0] -eq 'update') {
        $tgt = '.'
        if ($args.Count -gt 1 -and -not "$($args[1])".StartsWith('-')) { $tgt = "$($args[1])" }
        __PY__ '__TOOLS__/graph-viewer.py' $tgt *> $null
        if ($LASTEXITCODE -eq 0) { Write-Host '-> eigener Betrachter aktualisiert (graph.viewer.html)' }
    }
    $global:LASTEXITCODE = $rc
}
# === /vault-kit ===
