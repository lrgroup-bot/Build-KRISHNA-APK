import unittest

from krishna_core.identity import classify_compreface_response


class VisionIdentityTests(unittest.TestCase):
    def test_known_match(self):
        match = classify_compreface_response({
            "result": [{"subjects": [{"subject": "Alice", "similarity": 0.91}]}]
        }, 0.80, 0.65)
        self.assertEqual("KNOWN", match.state)
        self.assertEqual("Alice", match.subject)

    def test_possible_match(self):
        match = classify_compreface_response({
            "result": [{"subjects": [{"subject": "Bob", "similarity": 0.70}]}]
        }, 0.80, 0.65)
        self.assertEqual("POSSIBLE_MATCH", match.state)
        self.assertEqual("Bob", match.subject)

    def test_unknown(self):
        match = classify_compreface_response({
            "result": [{"subjects": [{"subject": "Carol", "similarity": 0.40}]}]
        }, 0.80, 0.65)
        self.assertEqual("UNKNOWN", match.state)
        self.assertIsNone(match.subject)

    def test_no_face(self):
        match = classify_compreface_response({"result": []})
        self.assertEqual("UNKNOWN", match.state)
        self.assertEqual(0, match.faces_detected)


if __name__ == "__main__":
    unittest.main()
