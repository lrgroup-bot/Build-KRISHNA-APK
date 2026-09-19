import tempfile,unittest
from pathlib import Path
from krishna_core.promotion_runtime import PromotionRuntime
class T(unittest.TestCase):
 def test_requires_verification_and_promotes(self):
  with tempfile.TemporaryDirectory() as s,tempfile.TemporaryDirectory() as w:
   Path(s,"a.txt").write_text("new")
   Path(w,"a.txt").write_text("old")
   p=PromotionRuntime()
   with self.assertRaises(PermissionError):p.promote(s,w,["a.txt"],False)
   r=p.promote(s,w,["a.txt"],True);self.assertEqual(Path(w,"a.txt").read_text(),"new")
   p.rollback(w,r["backup"],["a.txt"]);self.assertEqual(Path(w,"a.txt").read_text(),"old")
if __name__=="__main__":unittest.main()
