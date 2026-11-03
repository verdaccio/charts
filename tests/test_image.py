"""Render regressions: python -m unittest discover -s tests (requires Helm and PyYAML)."""
import unittest

import yaml

from helpers import CHART, container, render


class ChartTemplates(unittest.TestCase):
    def assert_version_labels(self, documents, expected):
        for doc in documents.values():
            if doc["kind"] in ("Deployment", "StatefulSet"):
                self.assertEqual(doc["metadata"]["labels"]["app.kubernetes.io/version"], expected)
                self.assertEqual(doc["spec"]["template"]["metadata"]["labels"]["app.kubernetes.io/version"], expected)

        def check(value):
            if isinstance(value, dict):
                for label, content in value.get("metadata", {}).get("labels", {}).items():
                    self.assertNotIn("sha256:", content)
                    self.assertLessEqual(len(content), 63)
                    self.assertRegex(content, r"^([A-Za-z0-9]([A-Za-z0-9_.-]*[A-Za-z0-9])?)?$")
                    if label == "app.kubernetes.io/version":
                        self.assertEqual(content, expected)
                for child in value.values():
                    check(child)
            elif isinstance(value, list):
                for child in value:
                    check(child)

        check(documents)

    def test_digest_and_tag_version_label(self):
        app_version = yaml.safe_load((CHART / "Chart.yaml").read_text())["appVersion"]
        for workload in ("deployment", "statefulset"):
            for tag in (None, "6.10.2"):
                for digest in ("", "sha256:" + "a" * 64):
                    with self.subTest(workload=workload, tag=tag, digest=digest):
                        image = {"repository": "example.com/verdaccio", "digest": digest}
                        if tag:
                            image["tag"] = tag
                        docs = render({"type": workload, "image": image})
                        expected = "example.com/verdaccio" + ("@" + digest if digest else ":" + (tag or app_version))
                        self.assertEqual(container(docs, workload)["image"], expected)
                        self.assert_version_labels(docs, tag or app_version)

    def test_omitted_or_null_digest_preserves_version_selection(self):
        app_version = yaml.safe_load((CHART / "Chart.yaml").read_text())["appVersion"]
        for workload in ("deployment", "statefulset"):
            for digest_values in ({}, {"digest": None}):
                for tag_values in ({}, {"tag": ""}, {"tag": "7.0.0-custom"}):
                    with self.subTest(workload=workload, digest=digest_values, tag=tag_values):
                        image = {**digest_values, **tag_values}
                        docs = render({"type": workload, "image": image})
                        version = tag_values.get("tag") or app_version
                        self.assertEqual(container(docs, workload)["image"], "verdaccio/verdaccio:" + version)
                        self.assert_version_labels(docs, version)

    def test_digest_with_private_registry_preserves_container_settings(self):
        digest = "sha256:" + "b" * 64
        for workload in ("deployment", "statefulset"):
            with self.subTest(workload=workload):
                docs = render({
                    "type": workload,
                    "image": {
                        "repository": "mirror.example.com:5000/team/verdaccio",
                        "digest": digest,
                        "tag": "7.0.0-custom",
                        "pullPolicy": "Always",
                        "pullSecrets": ["registry-credentials"],
                    },
                    "cachingNginx": {"enabled": True},
                    "extraInitContainers": [{"name": "prepare", "image": "busybox:1.37"}],
                })
                self.assertIn(("ConfigMap", "verdaccio"), docs)
                self.assertIn(("ConfigMap", "verdaccio-nginx-config"), docs)
                main = container(docs, workload)
                self.assertEqual(main["image"], "mirror.example.com:5000/team/verdaccio@" + digest)
                self.assertEqual(main["imagePullPolicy"], "Always")
                kind = "StatefulSet" if workload == "statefulset" else "Deployment"
                pod = docs[(kind, "verdaccio")]["spec"]["template"]["spec"]
                self.assertEqual(pod["imagePullSecrets"], [{"name": "registry-credentials"}])
                self.assertEqual(pod["initContainers"][0]["image"], "busybox:1.37")
                nginx = next(c for c in pod["containers"] if c["name"] == "verdaccio-nginx")
                self.assertEqual(nginx["image"], "nginx:1.25.0")
                self.assert_version_labels(docs, "7.0.0-custom")


if __name__ == "__main__":
    unittest.main()
