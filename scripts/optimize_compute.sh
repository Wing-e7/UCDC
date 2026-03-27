#!/bin/bash
set -euo pipefail

# Usage: optimize_compute.sh [--dry-run]
# Runs only on macOS. Use --dry-run to see what would happen.

DRY_RUN=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=true; shift;;
    *) echo "Unsupported flag: $1" >&2; exit 1;;
  esac
done

log() {
  printf "%s %s\n" "$(date --iso-8601=seconds)" "$*"
}

gather_top() {
  log "Top 10 memory users"
  ps -e -o pid,%mem,%cpu,command --sort=-%mem | head -n 10
}

terminate_apps() {
  local apps=("Safari" "Mail" "Notes" "Messages" "Preview")
  for app in "${apps[@]}"; do
    if pgrep -x "$app" > /dev/null; then
      log "Requesting quit for $app"
      if ! $DRY_RUN; then
        osascript -e "tell application \"$app\" to quit" >/dev/null 2>&1 || true
      fi
    fi
  done
}

free_memory() {
  if $DRY_RUN; then
    log "Would run: sudo purge"
  else
    if command -v purge >/dev/null; then
      log "Running sudo purge (may ask for password)"
      sudo purge >/dev/null 2>&1
    else
      log "purge not available, skipping"
    fi
  fi
  log "Recording vm_stat"
  vm_stat
}

restart_background_daemons() {
  log "Restarting low-priority background daemons"
  readonly daemons=("com.apple.SiriService" "com.apple.AirPlayUIAgent")
  for d in "${daemons[@]}"; do
    if launchctl print "system/$d" > /dev/null 2>&1; then
      if $DRY_RUN; then
        log "Would unload + load $d"
      else
        sudo launchctl kickstart -k "system/$d" >/dev/null 2>&1 || true
      fi
    fi
  done
}

log "Starting compute optimization"
gather_top
terminate_apps
free_memory
restart_background_daemons
log "Optimization complete"
