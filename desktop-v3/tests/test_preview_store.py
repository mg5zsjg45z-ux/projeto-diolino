import importlib.util
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("preview_store", Path(__file__).resolve().parents[1] / "preview_store.py")
store = importlib.util.module_from_spec(spec)
spec.loader.exec_module(store)

class PreviewStoreTests(unittest.TestCase):
    def test_roundtrip_import_and_backup(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "preview.sqlite3"
            key = "diolino-habits-v1"
            self.assertTrue(store.import_if_absent(key, [], path))
            self.assertFalse(store.import_if_absent(key, [1], path))
            self.assertEqual(store.get(key, path), [])
            store.put(key, [{"name": "Teste"}], path)
            copy = store.backup(path)
            self.assertEqual(store.get(key, copy), [{"name": "Teste"}])
    def test_reject_unknown_key(self):
        with self.assertRaises(ValueError):
            store.get("unknown")

if __name__ == "__main__":
    unittest.main()
