"""Append-only hash-chained audit log for local demonstrations."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOG_FILE = PROJECT_ROOT / "data" / "audit" / "audit.log"


class AuditLog:
    def __init__(self, log_file=DEFAULT_LOG_FILE):
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def _calculate_hash(self, entry):
        content = json.dumps(entry, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(content).hexdigest()

    def _get_last_hash(self):
        entries = self.entries()
        return entries[-1]["entry_hash"] if entries else "GENESIS"

    def entries(self):
        if not self.log_file.exists():
            return []
        entries = []
        for line in self.log_file.read_text(encoding="utf-8").splitlines():
            if line.strip():
                entries.append(json.loads(line))
        return entries

    def append(self, event, data):
        entry = {"timestamp": datetime.now(timezone.utc).isoformat(), "event": event,
                 "data": data, "previous_hash": self._get_last_hash()}
        entry["entry_hash"] = self._calculate_hash(entry)
        with self.log_file.open("a", encoding="utf-8") as file:
            file.write(json.dumps(entry, sort_keys=True) + "\n")
        return entry

    def verify(self):
        if not self.log_file.exists():
            return True, "Audit log is empty."
        previous_hash = "GENESIS"
        try:
            lines = self.log_file.read_text(encoding="utf-8").splitlines()
        except OSError:
            return False, "Audit log could not be read."
        for index, line in enumerate(lines, start=1):
            try:
                entry = json.loads(line)
                if not isinstance(entry, dict):
                    return False, f"Invalid entry structure at entry {index}."
            except json.JSONDecodeError:
                return False, f"Invalid JSON at entry {index}."
            if entry.get("previous_hash") != previous_hash:
                return False, f"Chain broken at entry {index}."
            stored_hash = entry.get("entry_hash")
            without_hash = {key: value for key, value in entry.items() if key != "entry_hash"}
            if self._calculate_hash(without_hash) != stored_hash:
                return False, f"Tampering detected at entry {index}."
            previous_hash = stored_hash
        return True, "Audit log is valid."
