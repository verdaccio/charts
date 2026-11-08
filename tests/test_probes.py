"""Render probe regressions for Deployment and StatefulSet (requires Helm and PyYAML)."""
import unittest

from helpers import container, render

PROBES = ("startupProbe", "livenessProbe", "readinessProbe")
WORKLOADS = ("deployment", "statefulset")
STARTUP_ON = {"startupProbe": {"enabled": True}}


def render_container(workload, values):
    return container(render(dict(values, type=workload)), workload)


class HealthProbes(unittest.TestCase):
    def test_defaults_allow_recovery_before_restart_without_startup_probe(self):
        for workload in WORKLOADS:
            with self.subTest(workload=workload):
                rendered = render_container(workload, {})
                self.assertNotIn("startupProbe", rendered)
                liveness, readiness = rendered["livenessProbe"], rendered["readinessProbe"]
                self.assertEqual(liveness["failureThreshold"], 6)
                self.assertEqual(readiness["failureThreshold"], 3)
                for probe in (liveness, readiness):
                    self.assertEqual(probe["timeoutSeconds"], 5)
                    self.assertEqual(probe["initialDelaySeconds"], 5)
                    self.assertEqual(probe["httpGet"], {"path": "/-/ping", "port": "http"})
                    self.assertNotIn("enabled", probe)

    def test_startup_probe_is_opt_in_and_covers_five_minutes(self):
        for workload in WORKLOADS:
            with self.subTest(workload=workload):
                startup = render_container(workload, STARTUP_ON)["startupProbe"]
                self.assertGreaterEqual(startup["periodSeconds"] * startup["failureThreshold"], 300)
                self.assertEqual(startup["initialDelaySeconds"], 0)
                self.assertEqual(startup["timeoutSeconds"], 5)
                self.assertNotIn("enabled", startup)
                # Timing overrides alone do not enable it.
                self.assertNotIn("startupProbe",
                                 render_container(workload, {"startupProbe": {"failureThreshold": 60}}))

    def test_each_probe_can_be_disabled_independently(self):
        for workload in WORKLOADS:
            for name in PROBES:
                with self.subTest(workload=workload, probe=name):
                    rendered = render_container(workload, {**STARTUP_ON, name: {"enabled": False}})
                    self.assertNotIn(name, rendered)
                    for other in PROBES:
                        if other != name:
                            self.assertIn(other, rendered)

    def test_all_probes_can_be_disabled(self):
        for workload in WORKLOADS:
            with self.subTest(workload=workload):
                rendered = render_container(workload, {name: {"enabled": False} for name in PROBES})
                self.assertTrue(all(name not in rendered for name in PROBES))

    def test_zero_initial_delay_is_preserved(self):
        values = {name: {"initialDelaySeconds": 0} for name in PROBES}
        values["startupProbe"]["enabled"] = True
        for workload in WORKLOADS:
            with self.subTest(workload=workload):
                rendered = render_container(workload, values)
                for name in PROBES:
                    self.assertEqual(rendered[name]["initialDelaySeconds"], 0)

    def test_existing_timing_overrides_without_enabled_are_preserved(self):
        settings = {"initialDelaySeconds": 2, "periodSeconds": 7, "timeoutSeconds": 4,
                    "successThreshold": 1, "failureThreshold": 9}
        values = {name: dict(settings) for name in ("livenessProbe", "readinessProbe")}
        values["readinessProbe"]["successThreshold"] = 2
        values["startupProbe"] = dict(settings, enabled=True)
        for workload in WORKLOADS:
            with self.subTest(workload=workload):
                rendered = render_container(workload, values)
                for name in PROBES:
                    for key, value in settings.items():
                        self.assertEqual(rendered[name][key], values[name][key])

    def test_empty_or_missing_settings_keep_defaults(self):
        # Null removes chart defaults, exercising fallback values for older releases.
        for workload in WORKLOADS:
            for settings in ({}, None):
                with self.subTest(workload=workload, settings=settings):
                    rendered = render_container(workload, {name: settings for name in PROBES})
                    self.assertNotIn("startupProbe", rendered)
                    self.assertGreater(rendered["livenessProbe"]["failureThreshold"],
                                       rendered["readinessProbe"]["failureThreshold"])
                    for name in ("livenessProbe", "readinessProbe"):
                        self.assertEqual(rendered[name]["timeoutSeconds"], 5)


if __name__ == "__main__":
    unittest.main()
