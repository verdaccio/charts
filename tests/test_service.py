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
    def test_service_target_port(self):
        for nginx in (False, True):
            for target in ("", 4873, "custom-http"):
                with self.subTest(nginx=nginx, target=target):
                    service = render({"cachingNginx": {"enabled": nginx}, "service": {"targetPort": target}})["Service"]
                    expected = target or ("caching-nginx" if nginx else "http")
                    self.assertEqual(service["spec"]["ports"][0]["targetPort"], expected)


if __name__ == "__main__":
    unittest.main()
