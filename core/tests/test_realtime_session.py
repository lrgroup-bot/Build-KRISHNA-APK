import tempfile,unittest
from krishna_core.realtime_session import RealtimeSessionStore
class T(unittest.TestCase):
 def test_sequence_resume_and_dedupe(self):
  with tempfile.TemporaryDirectory() as d:
   s=RealtimeSessionStore(d);a=s.publish("p","x",{"a":1},"same");b=s.publish("p","x",{"a":2},"same")
   self.assertEqual(a["id"],b["id"]);c=s.publish("p","y",{});self.assertEqual([c],s.after("p",a["seq"]))
if __name__=="__main__":unittest.main()
