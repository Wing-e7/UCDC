param(
  [ValidateSet("stable", "beta")]
  [string]$Channel = "stable"
)

$ErrorActionPreference = "Stop"

Write-Host "==> UCDC Windows installer ($Channel)"

$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).
  IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
  throw "Run PowerShell as Administrator. Example: irm <installer-url> | iex"
}

$RepoUrl = if ($env:UCDC_REPO_URL) { $env:UCDC_REPO_URL } else { "https://github.com/Wing-e7/UCDC.git" }
$InstallRoot = if ($env:UCDC_INSTALL_ROOT) { $env:UCDC_INSTALL_ROOT } else { "C:\ProgramData\UCDC" }
$InstallDir = Join-Path $InstallRoot "app"

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
  throw "git is required. Install Git for Windows and rerun."
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
  throw "Docker Desktop CLI is required. Install Docker Desktop and rerun."
}

New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null

if (Test-Path (Join-Path $InstallDir ".git")) {
  Write-Host "==> Updating existing UCDC install"
  git -C $InstallDir fetch --all --tags
  git -C $InstallDir pull --ff-only
} else {
  Write-Host "==> Cloning UCDC repository"
  if (Test-Path $InstallDir) { Remove-Item -Recurse -Force $InstallDir }
  git clone --depth 1 $RepoUrl $InstallDir
}

Set-Location $InstallDir
Write-Host "==> Starting local stack"
docker compose up -d --build

Write-Host ""
Write-Host "UCDC install complete."
Write-Host "Onboarding URL: http://127.0.0.1:8001/ui/"
Write-Host "Founder URL:    http://127.0.0.1:8001/ui/founder/"
Write-Host "Health check:   curl http://127.0.0.1:8001/health"
