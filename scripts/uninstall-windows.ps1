$ErrorActionPreference = "Stop"

Write-Host "==> UCDC Windows uninstall"

$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).
  IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
  throw "Run PowerShell as Administrator."
}

$InstallRoot = if ($env:UCDC_INSTALL_ROOT) { $env:UCDC_INSTALL_ROOT } else { "C:\ProgramData\UCDC" }
$InstallDir = Join-Path $InstallRoot "app"

if (Test-Path $InstallDir) {
  Set-Location $InstallDir
  if (Get-Command docker -ErrorAction SilentlyContinue) {
    docker compose down --remove-orphans | Out-Null
  }
}

if (Test-Path $InstallRoot) {
  Remove-Item -Recurse -Force $InstallRoot
}

Write-Host "UCDC uninstalled from $InstallRoot"
