"""Regressions for configurable ingress path types (issue #145)."""
import unittest

from helpers import render


class IngressPathTypes(unittest.TestCase):
    def test_configurable_path_types_with_and_without_hosts(self):
        for version in ("1.18.0", "1.19.0"):
            for hosts in ([], ["{{ .Release.Name }}.example.com", "other.example.com"]):
                for path_type in ("Prefix", "Exact", "ImplementationSpecific"):
                    with self.subTest(version=version, hosts=hosts, path_type=path_type):
                        ingress = render({"ingress": {
                            "enabled": True, "hosts": hosts,
                            "paths": ["/*", "/registry"], "pathType": path_type,
                        }}, extra_args=("--kube-version", version))[("Ingress", "verdaccio")]
                        rules = ingress["spec"]["rules"]
                        self.assertEqual(len(rules), len(hosts) or 1)
                        if hosts:
                            self.assertEqual([rule["host"] for rule in rules],
                                             ["verdaccio.example.com", "other.example.com"])
                        else:
                            self.assertNotIn("host", rules[0])
                        expected_backend = (
                            {"service": {"name": "verdaccio", "port": {"number": 4873}}}
                            if version == "1.19.0"
                            else {"serviceName": "verdaccio", "servicePort": 4873}
                        )
                        for rule in rules:
                            self.assertEqual(rule["http"]["paths"], [
                                {"path": path, "pathType": path_type, "backend": expected_backend}
                                for path in ("/*", "/registry")
                            ])

    def test_default_path_type_remains_prefix(self):
        for hosts in ([], ["registry.example.com"]):
            for override in ({}, {"pathType": None}, {"pathType": ""}):
                with self.subTest(hosts=hosts, override=override):
                    ingress = render({"ingress": {
                        "enabled": True, "hosts": hosts, **override,
                    }})[("Ingress", "verdaccio")]
                    paths = ingress["spec"]["rules"][0]["http"]["paths"]
                    self.assertEqual(paths[0]["path"], "/")
                    self.assertEqual(paths[0]["pathType"], "Prefix")

    def test_extra_paths_keep_their_own_path_type(self):
        ingress = render({"ingress": {
            "enabled": True, "hosts": ["registry.example.com"],
            "pathType": "ImplementationSpecific", "paths": ["/*"],
            "extraPaths": [{"path": "/health", "pathType": "Exact", "service": "health", "port": 80}],
        }}, extra_args=("--kube-version", "1.19.0"))[("Ingress", "verdaccio")]
        paths = ingress["spec"]["rules"][0]["http"]["paths"]
        self.assertEqual(paths[0], {
            "path": "/health", "pathType": "Exact",
            "backend": {"service": {"name": "health", "port": {"number": 80}}},
        })
        self.assertEqual(paths[1]["pathType"], "ImplementationSpecific")


if __name__ == "__main__":
    unittest.main()
