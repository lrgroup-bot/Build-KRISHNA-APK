import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from hashlib import sha256
from tools.verify_source_manifest import verify_source_manifest

class SourceManifestGateTests(unittest.TestCase):
    def test_local_integrity_without_runtime_claim(self):
        with TemporaryDirectory() as folder:
            root=Path(folder);(root/"MainActivity.java").write_text("source",encoding="utf-8")
            record={"canonical_repository":"lrgroup-bot/KRISHNA-CORE",
                    "canonical_commit":"a"*40,
                    "file_hashes":{"MainActivity.java":sha256(b"source").hexdigest()}}
            result=verify_source_manifest(root,record)
            self.assertTrue(result["ok"])
            self.assertFalse(result["runtime_verified"])
    def test_traversal_is_rejected(self):
        with TemporaryDirectory() as folder:
            record={"canonical_repository":"lrgroup-bot/KRISHNA-CORE",
                    "canonical_commit":"a"*40,
                    "file_hashes":{"../outside":"a"*64}}
            result=verify_source_manifest(folder,record)
            self.assertFalse(result["ok"])
            self.assertIn("path_outside_source_root",result["errors"])
if __name__=="__main__":unittest.main()
