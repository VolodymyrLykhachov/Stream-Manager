import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from onvif_proxy.config import load_settings, pick_port


class PortTests(unittest.TestCase):
    def test_keeps_the_configured_port_when_free(self):
        self.assertEqual(pick_port(8554, (8564,), check=lambda port, host: True), 8554)

    def test_moves_to_the_first_free_fallback_when_taken(self):
        busy = {8554, 8564}
        self.assertEqual(pick_port(8554, (8564, 8574, 18554), check=lambda port, host: port not in busy), 8574)


class LogLevelTests(unittest.TestCase):
    def load_with_level(self, level: str | None) -> str:
        with tempfile.TemporaryDirectory() as folder:
            data_dir = Path(folder)
            if level is not None:
                (data_dir / "options.json").write_text(json.dumps({"log_level": level}), encoding="utf-8")
            with patch.dict(os.environ, {}, clear=True), patch("onvif_proxy.config.default_data_dir", return_value=data_dir):
                return load_settings().log_level

    def test_debug_level_is_configurable(self):
        self.assertEqual(self.load_with_level("debug"), "debug")

    def test_default_level_is_info(self):
        self.assertEqual(self.load_with_level(None), "info")

    def test_unknown_level_falls_back_to_info(self):
        self.assertEqual(self.load_with_level("verbose"), "info")


if __name__ == "__main__":
    unittest.main()
