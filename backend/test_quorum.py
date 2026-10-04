"""Regression tests for QUORUM's quorum and audit core."""
import tempfile
import unittest
from pathlib import Path

from backend.audit.audit_log import AuditLog
from backend.core.quorum import evaluate_quorum


class QuorumTests(unittest.TestCase):
    def test_two_of_three_accepts(self):
        builders = [
            {"builder_id": "builder-a", "verified": True, "artifact_hash": "same"},
            {"builder_id": "builder-b", "verified": True, "artifact_hash": "same"},
            {"builder_id": "builder-c", "verified": False, "artifact_hash": None},
        ]
        decision = evaluate_quorum(builders, 2)
        self.assertEqual(decision["status"], "ACCEPT")
        self.assertEqual(decision["quorum"], 2)
        self.assertEqual(decision["winning_group"], ["builder-a", "builder-b"])

    def test_one_of_three_rejects(self):
        builders = [
            {"builder_id": "builder-a", "verified": True, "artifact_hash": "same"},
            {"builder_id": "builder-b", "verified": False, "artifact_hash": None},
            {"builder_id": "builder-c", "verified": False, "artifact_hash": None},
        ]
        decision = evaluate_quorum(builders, 2)
        self.assertEqual(decision["status"], "REJECT")
        self.assertEqual(decision["quorum"], 1)

    def test_three_matching_verified_builders_accept(self):
        builders = [
            {"builder_id": "builder-a", "verified": True, "artifact_hash": "same"},
            {"builder_id": "builder-b", "verified": True, "artifact_hash": "same"},
            {"builder_id": "builder-c", "verified": True, "artifact_hash": "same"},
        ]
        decision = evaluate_quorum(builders, 2)
        self.assertEqual(decision["status"], "ACCEPT")
        self.assertEqual(decision["quorum"], 3)

    def test_outlier_is_reported(self):
        builders = [
            {"builder_id": "builder-a", "verified": True, "artifact_hash": "same"},
            {"builder_id": "builder-b", "verified": True, "artifact_hash": "same"},
            {"builder_id": "builder-c", "verified": True, "artifact_hash": "different"},
        ]
        decision = evaluate_quorum(builders, 2)
        self.assertEqual(decision["status"], "ACCEPT")
        self.assertEqual(decision["outliers"], ["builder-c"])


class AuditTests(unittest.TestCase):
    def test_audit_chain_and_tamper_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "audit.log"
            audit = AuditLog(path)
            self.assertTrue(audit.verify()[0])
            audit.append("TEST_EVENT", {"status": "ACCEPT"})
            audit.append("SECOND_EVENT", {"count": 2})
            self.assertTrue(audit.verify()[0])
            rows = path.read_text(encoding="utf-8").splitlines()
            rows[0] = rows[0].replace("TEST_EVENT", "EDITED_EVENT")
            path.write_text("\n".join(rows) + "\n", encoding="utf-8")
            valid, message = audit.verify()
            self.assertFalse(valid)
            self.assertTrue("broken" in message.lower() or "tampering" in message.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
