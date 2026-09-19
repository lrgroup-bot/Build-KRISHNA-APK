import tempfile, unittest
from pathlib import Path
from krishna_core.specialist_library import SpecialistLibrary

class SpecialistLibraryTests(unittest.TestCase):
    def test_indexes_and_selects_prompt_only_specialists(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/"agency"; (root/"engineering").mkdir(parents=True); (root/"testing").mkdir()
            (root/"engineering"/"backend.md").write_text("---\nname: Backend Architect\ndescription: APIs databases Python services\n---\n# Backend\n",encoding="utf-8")
            (root/"testing"/"reality.md").write_text("---\nname: Reality Checker\ndescription: Verify evidence tests production readiness\n---\n# Verify\n",encoding="utf-8")
            lib=SpecialistLibrary(Path(td)/"state",root); status=lib.index()
            self.assertEqual(status["total"],2)
            chosen=lib.select("fix Python API code and verify tests",5)
            self.assertTrue(any(x["name"]=="Backend Architect" for x in chosen))
            self.assertTrue(any(x["name"]=="Reality Checker" for x in chosen))
            ctx=lib.context("engineering/backend")
            self.assertIn("# Backend",ctx["instructions"])

if __name__=="__main__": unittest.main()
