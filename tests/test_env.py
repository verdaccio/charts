"""Render regressions for extra environment variables and the default port."""
import unittest

from helpers import container, render


class EnvironmentVariables(unittest.TestCase):
    def test_default_port_survives_extra_environment(self):
        cases = (
            {},
            {"extraEnvVars": []},
            {"extraEnvVars": None},
            {"extraEnvVars": [{"name": "CUSTOM_VAR", "value": "test"}]},
        )
        for workload in ("deployment", "statefulset"):
            for overrides in cases:
                with self.subTest(workload=workload, overrides=overrides):
                    env = container(render({"type": workload, **overrides}), workload)["env"]
                    expected = [{"name": "VERDACCIO_PORT", "value": "4873"}]
                    expected.extend(overrides.get("extraEnvVars") or [])
                    self.assertEqual(env, expected)

    def test_environment_templates_use_chart_context(self):
        for workload in ("deployment", "statefulset"):
            with self.subTest(workload=workload):
                docs = render({
                    "type": workload,
                    "service": {"port": 5080},
                    "extraEnvVars": [
                        {"name": "VERDACCIO_PUBLIC_URL", "value": "https://{{ .Release.Name }}.example.com"},
                        {"name": "PORT_ALIAS", "value": "{{ .Values.service.port }}"},
                        {"name": "TOKEN", "valueFrom": {"secretKeyRef": {
                            "name": '{{ include "verdaccio.fullname" . }}-credentials',
                            "key": "{{ .Chart.Name }}-token",
                        }}},
                    ],
                })
                self.assertEqual(container(docs, workload)["env"], [
                    {"name": "VERDACCIO_PORT", "value": "4873"},
                    {"name": "VERDACCIO_PUBLIC_URL", "value": "https://verdaccio.example.com"},
                    {"name": "PORT_ALIAS", "value": "5080"},
                    {"name": "TOKEN", "valueFrom": {"secretKeyRef": {
                        "name": "verdaccio-credentials", "key": "verdaccio-token",
                    }}},
                ])

    def test_explicit_port_is_rendered_without_duplicates(self):
        cases = (
            ({"name": "VERDACCIO_PORT", "value": "5000"},
             {"name": "VERDACCIO_PORT", "value": "5000"}),
            ({"name": "VERDACCIO_PORT", "valueFrom": {
                "configMapKeyRef": {"name": "ports", "key": "http"}}},
             {"name": "VERDACCIO_PORT", "valueFrom": {
                "configMapKeyRef": {"name": "ports", "key": "http"}}}),
            ({"name": "VERDACCIO_PORT", "value": "{{ .Values.service.port }}"},
             {"name": "VERDACCIO_PORT", "value": "5080"}),
            ({"name": '{{ printf "VERDACCIO_%s" "PORT" }}', "value": "5000"},
             {"name": "VERDACCIO_PORT", "value": "5000"}),
        )
        for workload in ("deployment", "statefulset"):
            for extra, expected in cases:
                with self.subTest(workload=workload, extra=extra):
                    docs = render({"type": workload, "service": {"port": 5080}, "extraEnvVars": [extra]})
                    self.assertEqual(container(docs, workload)["env"], [expected])


if __name__ == "__main__":
    unittest.main()
