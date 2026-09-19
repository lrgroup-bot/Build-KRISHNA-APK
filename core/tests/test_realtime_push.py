import tempfile,unittest
from krishna_core.realtime_session import RealtimeSessionStore
from krishna_core.realtime_push import RealtimePush
class T(unittest.TestCase):
 def test_returns_event(self):
  with tempfile.TemporaryDirectory() as d:
   s=RealtimeSessionStore(d);s.publish("d","task.verified",{"ok":True})
   self.assertEqual(RealtimePush(s).wait("d",0,.1)[0]["type"],"task.verified")
if __name__=="__main__":unittest.main()
