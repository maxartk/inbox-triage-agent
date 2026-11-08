"""File-based outbox with an explicit human approval gate and audit trail."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, List, Optional

PENDING = "pending_approval"
APPROVED = "approved"
SENT = "sent"
REJECTED = "rejected"


class Outbox:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.pending_dir = self.root / PENDING
        self.sent_dir = self.root / SENT
        self.audit_path = self.root / "audit.jsonl"
        for directory in (self.pending_dir, self.sent_dir):
            directory.mkdir(parents=True, exist_ok=True)

    # --- audit -----------------------------------------------------------
    def _audit(self, action: str, item_id: str, actor: str, extra: Optional[Dict] = None) -> None:
        record = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "action": action,
            "id": item_id,
            "actor": actor,
        }
        if extra:
            record.update(extra)
        with self.audit_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    # --- write -----------------------------------------------------------
    def submit(self, item: Dict) -> Path:
        item_id = item["id"]
        item.setdefault("status", PENDING)
        item.setdefault("created", time.strftime("%Y-%m-%dT%H:%M:%S"))
        path = self.pending_dir / f"{item_id}.json"
        path.write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
        self._audit("submitted", item_id, "agent", {"intent": item.get("triage", {}).get("intent")})
        return path

    # --- read ------------------------------------------------------------
    def list_pending(self) -> List[Dict]:
        items = []
        for path in sorted(self.pending_dir.glob("*.json")):
            items.append(json.loads(path.read_text(encoding="utf-8")))
        return items

    def get(self, item_id: str) -> Optional[Dict]:
        path = self.pending_dir / f"{item_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    # --- transitions -----------------------------------------------------
    def approve(self, item_id: str, actor: str) -> Dict:
        if not actor or not actor.strip():
            raise PermissionError("approve vyžaduje jméno schvalovatele (--by)")

        item = self.get(item_id)
        if item is None:
            sent_path = self.sent_dir / f"{item_id}.json"
            if sent_path.exists():
                self._audit("approve_rejected_already_sent", item_id, actor)
                return {"id": item_id, "status": "already_sent"}
            raise FileNotFoundError(f"Položka {item_id} neexistuje")

        if item.get("status") == APPROVED:
            self._audit("approve_rejected_duplicate", item_id, actor)
            return {"id": item_id, "status": "already_approved"}

        item["status"] = APPROVED
        item["approved_by"] = actor
        item["approved_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        (self.sent_dir / f"{item_id}.json").write_text(
            json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (self.pending_dir / f"{item_id}.json").unlink()
        self._audit("approved", item_id, actor)
        return {"id": item_id, "status": APPROVED}

    def reject(self, item_id: str, actor: str, reason: str = "") -> Dict:
        item = self.get(item_id)
        if item is None:
            raise FileNotFoundError(f"Položka {item_id} neexistuje")
        item["status"] = REJECTED
        item["rejected_by"] = actor
        item["reject_reason"] = reason
        (self.root / f"{item_id}.rejected.json").write_text(
            json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (self.pending_dir / f"{item_id}.json").unlink()
        self._audit("rejected", item_id, actor, {"reason": reason})
        return {"id": item_id, "status": REJECTED}

    def read_audit(self) -> List[Dict]:
        if not self.audit_path.exists():
            return []
        return [json.loads(line) for line in self.audit_path.read_text(encoding="utf-8").splitlines() if line.strip()]
