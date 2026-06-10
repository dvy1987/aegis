# Aegis dev launcher (Windows PowerShell 5.1+ / PowerShell 7+).
#
# Starts the backend services (v1 + swarm) and the frontend (Next.js) together,
# streams interleaved logs with [back-v1] / [back-swarm] / [frontend] prefixes,
# and cleans up all processes on Ctrl-C.
#
# Usage:
#   .\scripts\dev.ps1                     # all three
#   .\scripts\dev.ps1 -Target backend    # both backends only
#   .\scripts\dev.ps1 -Target frontend   # frontend only
#
# Env / param overrides:
#   -BackendV1Port    default 8001
#   -BackendSwarmPort default 8002
#   -FrontendPort     default 3000
#   -BackendHost      default 127.0.0.1
#
# If you get an execution-policy error, run once per shell:
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

[CmdletBinding()]
param(
  [ValidateSet("both", "backend", "frontend")]
  [string] $Target = "both",
  [int]    $BackendV1Port    = 8001,
  [int]    $BackendSwarmPort = 8002,
  [int]    $FrontendPort     = 3000,
  [string] $BackendHost      = "127.0.0.1"
)

$ErrorActionPreference = "Stop"

$Root        = Split-Path -Parent $PSScriptRoot
$BackendDir  = Join-Path $Root "backend"
$FrontendDir = Join-Path $Root "frontend"

# --- Logging helpers -------------------------------------------------------

function Write-Info($msg)  { Write-Host "[dev] $msg" -ForegroundColor DarkGray }
function Write-Warn2($msg) { Write-Host "[dev] $msg" -ForegroundColor Yellow }
function Write-Err2($msg)  { Write-Host "[dev] $msg" -ForegroundColor Red }

# --- Tool checks -----------------------------------------------------------

function Test-Tool($name, $installHint) {
  if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
    Write-Err2 "missing required tool: $name"
    Write-Err2 "  install: $installHint"
    return $false
  }
  return $true
}

$needsBackend  = ($Target -eq "both" -or $Target -eq "backend")
$needsFrontend = ($Target -eq "both" -or $Target -eq "frontend")

if ($needsBackend -and -not (Test-Path $BackendDir)) {
  Write-Warn2 "backend dir not found at $BackendDir — skipping backend"
  $needsBackend = $false
  if (-not $needsFrontend) { exit 1 }
}
if ($needsFrontend -and -not (Test-Path $FrontendDir)) {
  Write-Warn2 "frontend dir not found at $FrontendDir — skipping frontend"
  $needsFrontend = $false
  if (-not $needsBackend) { exit 1 }
}

if ($needsBackend  -and -not (Test-Tool "uv"   "https://docs.astral.sh/uv/getting-started/")) { exit 1 }
if ($needsFrontend -and -not (Test-Tool "pnpm" "winget install pnpm.pnpm  (or npm i -g pnpm)")) { exit 1 }

# --- Load .env from repo root, if present ---------------------------------

$envFile = Join-Path $Root ".env"
if (Test-Path $envFile) {
  Get-Content $envFile | ForEach-Object {
    $line = $_.Trim()
    if (-not $line) { return }
    if ($line.StartsWith("#")) { return }
    $eq = $line.IndexOf("=")
    if ($eq -lt 1) { return }
    $key = $line.Substring(0, $eq).Trim()
    $val = $line.Substring($eq + 1).Trim().Trim('"').Trim("'")
    # Skip empty values — an empty GOOGLE_APPLICATION_CREDENTIALS= would shadow the gcloud ADC chain.
    if (-not $val) { return }
    [System.Environment]::SetEnvironmentVariable($key, $val, "Process")
  }
  Write-Info ".env loaded from $envFile"
}

# --- Process bookkeeping ---------------------------------------------------

$processes  = New-Object System.Collections.Generic.List[System.Diagnostics.Process]
$jobs       = New-Object System.Collections.Generic.List[System.Management.Automation.Job]

function Stop-AllProcesses {
  foreach ($p in $processes) {
    try {
      if ($p -and -not $p.HasExited) {
        try { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue } catch {}
      }
    } catch {}
  }
  foreach ($j in $jobs) {
    try { Stop-Job   -Job $j -ErrorAction SilentlyContinue } catch {}
    try { Remove-Job -Job $j -Force -ErrorAction SilentlyContinue } catch {}
  }
}

# --- Process launcher ------------------------------------------------------

function Start-StreamingProcess {
  param(
    [string]   $Label,
    [ConsoleColor] $Color,
    [string]   $WorkingDir,
    [string]   $FileName,
    [string[]] $Arguments,
    [hashtable] $ExtraEnv = @{}
  )

  $psi = New-Object System.Diagnostics.ProcessStartInfo
  $psi.FileName               = $FileName
  foreach ($a in $Arguments) { $psi.ArgumentList.Add($a) }
  $psi.WorkingDirectory       = $WorkingDir
  $psi.UseShellExecute        = $false
  $psi.RedirectStandardOutput = $true
  $psi.RedirectStandardError  = $true
  $psi.CreateNoWindow         = $true
  foreach ($k in $ExtraEnv.Keys) { $psi.Environment[$k] = [string]$ExtraEnv[$k] }

  $proc = [System.Diagnostics.Process]::new()
  $proc.StartInfo = $psi
  $proc.EnableRaisingEvents = $true

  $tag = "[$Label]"

  $onOut = {
    param($sender, $e)
    if ($null -ne $e.Data) {
      Write-Host "$($Event.MessageData.Tag) $($e.Data)" -ForegroundColor $Event.MessageData.Color
    }
  }
  $onErr = {
    param($sender, $e)
    if ($null -ne $e.Data) {
      Write-Host "$($Event.MessageData.Tag) $($e.Data)" -ForegroundColor $Event.MessageData.Color
    }
  }
  $msg = [pscustomobject]@{ Tag = $tag; Color = $Color }

  Register-ObjectEvent -InputObject $proc -EventName OutputDataReceived -Action $onOut -MessageData $msg | Out-Null
  Register-ObjectEvent -InputObject $proc -EventName ErrorDataReceived  -Action $onErr -MessageData $msg | Out-Null

  [void] $proc.Start()
  $proc.BeginOutputReadLine()
  $proc.BeginErrorReadLine()
  return $proc
}

# --- Launchers -------------------------------------------------------------

function Start-BackendV1 {
  Write-Info "starting backend v1 on http://${BackendHost}:${BackendV1Port} (Phoenix: default)"
  $args = @(
    "run", "uvicorn", "app.main_v1:app",
    "--host", $BackendHost,
    "--port", "$BackendV1Port",
    "--reload"
  )
  $extra = @{
    PHOENIX_PROJECT_NAME = "default"
  }
  $p = Start-StreamingProcess `
    -Label "back-v1" -Color Green `
    -WorkingDir $BackendDir `
    -FileName "uv" -Arguments $args `
    -ExtraEnv $extra
  $processes.Add($p) | Out-Null
}

function Start-BackendSwarm {
  Write-Info "starting backend swarm on http://${BackendHost}:${BackendSwarmPort} (Phoenix: aegis-swarm)"
  $args = @(
    "run", "uvicorn", "app.main_swarm:app",
    "--host", $BackendHost,
    "--port", "$BackendSwarmPort",
    "--reload"
  )
  $extra = @{
    PHOENIX_PROJECT_NAME = "aegis-swarm"
  }
  $p = Start-StreamingProcess `
    -Label "back-swarm" -Color Cyan `
    -WorkingDir $BackendDir `
    -FileName "uv" -Arguments $args `
    -ExtraEnv $extra
  $processes.Add($p) | Out-Null
}

function Start-Frontend {
  Write-Info "starting frontend on http://localhost:${FrontendPort} (next dev)"
  $extra = @{
    NEXT_PUBLIC_BACKEND_V1_URL    = "http://${BackendHost}:${BackendV1Port}";
    NEXT_PUBLIC_BACKEND_SWARM_URL = "http://${BackendHost}:${BackendSwarmPort}";
    PORT                          = "$FrontendPort"
  }
  $p = Start-StreamingProcess `
    -Label "frontend" -Color Yellow `
    -WorkingDir $FrontendDir `
    -FileName "pnpm" -Arguments @("dev") `
    -ExtraEnv $extra
  $processes.Add($p) | Out-Null
}

if ($needsBackend)  { Start-BackendV1; Start-BackendSwarm }
if ($needsFrontend) { Start-Frontend }

# --- Readiness probes ------------------------------------------------------

if ($needsBackend) {
  $deadline = (Get-Date).AddSeconds(30)
  $v1Ready = $false
  $swarmReady = $false

  while ((Get-Date) -lt $deadline -and -not ($v1Ready -and $swarmReady)) {
    if (-not $v1Ready) {
      try {
        $r = Invoke-WebRequest -Uri "http://${BackendHost}:${BackendV1Port}/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        if ($r.StatusCode -eq 200) {
          Write-Info "backend v1 ready   http://${BackendHost}:${BackendV1Port}/health"
          $v1Ready = $true
        }
      } catch {}
    }
    if (-not $swarmReady) {
      try {
        $r = Invoke-WebRequest -Uri "http://${BackendHost}:${BackendSwarmPort}/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        if ($r.StatusCode -eq 200) {
          Write-Info "backend swarm ready http://${BackendHost}:${BackendSwarmPort}/health"
          $swarmReady = $true
        }
      } catch {}
    }
    Start-Sleep -Milliseconds 500
  }
  if (-not $v1Ready)    { Write-Warn2 "backend v1 did not become ready within 30s" }
  if (-not $swarmReady) { Write-Warn2 "backend swarm did not become ready within 30s" }
}

if ($needsFrontend) {
  Write-Info "frontend starting on http://localhost:${FrontendPort}"
}

Write-Info "press Ctrl-C to stop"

# Trap Ctrl-C and exit cleanly.
$cancelled = $false
try {
  $handler = {
    param($sender, $e)
    $e.Cancel = $true
    $script:cancelled = $true
  }
  [Console]::add_CancelKeyPress($handler)

  while (-not $cancelled) {
    $allDead = $true
    foreach ($p in $processes) {
      if ($p -and -not $p.HasExited) { $allDead = $false }
    }
    if ($allDead) { break }
    Start-Sleep -Milliseconds 250
  }

  if ($cancelled) {
    Write-Info "shutting down..."
  } else {
    Write-Warn2 "a child process exited; stopping the others"
  }
} finally {
  Stop-AllProcesses
  Write-Info "stopped"
}
