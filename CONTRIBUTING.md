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
