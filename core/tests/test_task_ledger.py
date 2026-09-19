import tempfile,unittest
from krishna_core.task_ledger import TaskLedger
class T(unittest.TestCase):
 def test_lifecycle(self):
  with tempfile.NamedTemporaryFile() as f:
   l=TaskLedger(f.name);t=l.create("x","fix");self.assertEqual(t["status"],"queued")
   t=l.update(t["task_id"],"running","investigate",{"n":1});self.assertEqual(t["detail"]["n"],1)
if __name__=="__main__":unittest.main()
