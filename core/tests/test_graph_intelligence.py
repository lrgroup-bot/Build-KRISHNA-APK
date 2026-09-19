import unittest
from krishna_core.project_graph import ProjectGraph
from krishna_core.graph_intelligence import GraphIntelligence
class T(unittest.TestCase):
 def test_dependency_signal_propagates(self):
  g=ProjectGraph();g.upsert_node("api.py","file");g.upsert_node("db.py","file");g.upsert_node("ui.js","file")
  g.link("api.py","db.py","depends_on");g.link("ui.js","api.py","calls")
  r=GraphIntelligence(g).rank(["api.py error"],hops=2)
  names=[x["node"] for x in r["ranked"]]
  self.assertIn("api.py",names);self.assertIn("db.py",names);self.assertIn("ui.js",names)
  self.assertFalse(r["authoritative"])
if __name__=="__main__":unittest.main()
