# Verdaccio Charts (Helm)

![verdaccio logo](https://cdn.verdaccio.dev/readme/verdaccio@2x.png)

[Verdaccio](https://verdaccio.org/) is a simple, **zero-config-required local private npm registry**.
No need for an entire database just to get started! Verdaccio comes out of the box with
**its own tiny database**, and the ability to proxy other registries (eg. npmjs.org),
caching the downloaded modules along the way.
For those looking to extend their storage capabilities, Verdaccio
**supports various community-made plugins to hook into services such as Amazon's s3,
Google Cloud Storage** or create your own plugin.

[Verdaccio](https://www.verdaccio.org) is a lightweight private
[NPM](https://www.npmjs.com) proxy registry.

## TL;DR;

```
$ helm repo add verdaccio https://charts.verdaccio.org
$ helm repo update
$ helm install verdaccio/verdaccio
```

> ⚠️ If you are using **stable/verdaccio** chart, [be aware is deprecated](https://github.com/helm/charts/pull/21929), forward all new PR and or issues to this repository.

## Introduction

This chart bootstraps a [Verdaccio](https://github.com/verdaccio/verdaccio)
deployment on a [Kubernetes](https://kubernetes.io) cluster using the
[Helm](https://helm.sh) package manager.

## Prerequisites

- Kubernetes 1.7+ with Beta APIs enabled
- PV provisioner support in the underlying infrastructure

## Installing the Chart

### Add repository

```
helm repo add verdaccio https://charts.verdaccio.org
```

In this example we use `npm` as release name:

```bash
helm install --name npm verdaccio/verdaccio
```

### Deploy a specific version

```bash
helm install --name npm --set image.tag=4.6.2 verdaccio/verdaccio
```

### Upgrading Verdaccio

```bash
helm upgrade npm verdaccio/verdaccio
```

The command deploys Verdaccio on the Kubernetes cluster in the default
configuration. The [configuration](#configuration) section lists the parameters
that can be configured during installation.

> **Tip**: List all releases using `helm list`

## Uninstalling the Chart

To uninstall/delete the `npm` deployment:

```
$ helm delete npm
```
