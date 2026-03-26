#!/usr/bin/env bash
set -euo pipefail

CHANNEL="${1:-stable}"
REPO_URL="${UCDC_REPO_URL:-https://github.com/Wing-e7/UCDC.git}"
INSTALL_ROOT="${UCDC_INSTALL_ROOT:-/opt/ucdc}"
INSTALL_DIR="${INSTALL_ROOT}/app"

echo "==> UCDC macOS installer (${CHANNEL})"

if [[ "${EUID}" -ne 0 ]]; then
  echo "This installer requires sudo/admin privileges."
  echo "Run: curl -fsSL <installer-url> | sudo bash -s -- ${CHANNEL}"
  exit 1
fi

if ! command -v git >/dev/null 2>&1; then
  echo "==> Installing git via Xcode Command Line Tools"
  xcode-select --install || true
  echo "Please rerun once git is available."
  exit 1
fi

if ! command -v brew >/dev/null 2>&1; then
  echo "==> Homebrew is required."
  echo "Install Homebrew first: https://brew.sh/"
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "==> Installing Docker CLI via Homebrew"
  brew install docker docker-compose
fi

mkdir -p "${INSTALL_ROOT}"
chown "${SUDO_USER:-root}:${SUDO_GID:-0}" "${INSTALL_ROOT}" || true

if [[ -d "${INSTALL_DIR}/.git" ]]; then
  echo "==> Updating existing UCDC install"
  git -C "${INSTALL_DIR}" fetch --all --tags
  git -C "${INSTALL_DIR}" pull --ff-only
else
  echo "==> Cloning UCDC repository"
  rm -rf "${INSTALL_DIR}"
  git clone --depth 1 "${REPO_URL}" "${INSTALL_DIR}"
fi

cd "${INSTALL_DIR}"

echo "==> Starting local stack"
docker compose up -d --build

cat <<EOF

UCDC install complete.
Onboarding URL: http://127.0.0.1:8001/ui/
Founder URL:    http://127.0.0.1:8001/ui/founder/
Health check:   curl -s http://127.0.0.1:8001/health

EOF
