"""Render probe regressions with Helm and PyYAML; no Kubernetes cluster required."""
import os
from pathlib import Path
import subprocess
import unittest

import yaml

CHART = Path(os.environ.get("CHART_PATH", Path(__file__).resolve().parents[1] / "charts/verdaccio"))
HELM = os.environ.get("HELM", "helm")
PROBES = ("startupProbe", "livenessProbe", "readinessProbe")
WORKLOADS = ("deployment", "statefulset")


def render_container(workload, values):
    values = dict(values, type=workload)
    result = subprocess.run(
        [HELM, "template", "verdaccio", str(CHART), "--kube-version", "1.20.0", "-f", "-"],
        input=yaml.safe_dump(values), text=True, capture_output=True,
    )
    if result.returncode:
        raise AssertionError(result.stderr)
    kind = "StatefulSet" if workload == "statefulset" else "Deployment"
    document = next(doc for doc in yaml.safe_load_all(result.stdout) if doc and doc["kind"] == kind)
    return next(c for c in document["spec"]["template"]["spec"]["containers"]
                if c["name"] == "verdaccio")


class HealthProbes(unittest.TestCase):
    def test_defaults_protect_startup_and_allow_recovery_before_restart(self):
        for workload in WORKLOADS:
            with self.subTest(workload=workload):
                container = render_container(workload, {})
                startup, liveness, readiness = (container[name] for name in PROBES)
                self.assertGreaterEqual(startup["periodSeconds"] * startup["failureThreshold"], 300)
                self.assertEqual(startup["initialDelaySeconds"], 0)
                self.assertEqual(liveness["failureThreshold"], 6)
                self.assertEqual(readiness["failureThreshold"], 3)
                for probe in (startup, liveness, readiness):
                    self.assertEqual(probe["timeoutSeconds"], 5)
                    self.assertEqual(probe["httpGet"], {"path": "/-/ping", "port": "http"})
                    self.assertNotIn("enabled", probe)

    def test_each_probe_can_be_disabled_independently(self):
        for workload in WORKLOADS:
            for name in PROBES:
                with self.subTest(workload=workload, probe=name):
                    container = render_container(workload, {name: {"enabled": False}})
                    self.assertNotIn(name, container)
                    for other in PROBES:
                        if other != name:
                            self.assertIn(other, container)

    def test_all_probes_can_be_disabled(self):
        for workload in WORKLOADS:
            with self.subTest(workload=workload):
                container = render_container(workload, {name: {"enabled": False} for name in PROBES})
                self.assertTrue(all(name not in container for name in PROBES))

    def test_zero_initial_delay_is_preserved(self):
        for workload in WORKLOADS:
            with self.subTest(workload=workload):
                container = render_container(workload, {name: {"initialDelaySeconds": 0} for name in PROBES})
                for name in ("livenessProbe", "readinessProbe", "startupProbe"):
                    self.assertEqual(container[name]["initialDelaySeconds"], 0)

    def test_existing_timing_overrides_without_enabled_are_preserved(self):
        settings = {"initialDelaySeconds": 2, "periodSeconds": 7, "timeoutSeconds": 4,
                    "successThreshold": 1, "failureThreshold": 9}
        for workload in WORKLOADS:
            with self.subTest(workload=workload):
                values = {name: dict(settings) for name in PROBES}
                values["readinessProbe"]["successThreshold"] = 2
                container = render_container(workload, values)
                for name in PROBES:
                    for key, value in values[name].items():
                        self.assertEqual(container[name][key], value)

    def test_empty_or_missing_settings_keep_probes_enabled(self):
        # Null removes chart defaults, exercising fallback values for older releases.
        for workload in WORKLOADS:
            for settings in ({}, None):
                with self.subTest(workload=workload, settings=settings):
                    container = render_container(workload, {name: settings for name in PROBES})
                    self.assertGreaterEqual(container["startupProbe"]["failureThreshold"], 30)
                    self.assertGreater(container["livenessProbe"]["failureThreshold"],
                                       container["readinessProbe"]["failureThreshold"])
                    for name in PROBES:
                        self.assertEqual(container[name]["timeoutSeconds"], 5)


if __name__ == "__main__":
    unittest.main()
