import unittest

from onvif_proxy.models import camera_from_dict
from onvif_proxy.rules import decide, matches, selected_source


def sample(**overrides):
    payload = {
        "name": "Printer cam",
        "listen_ip": "127.0.0.1",
        "enabled": True,
        "rules_enabled": True,
        "fallback_source_id": "still",
        "sources": [
            {"id": "live", "type": "rtsp", "name": "Live", "url": "rtsp://camera.example/live"},
            {"id": "still", "type": "image", "name": "Off", "image_url": "https://example.com/off.jpg"},
            {"id": "other", "type": "rtsp", "name": "Other", "url": "rtsp://camera.example/other"},
        ],
        "rules": [
            {"id": "r1", "entity_id": "switch.printer", "operator": "eq", "value": "on", "source_id": "live"},
            {"id": "r2", "entity_id": "sensor.temp", "operator": "gt", "value": "70", "source_id": "other"},
        ],
    }
    payload.update(overrides)
    return camera_from_dict(payload)


class RuleTests(unittest.TestCase):
    def test_first_match_wins(self):
        camera = sample()
        decision = decide(camera, {"switch.printer": "on", "sensor.temp": "90"})
        self.assertEqual(decision.source_id, "live")
        self.assertEqual(decision.rule_id, "r1")
        self.assertEqual(decision.reason, "rule")

    def test_later_rule_when_earlier_misses(self):
        camera = sample()
        decision = decide(camera, {"switch.printer": "off", "sensor.temp": "71"})
        self.assertEqual(decision.source_id, "other")
        self.assertEqual(selected_source(camera, decision).kind(), "stream")

    def test_fallback_when_nothing_matches(self):
        camera = sample()
        decision = decide(camera, {"switch.printer": "off", "sensor.temp": "10"})
        self.assertEqual(decision.reason, "fallback")
        self.assertEqual(decision.source_id, "still")
        self.assertEqual(selected_source(camera, decision).kind(), "image")

    def test_rules_disabled_uses_fallback_even_if_a_rule_would_match(self):
        camera = sample(rules_enabled=False)
        decision = decide(camera, {"switch.printer": "on"})
        self.assertEqual(decision.reason, "fallback")
        self.assertEqual(decision.source_id, "still")

    def test_missing_entity_does_not_match_and_state_change_switches_back(self):
        camera = sample()
        self.assertEqual(decide(camera, {}).reason, "fallback")
        on = decide(camera, {"switch.printer": "ON"})
        self.assertEqual(on.source_id, "live")
        off = decide(camera, {"switch.printer": "off"})
        self.assertEqual(off.source_id, "still")

    def test_numeric_unavailable_does_not_match(self):
        self.assertFalse(matches("gt", "70", "unavailable"))
        self.assertFalse(matches("lt", "70", "unknown"))
        self.assertTrue(matches("gt", "70", "70.5"))
        self.assertTrue(matches("lt", "70", "69"))
        self.assertFalse(matches("gt", "70", "70"))

    def test_disabled_camera(self):
        camera = sample(enabled=False)
        decision = decide(camera, {"switch.printer": "on"})
        self.assertEqual(decision.reason, "disabled")
        self.assertIsNone(decision.source_id)


if __name__ == "__main__":
    unittest.main()
