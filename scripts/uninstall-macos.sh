#!/usr/bin/env bash
set -euo pipefail

INSTALL_ROOT="${UCDC_INSTALL_ROOT:-/opt/ucdc}"
INSTALL_DIR="${INSTALL_ROOT}/app"

echo "==> UCDC macOS uninstall"

if [[ "${EUID}" -ne 0 ]]; then
  echo "This uninstaller requires sudo/admin privileges."
  echo "Run: sudo bash uninstall-macos.sh"
  exit 1
fi

if [[ -d "${INSTALL_DIR}" ]]; then
  cd "${INSTALL_DIR}"
  if command -v docker >/dev/null 2>&1; then
    docker compose down --remove-orphans || true
  fi
fi

rm -rf "${INSTALL_ROOT}"

echo "UCDC uninstalled from ${INSTALL_ROOT}"
