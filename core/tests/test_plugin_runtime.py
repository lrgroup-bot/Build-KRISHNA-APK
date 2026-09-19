import tempfile
import unittest
from pathlib import Path
from krishna_core.plugin_runtime import PluginRegistry

class PluginRegistryTests(unittest.TestCase):
    def test_builtin_and_arbitrary_plugin_lifecycle(self):
        with tempfile.TemporaryDirectory() as td:
            r=PluginRegistry(Path(td))
            ids={p["id"] for p in r.list()}
            self.assertIn("pc",ids); self.assertIn("github",ids)
            added=r.add({"name":"My Tool","kind":"mcp","permissions":["read"],"project_scope":["*"]})
            self.assertEqual(added["id"],"my-tool")
            self.assertFalse(added["enabled"])
            self.assertTrue(r.set_enabled("my-tool",True)["enabled"])
            self.assertTrue(r.remove("my-tool"))

    def test_builtin_cannot_be_removed(self):
        with tempfile.TemporaryDirectory() as td:
            r=PluginRegistry(Path(td))
            with self.assertRaises(PermissionError):
                r.remove("pc")

if __name__=="__main__":
    unittest.main()
