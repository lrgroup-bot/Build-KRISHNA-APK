from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[1]
WEB=ROOT/"core"/"web_validation.html"

class WebIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text=WEB.read_text(encoding="utf-8")

    def test_single_required_ids(self):
        for element_id in ("home","sudarshan","projects","garuda","plugins","specialists","development","work","activity","system","messages","project"):
            needle=f'id="{element_id}"'
            self.assertEqual(self.text.count(needle),1,needle)

    def test_no_literal_escape_artifacts(self):
        self.assertNotIn("showView(\\'",self.text)
        self.assertNotIn("</section>\\n<section",self.text)

    def test_sudarshan_has_complete_spatial_deck(self):
        start=self.text.index('<section id="sudarshan"')
        end=self.text.index('<section id="projects"',start)
        block=self.text[start:end]
        self.assertIn('holoRail left',block)
        self.assertIn('sudarshanCenter',block)
        self.assertIn('holoRail right',block)
        self.assertEqual(block.count("</aside>"),2)
        self.assertIn('id="messages"',block)

    def test_referenced_dom_ids_exist(self):
        ids=set(re.findall(r'id="([^"]+)"',self.text))
        refs=set(re.findall(r"\$\('([^']+)'\)",self.text))
        missing=sorted(refs-ids)
        self.assertEqual(missing,[],missing)

    def test_no_known_undefined_escape_helper(self):
        self.assertNotRegex(self.text,r"(?<![A-Za-z])esc\(")

    def test_attachment_control_present(self):
        self.assertIn('id="attachInput"',self.text)
        self.assertIn('uploadAttachment(this)',self.text)

if __name__=="__main__":
    unittest.main()
