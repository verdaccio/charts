"""Render regressions: python -m unittest discover -s tests (requires Helm and PyYAML)."""
import os
from pathlib import Path
import subprocess
import unittest

import yaml

CHART = Path(os.environ.get("CHART_PATH", Path(__file__).resolve().parents[1] / "charts/verdaccio"))
HELM = os.environ.get("HELM", "helm")


def render(values, extra_args=()):
    result = subprocess.run(
        [HELM, "template", "verdaccio", str(CHART), "-f", "-", *extra_args],
        input=yaml.safe_dump(values), text=True, capture_output=True,
    )
    if result.returncode:
        raise AssertionError(result.stderr)
    return {(doc["kind"], doc["metadata"]["name"]): doc
            for doc in yaml.safe_load_all(result.stdout) if doc}


class ChartTemplates(unittest.TestCase):
    def test_service_target_port(self):
        for nginx in (False, True):
            for target in (None, "", 4873, "4873", "custom-http"):
                with self.subTest(nginx=nginx, target=target):
                    values = {"cachingNginx": {"enabled": nginx}}
                    if target is not None:
                        values["service"] = {"targetPort": target}
                    service = render(values)[("Service", "verdaccio")]
                    expected = 4873 if target == "4873" else target
                    expected = expected or ("caching-nginx" if nginx else "http")
                    self.assertEqual(service["spec"]["ports"][0]["targetPort"], expected)

    def test_service_target_port_from_set_string(self):
        for nginx in (False, True):
            with self.subTest(nginx=nginx):
                service = render(
                    {"cachingNginx": {"enabled": nginx}},
                    extra_args=("--set-string", "service.targetPort=4873"),
                )[("Service", "verdaccio")]
                self.assertEqual(service["spec"]["ports"][0]["targetPort"], 4873)


if __name__ == "__main__":
    unittest.main()
