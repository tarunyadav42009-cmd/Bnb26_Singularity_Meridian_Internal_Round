"""Small regression suite for the QUORUM verification and audit core."""
import tempfile
import unittest
from pathlib import Path

from backend.audit.audit_log import AuditLog
from backend.core.quorum import evaluate_quorum as evaluate_core_quorum
from backend.verifier.verification import evaluate_quorum, verify_all


class VerificationTests(unittest.TestCase):
    def test_sample_attestations_verify(self):
        report = verify_all(2)
        self.assertEqual(report["decision"]["status"], "ACCEPT")
        self.assertEqual(report["decision"]["quorum"], 3)
        self.assertTrue(all(builder["verified"] for builder in report["builders"]))

    def test_quorum_requires_matching_verified_hashes(self):
        builders = [
            {"builder_id": "builder-a", "verified": True, "actual_hash": "same"},
            {"builder_id": "builder-b", "verified": True, "actual_hash": "same"},
            {"builder_id": "builder-c", "verified": True, "actual_hash": "different"},
        ]
        self.assertEqual(evaluate_quorum(builders, 2)["status"], "ACCEPT")
        self.assertEqual(evaluate_quorum(builders, 3)["status"], "REJECT")
        self.assertEqual(evaluate_quorum(builders, 2)["outliers"], ["builder-c"])

    def test_invalid_quorum_is_rejected(self):
        with self.assertRaises(ValueError):
            verify_all(0)
        with self.assertRaises(ValueError):
            verify_all(True)

    def test_legacy_core_quorum_does_not_accept_boolean_quorum(self):
        with self.assertRaises((ValueError, TypeError)):
            evaluate_core_quorum([], True)


class AuditTests(unittest.TestCase):
    def test_audit_chain_and_tamper_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "audit.log"
            audit = AuditLog(path)
            self.assertEqual(audit.verify()[0], True)
            audit.append("TEST_EVENT", {"status": "ACCEPT"})
            audit.append("SECOND_EVENT", {"count": 2})
            self.assertEqual(audit.verify()[0], True)
            rows = path.read_text(encoding="utf-8").splitlines()
            rows[0] = rows[0].replace("TEST_EVENT", "EDITED_EVENT")
            path.write_text("\n".join(rows) + "\n", encoding="utf-8")
            valid, message = audit.verify()
            self.assertFalse(valid)
            self.assertTrue("broken" in message.lower() or "tampering" in message.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
