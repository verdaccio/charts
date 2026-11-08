"""Render regressions: python -m unittest discover -s tests (requires Helm and PyYAML)."""
import unittest

from helpers import render


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
