import tempfile,unittest
from krishna_core.graph_dataset import GraphDataset
class T(unittest.TestCase):
 def test_verified_only(self):
  with tempfile.TemporaryDirectory() as d:
   x=GraphDataset(d+"/g.jsonl")
   with self.assertRaises(PermissionError):x.append({"x":1},False)
   x.append({"x":1},True);self.assertEqual(x.load(),[{"x":1}])
if __name__=="__main__":unittest.main()
