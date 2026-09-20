from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
MEM=(ROOT/"core"/"krishna_core"/"memory.py").read_text(encoding="utf-8")
ORCH=(ROOT/"core"/"krishna_core"/"orchestrator.py").read_text(encoding="utf-8")
SERVER=(ROOT/"core"/"krishna_core"/"server.py").read_text(encoding="utf-8")
WEB=(ROOT/"core"/"web_validation.html").read_text(encoding="utf-8")
class GyanAvatarContractTests(unittest.TestCase):
    def test_learning_schema_and_api(self):
        self.assertIn("CREATE TABLE IF NOT EXISTS learnings",MEM)
        self.assertIn("def learn(",MEM); self.assertIn("def learnings(",MEM)
        self.assertIn("GyanBhandarAgent",ORCH)
        self.assertIn('/api/gyan-bhandar',SERVER)
        self.assertIn('/api/gyan-bhandar/strengthen',SERVER)
    def test_krishna_remains_authority(self):
        g=(ROOT/"core"/"krishna_core"/"gyan_bhandar.py").read_text(encoding="utf-8")
        self.assertIn('"decision_authority":"KRISHNA"',g)
        self.assertIn('"auto_implementation":False',g)
        self.assertIn('"implementation_executor":"Sudarshan"',g)
    def test_private_avatar_is_local_route(self):
        self.assertIn('/api/avatar.glb',SERVER)
        self.assertIn('dashboard" / "assets" / "avatar" / "krishna.glb"',SERVER)
        self.assertIn('src="/api/avatar.glb"',WEB)
        self.assertIn('id="krishnaModel"',WEB)
    def test_gyan_ui_contract(self):
        self.assertIn('id="gyan"',WEB)
        self.assertIn('Gyan-Bhandar',WEB)
        self.assertIn('strengthenGyan()',WEB)
if __name__=="__main__":unittest.main()
