import importlib.util
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "generate_catalog.py"
SPEC = importlib.util.spec_from_file_location("generate_catalog", MODULE_PATH)
assert SPEC and SPEC.loader
generator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(generator)


class GenerateCatalogTests(unittest.TestCase):
    def test_parses_company_and_uuid_entries(self):
        companies = generator.parse_companies(
            """
company_identifiers:
  - value: 0x004C
    name: 'Apple, Inc.'
"""
        )
        uuids = generator.parse_uuid_entries(
            """
uuids:
 - uuid: 0x180D
   name: Heart Rate
   id: org.bluetooth.service.heart_rate
"""
        )

        self.assertEqual(companies, {"004C": "Apple, Inc."})
        self.assertEqual(uuids["180D"]["name"], "Heart Rate")
        self.assertEqual(
            uuids["180D"]["identifier"],
            "org.bluetooth.service.heart_rate",
        )

    def test_flattens_appearance_category_and_subcategory(self):
        appearances = generator.parse_appearances(
            """
appearance_values:
 - category: 0x001
   name: Phone
 - category: 0x002
   name: Computer
   subcategory:
    - value: 0x01
      name: Desktop Workstation
"""
        )

        self.assertEqual(appearances["0040"]["category"], "Phone")
        self.assertIsNone(appearances["0040"]["subcategory"])
        self.assertEqual(appearances["0081"]["subcategory"], "Desktop Workstation")

    def test_semantic_payload_ignores_snapshot_date_only(self):
        left = {"generatedAt": "2026-07-10", "entries": {"004C": "Apple"}}
        right = {"generatedAt": "2026-07-17", "entries": {"004C": "Apple"}}
        self.assertEqual(
            generator.semantic_payload(left),
            generator.semantic_payload(right),
        )

    def test_read_existing_returns_none_for_missing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertIsNone(generator.read_existing(Path(directory) / "missing.json"))


if __name__ == "__main__":
    unittest.main()
