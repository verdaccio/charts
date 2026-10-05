"""Render regressions: python -m unittest discover -s tests (requires Helm and PyYAML)."""
import os
from pathlib import Path
import subprocess
import unittest

import yaml

CHART = Path(os.environ.get("CHART_PATH", Path(__file__).resolve().parents[1] / "charts/verdaccio"))
HELM = os.environ.get("HELM", "helm")


def render(values, kube_version="1.19.0"):
    result = subprocess.run(
        [HELM, "template", "verdaccio", str(CHART), "--kube-version", kube_version, "-f", "-"],
        input=yaml.safe_dump(values), text=True, capture_output=True,
    )
    if result.returncode:
        raise AssertionError(result.stderr)
    return {doc["kind"]: doc for doc in yaml.safe_load_all(result.stdout) if doc}


def container(documents, workload):
    kind = "StatefulSet" if workload == "statefulset" else "Deployment"
    return next(c for c in documents[kind]["spec"]["template"]["spec"]["containers"]
                if c["name"] == "verdaccio")


class ChartTemplates(unittest.TestCase):
    def test_extra_environment_preserves_port_and_renders_templates(self):
        for workload in ("deployment", "statefulset"):
            for extra in ([], [
                {"name": "VERDACCIO_PUBLIC_URL", "value": "https://{{ .Release.Name }}.example.com"},
                {"name": "TOKEN", "valueFrom": {"secretKeyRef": {
                    "name": "{{ .Release.Name }}-credentials", "key": "token"}}},
            ]):
                with self.subTest(workload=workload, extra=extra):
                    env = container(render({"type": workload, "extraEnvVars": extra}), workload)["env"]
                    ports = [e for e in env if e["name"] == "VERDACCIO_PORT"]
                    self.assertEqual(ports, [{"name": "VERDACCIO_PORT", "value": "4873"}])
                    if extra:
                        self.assertIn({"name": "VERDACCIO_PUBLIC_URL", "value": "https://verdaccio.example.com"}, env)
                        self.assertIn({"name": "TOKEN", "valueFrom": {"secretKeyRef": {
                            "name": "verdaccio-credentials", "key": "token"}}}, env)


    def test_explicit_port_is_not_duplicated(self):
        for workload in ("deployment", "statefulset"):
            for port in ({"value": "5000"}, {"valueFrom": {"configMapKeyRef": {"name": "ports", "key": "http"}}}):
                with self.subTest(workload=workload, port=port):
                    extra = [{"name": "VERDACCIO_PORT", **port}]
                    env = container(render({"type": workload, "extraEnvVars": extra}), workload)["env"]
                    self.assertEqual(env, extra)


if __name__ == "__main__":
    unittest.main()
