"""Render regressions for the IPv6 nginx sidecar (requires Helm and PyYAML)."""

import unittest

from helpers import render


class NginxIPv6(unittest.TestCase):
    def test_both_families_share_configuration_and_service_restrictions(self):
        ranges = ["192.0.2.0/24", "2001:db8:195::/64"]
        for workload in ("deployment", "statefulset"):
            with self.subTest(workload=workload):
                common = {
                    "type": workload,
                    "service": {
                        "type": "LoadBalancer",
                        "loadBalancerSourceRanges": ranges,
                    },
                }
                ipv4 = render({**common, "cachingNginx": {
                    "enabled": True, "ipv6Enabled": False,
                }})
                dual = render({**common, "cachingNginx": {"enabled": True}})

                # The additional socket must be the only manifest difference:
                # request handling, auth config, Service and Pod settings are shared.
                configs = []
                for documents in (ipv4, dual):
                    config = next(doc for doc in documents.values() if doc["kind"] == "ConfigMap"
                                  and "default.conf" in doc.get("data", {}))
                    configs.append(config["data"])
                    service = documents[("Service", "verdaccio")]
                    self.assertEqual(service["spec"]["loadBalancerSourceRanges"], ranges)
                    self.assertEqual(service["spec"]["ports"][0]["targetPort"], "caching-nginx")
                    kind = "Deployment" if workload == "deployment" else "StatefulSet"
                    pod = documents[(kind, "verdaccio")]
                    annotations = pod["spec"]["template"]["metadata"]["annotations"]
                    annotations.pop("checksum/config-nginx")

                ipv4_data, dual_data = configs
                listen = "  listen [::]:80 ipv6only=on;\n"
                self.assertEqual(dual_data["default.conf"].count(listen), 1)
                dual_data["default.conf"] = dual_data["default.conf"].replace(listen, "")
                self.assertEqual(ipv4, dual)
                self.assertEqual(ipv4_data["default.conf"].count("server {"), 1)
                self.assertIn("listen 80;", ipv4_data["default.conf"])
                self.assertIn("proxy_pass http://127.0.0.1:4873;", ipv4_data["default.conf"])
                self.assertIn("client_max_body_size 100m;", ipv4_data["nginx.conf"])
                self.assertNotRegex(ipv4_data["nginx.conf"], r"set_real_ip_from\s+::/0")

    def test_disabled_sidecar_does_not_change_resources(self):
        default = render({})
        enabled_ipv6 = render({"cachingNginx": {"enabled": False, "ipv6Enabled": True}})
        disabled_ipv6 = render({"cachingNginx": {"enabled": False, "ipv6Enabled": False}})
        self.assertEqual(default, enabled_ipv6)
        self.assertEqual(default, disabled_ipv6)
        self.assertFalse(any("default.conf" in doc.get("data", {}) for doc in default.values()))


if __name__ == "__main__":
    unittest.main()
