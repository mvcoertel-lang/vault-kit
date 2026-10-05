<#
.SYNOPSIS
    vault-kit unter Windows installieren oder aktualisieren.
.DESCRIPTION
    Sucht ein echtes Python 3.9+ (zuerst den Launcher "py -3", dann "python"; den Microsoft-Store-
    Platzhalter lehnt es ab), prüft Git for Windows und die ExecutionPolicy und startet dann
    install.py, die gemeinsame Logik für Windows, macOS und Linux. Mehrfach ausführbar.
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\install.ps1
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\install.ps1 -Vault D:\Vault -Live
#>
param(
    [string]$Vault = (Join-Path $HOME 'Claude'),
    [switch]$NoGraphify,
    [switch]$Live,
    [switch]$ForceKit
)
$ErrorActionPreference = 'Continue'
$Kit = Split-Path -Parent $MyInvocation.MyCommand.Path
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}

function Test-Python([string[]]$cmd) {
    $exe = $cmd[0]
    $pre = @($cmd | Select-Object -Skip 1)
    try {
        $v = & $exe @pre -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null | Select-Object -Last 1
        if ($LASTEXITCODE -eq 0 -and "$v" -match '^3\.(\d+)$' -and [int]$Matches[1] -ge 9) { return $true }
    } catch {}
    return $false
}

$py = $null
foreach ($c in @(, @('py', '-3')) + @(, @('python')) + @(, @('python3'))) {
    if ((Get-Command $c[0] -ErrorAction SilentlyContinue) -and (Test-Python $c)) { $py = $c; break }
}
if (-not $py) {
    Write-Host 'Python 3.9 oder neuer fehlt.' -ForegroundColor Yellow
    Write-Host '  winget install Python.Python.3.13'
    Write-Host '  oder https://www.python.org/downloads/windows/ (Haken bei "py launcher" und "Add python.exe to PATH")'
    Write-Host 'Danach ein neues PowerShell-Fenster öffnen und install.ps1 erneut starten.'
    exit 1
}
Write-Host "Python: $($py -join ' ')"

if (-not (Get-Command git -ErrorAction SilentlyContinue) -and -not (Test-Path 'C:\Program Files\Git\bin\bash.exe')) {
    Write-Warning 'Git for Windows fehlt. Claude Code braucht es unter Windows für Shell-Befehle: winget install Git.Git'
}

# Wirksame ExecutionPolicy ohne die Prozess-Ebene (die setzt -ExecutionPolicy Bypass nur für diesen Lauf)
$pol = 'Restricted'
foreach ($e in Get-ExecutionPolicy -List) {
    if ($e.Scope -ne 'Process' -and "$($e.ExecutionPolicy)" -ne 'Undefined') { $pol = "$($e.ExecutionPolicy)"; break }
}
if ($pol -in @('Restricted', 'AllSigned')) {
    Write-Warning ("ExecutionPolicy ist $pol. Dann lädt PowerShell das Profil mit den Startern claude/graphify nicht. " +
        'Abhilfe, falls erlaubt: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned. Die Desktop-App und die Hooks laufen unabhängig davon.')
}

$docs = [Environment]::GetFolderPath('MyDocuments')
$a = @($py | Select-Object -Skip 1) + @((Join-Path $Kit 'install.py'), $Vault, '--py', ($py -join ' '), '--docs', $docs)
if ($NoGraphify) { $a += '--no-graphify' }
if ($Live) { $a += '--live' }
if ($ForceKit) { $a += '--force-kit' }
& $py[0] @a
exit $LASTEXITCODE
