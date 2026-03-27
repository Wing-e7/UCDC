# UCDC Distribution (Windows + macOS)

This document defines the shipping path for one-line installs with admin privileges.

## Channels and Versioning

- Stable channel: `https://raw.githubusercontent.com/Wing-e7/UCDC/main/scripts/`
- Beta channel: `https://raw.githubusercontent.com/Wing-e7/UCDC/main/scripts/` (branch/tag override recommended for beta)
- Manifest: `scripts/install-manifest.json`

Use GitHub releases/tags as source of truth. For immediate usage, installers are pulled directly from `Wing-e7/UCDC`.

## One-Line Install Commands

### macOS (admin/sudo)

```bash
curl -fsSL https://raw.githubusercontent.com/Wing-e7/UCDC/main/scripts/install-macos.sh | sudo bash -s -- stable
```

Beta:

```bash
curl -fsSL https://raw.githubusercontent.com/Wing-e7/UCDC/main/scripts/install-macos.sh | sudo bash -s -- beta
```

### Windows (Administrator PowerShell)

```powershell
irm https://raw.githubusercontent.com/Wing-e7/UCDC/main/scripts/install-windows.ps1 | iex
```

Beta:

```powershell
irm https://raw.githubusercontent.com/Wing-e7/UCDC/main/scripts/install-windows.ps1 | iex
```

## Integrity Checks (Required)

Publish SHA256 checksums per release.

### macOS

```bash
curl -fsSL https://raw.githubusercontent.com/Wing-e7/UCDC/main/scripts/install-macos.sh -o install-macos.sh
shasum -a 256 install-macos.sh
```

### Windows

```powershell
Invoke-WebRequest https://raw.githubusercontent.com/Wing-e7/UCDC/main/scripts/install-windows.ps1 -OutFile install-windows.ps1
Get-FileHash .\install-windows.ps1 -Algorithm SHA256
```

## Rollback Procedure

1. Repoint stable URL to prior verified installer artifact (GitHub tag/raw path or release asset).
2. Update `scripts/install-manifest.json` (`version`, `prior_version`, checksums).
3. Post incident note in release log with rollback timestamp and reason.
4. Re-run smoke checks on both OS targets.

## Channel-Ready Distribution Copy

### GitHub README snippet

`macOS`: `curl -fsSL https://raw.githubusercontent.com/Wing-e7/UCDC/main/scripts/install-macos.sh | sudo bash -s -- stable`

`Windows`: `irm https://raw.githubusercontent.com/Wing-e7/UCDC/main/scripts/install-windows.ps1 | iex`

After install:
- Onboarding: `http://127.0.0.1:8001/ui/`
- Founder dashboard: `http://127.0.0.1:8001/ui/founder/`

### WhatsApp short message

`Install UCDC (Mac/Windows) in one command. Admin privileges required. Includes Trust Pact onboarding and Founder dashboard. Reply if you want beta link.`

### Telegram short message

`UCDC one-line install is live (Mac + Windows). Run as admin/sudo. Stable links + verification in docs. Founder dashboard included.`

### Email template (short)

Subject: UCDC one-line installer (Windows + macOS)

Body:
- Use stable install command from distribution docs.
- Run with admin privileges.
- Verify checksum before execution.
- Open:
  - `http://127.0.0.1:8001/ui/`
  - `http://127.0.0.1:8001/ui/founder/`

## Validation Checklist and Go/No-Go

### Test matrix

- macOS Intel (latest two supported versions)
- macOS Apple Silicon (latest two supported versions)
- Windows 11 with PowerShell 7
- Windows 11 with Windows PowerShell

### Acceptance thresholds

- Install success rate >= 90% in alpha.
- Median time to first UI <= 10 minutes.
- No critical privilege escalation or permission failures.
- Health endpoints all green after install:
  - `http://127.0.0.1:8001/health`
  - `http://127.0.0.1:8002/health`
  - `http://127.0.0.1:8003/health`
