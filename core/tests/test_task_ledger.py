import tempfile,unittest
from pathlib import Path
from krishna_core.task_ledger import TaskLedger
class T(unittest.TestCase):
 def test_lifecycle(self):
  with tempfile.TemporaryDirectory() as td:
   l=TaskLedger(str(Path(td)/"tasks.db"))
   try:
    t=l.create("x","fix");self.assertEqual(t["status"],"queued")
    t=l.update(t["task_id"],"running","investigate",{"n":1});self.assertEqual(t["detail"]["n"],1)
   finally:l.close()
if __name__=="__main__":unittest.main()
