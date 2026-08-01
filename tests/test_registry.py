from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from skillhub import registry
from skillhub.paths import get_registry_path
from skillhub.syncer import doctor


class RegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"SKILLHUB_HOME": self.temp_dir.name})
        self.env.start()
        registry.init_db()

    def tearDown(self) -> None:
        self.env.stop()
        self.temp_dir.cleanup()

    def test_registry_round_trip_uses_isolated_sqlite_file(self) -> None:
        registry.add_skill("demo", "Demo", "1.0.0", "skill", "Example")

        skill = registry.get_skill("demo")

        self.assertEqual(skill["name"], "Demo")
        self.assertEqual(
            Path(get_registry_path()).resolve(),
            (Path(self.temp_dir.name) / "registry.db").resolve(),
        )

    def test_doctor_reports_missing_canonical_skill(self) -> None:
        registry.add_skill("missing", "Missing", "1.0.0", "skill")

        issues = doctor()

        self.assertEqual(issues[0]["type"], "missing_canonical")


if __name__ == "__main__":
    unittest.main()
