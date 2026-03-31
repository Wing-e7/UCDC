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

StafferAction = Literal["get", "setup", "setup_new", "execute"]


def _resolve_repo_path(s: Settings) -> Path | None:
    raw = (s.staffer_local_repo or "").strip()
    if not raw:
        return None
    return Path(raw).expanduser().resolve()


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
    repo_path = _resolve_repo_path(s)
    if not repo_path:
        return (
            False,
            "Point STAFFER_LOCAL_REPO at your Staffer project (the folder with main.py and run_config.py).",
            None,
        )
    if repo_path.exists() and not repo_path.is_dir():
        return False, f"That path exists but is not a folder: {repo_path}", None
    if not repo_path.exists():
        return True, "Staffer is not downloaded yet. Tap GET STAFFER to clone it on this machine.", str(repo_path)
    return True, "Ready — we’ll run commands in your Staffer project on this machine.", str(repo_path)


def is_staffer_local_bridge_enabled() -> bool:
    s = get_settings()
    ok, _, _ = _bridge_state(s)
    return ok


def get_staffer_local_status() -> StafferLocalStatus:
    s = get_settings()
    ok, msg, repo = _bridge_state(s)
    return StafferLocalStatus(enabled=ok, repo_path=repo, message=msg)


def _run_command(*, args: list[str], cwd: str, timeout: int, command_label: str) -> StafferLocalRunOut:
    logger.info("staffer_local_bridge: cwd=%s cmd=%s", cwd, command_label)
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
            command=command_label,
        )
    except OSError as e:
        return StafferLocalRunOut(ok=False, returncode=-1, stdout="", stderr=str(e), command=command_label)
    return StafferLocalRunOut(
        ok=proc.returncode == 0,
        returncode=proc.returncode,
        stdout=proc.stdout or "",
        stderr=proc.stderr or "",
        command=command_label,
    )


def run_staffer_action(action: StafferAction) -> StafferLocalRunOut:
    s = get_settings()
    ok, msg, repo = _bridge_state(s)
    if not ok or not repo:
        raise RuntimeError(msg)

    repo_path = Path(repo)
    if action == "get":
        git_url = (s.staffer_git_url or "").strip()
        if not git_url:
            return StafferLocalRunOut(
                ok=False,
                returncode=-1,
                stdout="",
                stderr="Set STAFFER_GIT_URL in your environment so UCDC knows where to clone Staffer from.",
                command="git clone",
            )
        if repo_path.exists() and (repo_path / ".git").is_dir():
            args = ["git", "-C", str(repo_path), "pull", "--ff-only"]
            return _run_command(
                args=args,
                cwd=str(repo_path),
                timeout=s.staffer_cmd_timeout_setup,
                command_label="git -C <repo> pull --ff-only",
            )
        repo_path.parent.mkdir(parents=True, exist_ok=True)
        args = ["git", "clone", git_url, str(repo_path)]
        return _run_command(
            args=args,
            cwd=str(repo_path.parent),
            timeout=s.staffer_cmd_timeout_setup,
            command_label=f"git clone {git_url} {repo_path}",
        )

    if not repo_path.is_dir():
        return StafferLocalRunOut(
            ok=False,
            returncode=-1,
            stdout="",
            stderr=f"Staffer folder not found at {repo_path}. Tap GET STAFFER first.",
            command="",
        )

    cmd_map = {
        "setup": s.staffer_cmd_setup,
        "setup_new": s.staffer_cmd_setup_new,
        "execute": s.staffer_cmd_execute,
    }
    cmd = cmd_map[action]
    timeout = s.staffer_cmd_timeout_execute if action == "execute" else s.staffer_cmd_timeout_setup
    # Windows vs POSIX: split so paths and flags parse correctly on each OS.
    args = shlex.split(cmd, posix=(os.name == "posix"))
    return _run_command(
        args=args,
        cwd=str(repo_path),
        timeout=timeout,
        command_label=cmd,
    )
