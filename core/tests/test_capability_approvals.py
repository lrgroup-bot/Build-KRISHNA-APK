import tempfile,unittest
from pathlib import Path
from krishna_core.capability_approvals import CapabilityApprovals
class T(unittest.TestCase):
 def test_explicit_caps(self):
  with tempfile.TemporaryDirectory() as td:
   a=CapabilityApprovals(str(Path(td)/"caps.db"));a.approve("d",["chat","notify"]);a.require("d","chat")
   with self.assertRaises(PermissionError):a.require("d","system.run")
   a.close()
if __name__=="__main__":unittest.main()
