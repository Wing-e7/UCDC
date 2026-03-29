"""Optional subprocess bridge to a local Staffer clone (dev only; see UCDC_ENABLE_STAFFER_LOCAL_BRIDGE)."""

from __future__ import annotations

import logging
import os
import shlex
import subprocess
from pathlib import Path
from typing import Literal

from .config import Settings, get_settings
from .schemas import StafferLocalRunOut, StafferLocalStatus

logger = logging.getLogger("ucdc")

StafferAction = Literal["setup", "setup_new", "execute"]


def _bridge_state(s: Settings) -> tuple[bool, str, str | None]:
    """Returns (enabled, message, repo_path_if_enabled)."""
    if s.ucdc_env.lower() == "production":
        return (
            False,
            "On cloud UCDC, your Staffer folder stays on your device. Use the local stack (installer or Docker on your machine) for one-tap setup.",
            None,
        )
    if not s.enable_staffer_local_bridge:
        return (
            False,
            "One-tap Staffer is off. Add UCDC_ENABLE_STAFFER_LOCAL_BRIDGE and STAFFER_LOCAL_REPO to your .env, then restart the consent server.",
            None,
        )
    raw = (s.staffer_local_repo or "").strip()
    if not raw:
        return (
            False,
            "Point STAFFER_LOCAL_REPO at your Staffer project (the folder with main.py and run_config.py).",
            None,
        )
    p = Path(raw).expanduser().resolve()
    if not p.is_dir():
        return False, f"That path isn’t a folder: {p}", None
    return True, "Ready — we’ll run commands in your Staffer project on this machine.", str(p)


def is_staffer_local_bridge_enabled() -> bool:
    s = get_settings()
    ok, _, _ = _bridge_state(s)
    return ok


def get_staffer_local_status() -> StafferLocalStatus:
    s = get_settings()
    ok, msg, repo = _bridge_state(s)
    return StafferLocalStatus(enabled=ok, repo_path=repo, message=msg)


def run_staffer_action(action: StafferAction) -> StafferLocalRunOut:
    s = get_settings()
    ok, msg, repo = _bridge_state(s)
    if not ok or not repo:
        raise RuntimeError(msg)

    cmd_map: dict[StafferAction, str] = {
        "setup": s.staffer_cmd_setup,
        "setup_new": s.staffer_cmd_setup_new,
        "execute": s.staffer_cmd_execute,
    }
    cmd = cmd_map[action]
    timeout = s.staffer_cmd_timeout_execute if action == "execute" else s.staffer_cmd_timeout_setup
    # Windows vs POSIX: split so paths and flags parse correctly on each OS.
    args = shlex.split(cmd, posix=(os.name == "posix"))
    cwd = repo
    logger.info("staffer_local_bridge: cwd=%s cmd=%s", cwd, cmd)
    try:
        proc = subprocess.run(
            args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
        )
    except subprocess.TimeoutExpired as e:
        return StafferLocalRunOut(
            ok=False,
            returncode=-1,
            stdout=e.stdout or "",
            stderr=(e.stderr or "") + f"\n[timeout after {timeout}s]",
            command=cmd,
        )
    except OSError as e:
        return StafferLocalRunOut(ok=False, returncode=-1, stdout="", stderr=str(e), command=cmd)

    return StafferLocalRunOut(
        ok=proc.returncode == 0,
        returncode=proc.returncode,
        stdout=proc.stdout or "",
        stderr=proc.stderr or "",
        command=cmd,
    )
