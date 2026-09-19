import tempfile
import unittest
from pathlib import Path

from krishna_core.change_gate import ChangeGate
from krishna_core.shadow import ShadowWorkspaceManager
from krishna_core.integrations import IntegrationRegistry
from krishna_core.agent_runtime import EngineeringWorker


class MythosStackTests(unittest.TestCase):
    def test_change_gate_blocks_high_risk_without_confirmation(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "trade_router.py"
            path.write_text("print('x')\n", encoding="utf-8")
            gate = ChangeGate()
            result = gate.assess(
                str(path),
                caller_count=20,
                changed_lines=120,
                tests_present=False,
                external_risk="high",
                explicit_confirmation=False,
            )
            self.assertFalse(result["allowed"])
            self.assertEqual("high", result["risk"])

    def test_change_gate_allows_bounded_low_risk_change(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "helper.py"
            path.write_text("x=1\n", encoding="utf-8")
            gate = ChangeGate()
            digest = gate.file_hash(str(path))
            result = gate.assess(
                str(path),
                expected_hash=digest,
                caller_count=0,
                changed_lines=3,
                tests_present=True,
            )
            self.assertTrue(result["allowed"])

    def test_hash_mismatch_blocks_write(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "x.py"
            path.write_text("x=1\n", encoding="utf-8")
            result = ChangeGate().assess(str(path), expected_hash="deadbeef")
            self.assertFalse(result["allowed"])

    def test_shadow_workspace_is_disposable(self):
        with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as shadow:
            src = Path(td)
            (src / "hello.py").write_text("print('ok')\n", encoding="utf-8")
            mgr = ShadowWorkspaceManager(shadow)
            ws = mgr.create(str(src))
            self.assertTrue(Path(ws["path"]).exists())
            destroyed = mgr.destroy(ws["workspace_id"])
            self.assertTrue(destroyed["destroyed"])
            self.assertFalse(Path(ws["path"]).exists())

    def test_shadow_blocks_unapproved_executable(self):
        with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as shadow:
            src = Path(td)
            (src / "x.txt").write_text("x", encoding="utf-8")
            mgr = ShadowWorkspaceManager(shadow)
            ws = mgr.create(str(src))
            result = mgr.run(ws["workspace_id"], ["powershell", "-Command", "echo hi"])
            self.assertTrue(result["blocked"])
            mgr.destroy(ws["workspace_id"])

    def test_linear_worker_stops_on_failure(self):
        with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as shadow:
            src = Path(td)
            (src / "x.py").write_text("print('x')\n", encoding="utf-8")
            mgr = ShadowWorkspaceManager(shadow)
            worker = EngineeringWorker(mgr)
            result = worker.execute_plan(str(src), [
                ["python", "-c", "print('ok')"],
                ["python", "-c", "raise SystemExit(1)"],
                ["python", "-c", "print('should not run')"],
            ])
            self.assertFalse(result["all_passed"])
            self.assertEqual(2, len(result["steps"]))
            mgr.destroy(result["workspace"]["workspace_id"])

    def test_integration_registry_is_nonfatal_when_tools_missing(self):
        statuses = IntegrationRegistry().statuses()
        names = {x["name"] for x in statuses}
        self.assertIn("codebase_memory", names)
        self.assertIn("calm", names)
        self.assertIn("cua", names)
        self.assertIn("goose", names)


if __name__ == "__main__":
    unittest.main()
