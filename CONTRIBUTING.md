## Contributions Guidelines

Welcome to the Verdaccio Chart repository.

If you are willing the contribute, these are the must-known:

- **Update documentation**: The readme is the main source of documentation, please if you add or modify any feature
  is a mandatory step.
- **Bum up**: Every new feature/fix requires a bump up (unfortunatelly is not automated).
- **Test are green**: The projects rely on `helm/chart-testing-action`, it has to be green before merge.
- **Document your PR**: What motivates the change and explain your solution is a nice to have, share knowledge would speed up the merge.
- **Breaking changes**: Any breaking change must bump up as major. What's a breaking change? eg: Verdaccio docker image bump up to major,
  or anything that clearly break current users workflows.

> Feel free to update this list.

## Kubernetes Group

The @verdaccio/kubernetes group (team according GH) is a group created to empower new contributors to keep contributing to this chart,
either reviewing new contributors and making grow the project. Every member has `maintain` role assigned.

You are eligible to this group when you have done a contribution to the chart.

## Merging a Pull Request

The current setup requires 2 members to approve the pull request and nobody agasint it, before merge, please take in account the contribution follow the
rules above described.

The administrator can merge without the 2 required approvals, but, only with the idea unblock lack of unresponsive approvals.

The contribution is meant to improve the chart and has to be positive for users. If for some reason, the PR has a `requested changes`
has to be resolved (either discussion or similar always following the code of conduct guidelines) before merge.

## Template regression tests

With Helm 3.19 or newer and Python installed, run:

```sh
python -m pip install -r tests/requirements.txt
python -m unittest discover -s tests -v
helm lint charts/verdaccio --strict
```

The render tests check generated Kubernetes manifests, including probe configuration for Deployment and StatefulSet. They run separately from the existing chart-testing lint and cluster installation job.

### nginx IPv6 validation

The nginx render tests check IPv4/IPv6 configuration parity.

With Docker running and support for IPv6-only Docker networks, also run:

```sh
python tests/nginx_runtime.py
```

This optional test uses `nginx:1.25.0`, `node:24.15.0-alpine`, and
`verdaccio/verdaccio` at the `appVersion` in `charts/verdaccio/Chart.yaml`
(Docker downloads them if needed). It creates isolated,
internal networks and temporary containers without publishing host ports, and
removes them after the run. It reproduces the IPv4-only listener failure and
checks IPv4/IPv6 connectivity, private package metadata and tarball permissions,
forged IP headers, and request size limits. It also checks both nginx configurations
with IPv6 addresses disabled via sysctl. This syntax check does not simulate a
kernel booted with `ipv6.disable=1`, where IPv6 sockets are unavailable.
It does not validate Kubernetes NetworkPolicies or cloud load balancer rules.

Validate the deployment in an IPv6-only cluster and a dual-stack cluster:

- Request `/-/ping` through the Service and load balancer over IPv6; it must
  reach Verdaccio without connection refusals or gateway errors. In dual-stack,
  repeat over IPv4 and compare results. Check both Deployment and StatefulSet.
- For a package restricted to a test user, request its metadata and tarball
  without credentials, with invalid credentials, and as a forbidden user. All
  must be denied over both families. The authorized user must succeed over both,
  including after an authorized request, to detect unintended cached access.
- From allowed and denied source networks, check both the load balancer and any
  direct Pod access permitted by your network. Network restrictions must reject
  denied clients over both families. Repeat with forged `X-Real-IP` and
  `X-Forwarded-For` headers to verify they cannot bypass those restrictions.
- Send a request exceeding the configured `client_max_body_size`; expect HTTP
  413 over both families. On a kernel booted with `ipv6.disable=1`, verify nginx starts with
  `ipv6Enabled: false`. A sysctl-only disable does not reproduce this condition.
