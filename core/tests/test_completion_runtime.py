import unittest
from krishna_core.completion_runtime import CompletionRuntime
class T(unittest.TestCase):
 def test_only_verified_emits(self):
  r=CompletionRuntime();self.assertIsNone(r.event("x",{"verified":False}))
  self.assertEqual(r.event("x",{"verified":True,"promotable":True})["type"],"task.verified")
if __name__=="__main__":unittest.main()
