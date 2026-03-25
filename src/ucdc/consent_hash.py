import hashlib
import json
from typing import List


def compute_consent_hash(*, user_id: str, agent_id: str, resources: List[str]) -> str:
    # Hash only the parts the orchestrator must be able to deterministically verify.
    # (We intentionally exclude `explanation` and any job-specific "data".)
    payload = {"user_id": user_id, "agent_id": agent_id, "resources": resources}
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()

