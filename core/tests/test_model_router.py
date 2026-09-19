import unittest
from unittest.mock import patch
from krishna_core.model_router import ModelRequest, ModelRouter

class Fake:
    def __init__(self,name,value=None,error=None): self.name=name; self.value=value; self.error=error
    def complete(self,req):
        if self.error: raise self.error
        return self.value

class RouterTests(unittest.TestCase):
    def test_fallback_is_local_and_ordered(self):
        r=ModelRouter(); r.providers=[Fake("ollama",error=RuntimeError("down")),Fake("gpt4all","ok")]
        self.assertEqual(r.complete(ModelRequest("x")),{"provider":"gpt4all","content":"ok"})

if __name__=="__main__": unittest.main()
