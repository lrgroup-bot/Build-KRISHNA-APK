import tempfile
import unittest
from pathlib import Path

from krishna_core.memory import MemoryStore
from krishna_core.project_graph import ProjectGraph
from krishna_core.investigator import EvidenceEngine, InvestigationEngine, Evidence
from krishna_core.verification import VerificationEngine
from krishna_core.recovery import RecoveryEngine
from krishna_core.knowledge import KnowledgeIngestor
from krishna_core.security import DefensiveSecurityScanner


class KrishnaCapabilityTests(unittest.TestCase):
    def test_project_graph_relevant(self):
        graph = ProjectGraph()
        graph.upsert_node("api", "service")
        graph.upsert_node("db", "database")
        graph.link("api", "db")
        snap = graph.relevant(["api"])
        self.assertEqual(2, len(snap["nodes"]))

    def test_evidence_investigation(self):
        engine = EvidenceEngine()
        engine.register_probe("health", lambda ctx: [Evidence("health", "service", "ollama down")])
        report = InvestigationEngine(engine).investigate("connection refused")
        self.assertEqual("evidence_collected", report["status"])
        self.assertTrue(report["hypotheses"])

    def test_verification_requires_all_checks(self):
        result = VerificationEngine().run([
            ("one", lambda: (True, "ok")),
            ("two", lambda: (False, "bad")),
        ])
        self.assertFalse(result["verified"])
        self.assertEqual(1, result["failed"])

    def test_recovery_blocks_mutation_by_default(self):
        engine = RecoveryEngine(False)
        engine.register("deploy", lambda payload: {"ok": True})
        result = engine.execute("deploy")
        self.assertTrue(result["blocked"])
        self.assertFalse(result["executed"])

    def test_knowledge_deduplicates(self):
        with tempfile.TemporaryDirectory() as td:
            store = MemoryStore(str(Path(td) / "test.db"))
            ingestor = KnowledgeIngestor(store, max_chunk_chars=500)
            first = ingestor.ingest("p", "web", "hello world")
            second = ingestor.ingest("p", "web", "hello world")
            self.assertEqual(1, first["written"])
            self.assertEqual(0, second["written"])

    def test_security_scanner_finds_risky_execution(self):
        findings = DefensiveSecurityScanner().scan_text("x.py", "import os\nos.system('echo x')\n")
        self.assertTrue(any(f["rule"] == "os_system" for f in findings))


if __name__ == "__main__":
    unittest.main()
