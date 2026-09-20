import tempfile, unittest
from pathlib import Path
from unittest.mock import Mock
from core.krishna_core.development_operator import DevelopmentOperator
from core.krishna_core.plugin_runtime import PluginRegistry
from core.krishna_core.plugin_executor import PluginExecutor
from core.krishna_core.runtime_deployer import RuntimeDeployer

class CompletionSafetyTests(unittest.TestCase):
    def test_development_stage_rejects_escape(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/"project"; root.mkdir()
            op=DevelopmentOperator(Mock())
            with self.assertRaises(ValueError):op.stage(root,[{"path":"../escape.txt","content":"x"}])

    def test_api_expectations_are_specific(self):
        net=[{"url":"http://localhost/api/status","status":200,"method":"GET"}]
        rows=DevelopmentOperator._match_api_expectations(net,[{"path":"/api/status","method":"GET","statuses":[200]},{"path":"/api/projects","statuses":[200]}])
        self.assertTrue(rows[0]["ok"]); self.assertFalse(rows[1]["ok"])

    def test_disabled_plugin_cannot_execute(self):
        with tempfile.TemporaryDirectory() as td:
            reg=PluginRegistry(td)
            reg.add({"id":"demo-http","name":"Demo","kind":"http","endpoint":"https://example.invalid","enabled":False})
            with self.assertRaises(PermissionError):PluginExecutor(reg).execute("demo-http","KRISHNA")

    def test_runtime_deployer_blocks_state(self):
        with tempfile.TemporaryDirectory() as td:
            source=Path(td)/"src"; runtime=Path(td)/"runtime"; backups=Path(td)/"backups"
            source.mkdir(); runtime.mkdir(); (source/".git").mkdir()
            (source/"state").mkdir(); (source/"state"/"x").write_text("x")
            dep=RuntimeDeployer(backups)
            with self.assertRaises(PermissionError):dep.deploy(source,runtime,["state/x"])

if __name__=="__main__":unittest.main()
