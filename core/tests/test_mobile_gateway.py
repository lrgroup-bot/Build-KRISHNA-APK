import tempfile, unittest
from krishna_core.device_pairing import DevicePairingStore
from krishna_core.mobile_gateway import MobileGateway
from krishna_core.mobile_rpc import MobileRPC

class GatewayTest(unittest.TestCase):
    def test_pair_auth_and_rpc_allowlist(self):
        with tempfile.TemporaryDirectory() as d:
            store=DevicePairingStore(d)
            req=store.request("phone-1","KRISHNA Mobile")
            auth=store.approve(req["request_id"])
            gw=MobileGateway(store,MobileRPC({"chat.send":lambda p:{"echo":p["text"]}}))
            self.assertEqual(gw.call("phone-1",auth["token"],"chat.send",{"text":"hi"})["echo"],"hi")
            with self.assertRaises(PermissionError): gw.call("phone-1",auth["token"],"system.run",{"cmd":"whoami"})
            with self.assertRaises(PermissionError): gw.call("phone-1","bad","chat.send",{"text":"x"})
if __name__=="__main__": unittest.main()
