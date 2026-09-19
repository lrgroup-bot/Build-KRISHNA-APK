import tempfile,unittest
from krishna_core.capability_approvals import CapabilityApprovals
class T(unittest.TestCase):
 def test_explicit_caps(self):
  with tempfile.NamedTemporaryFile() as f:
   a=CapabilityApprovals(f.name);a.approve("d",["chat","notify"]);a.require("d","chat")
   with self.assertRaises(PermissionError):a.require("d","system.run")
if __name__=="__main__":unittest.main()
