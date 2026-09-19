import unittest
from pathlib import Path

class WebValidationTests(unittest.TestCase):
    def test_validation_ui_contains_real_core_workflows(self):
        root = Path(__file__).resolve().parents[1]
        text = (root / "web_validation.html").read_text(encoding="utf-8")
        for endpoint in (
            "/api/status", "/api/projects", "/api/core/chat",
            "/api/projects/index", "/api/investigate",
            "/api/browser/inspect", "/api/research/github",
        ):
            self.assertIn(endpoint, text)
        self.assertIn("Run full web check", text)

    def test_server_exposes_validation_route(self):
        root = Path(__file__).resolve().parents[1]
        text = (root / "krishna_core" / "server.py").read_text(encoding="utf-8")
        self.assertIn('"/web-test"', text)
        self.assertIn("WEB_VALIDATION", text)

if __name__ == "__main__":
    unittest.main()
