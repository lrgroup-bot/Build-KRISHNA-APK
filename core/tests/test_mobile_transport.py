import tempfile,unittest
from pathlib import Path
from krishna_core.device_pairing import DevicePairingStore
from krishna_core.realtime_session import RealtimeSessionStore
from krishna_core.mobile_transport import MobileTransport
class Gateway:
 def __init__(self,p):self.pairing=p;self.calls=0
 def call(self,d,t,m,p):self.calls+=1;return {"calls":self.calls}
class T(unittest.TestCase):
 def test_duplicate_command_executes_once(self):
  with tempfile.TemporaryDirectory() as d:
   p=DevicePairingStore(d);r=p.request("d","phone");token=p.approve(r["request_id"])["token"]
   g=Gateway(p);t=MobileTransport(g,RealtimeSessionStore(d))
   a=t.command("d",token,"m1","chat.send",{});b=t.command("d",token,"m1","chat.send",{})
   self.assertEqual(a,b);self.assertEqual(g.calls,1)
if __name__=="__main__":unittest.main()
