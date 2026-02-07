<#
Load environment variables from a .env file at the repository root
and launch VS Code from that environment so settings like
`${env:PGDATABASE}` are available to workspace settings.

Usage:
  powershell -ExecutionPolicy ByPass -File .\scripts\open-vscode-with-env.ps1
  # or with explicit env file
  powershell -ExecutionPolicy ByPass -File .\scripts\open-vscode-with-env.ps1 -EnvPath 'C:\path\to\.env'
#>

param(
    [string]$EnvPath = ''
)

$workspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

if (-not $EnvPath) {
    $EnvPath = Join-Path $workspaceRoot '.env'
}

if (-not (Test-Path $EnvPath)) {
    Write-Host "No .env found at $EnvPath; launching VS Code without loading env vars."
    code $workspaceRoot
    exit 0
}

Get-Content $EnvPath | ForEach-Object {
    if ($_ -and ($_ -notmatch '^[\s#]')) {
        $parts = $_ -split '=', 2
        if ($parts.Length -eq 2) {
            $name = $parts[0].Trim()
            $value = $parts[1].Trim()
            Set-Item -Path Env:$name -Value $value
        }
    }
}

Write-Host "Loaded environment variables from $EnvPath"
code $workspaceRoot
