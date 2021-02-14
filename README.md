# Verdaccio

[Verdaccio](https://www.verdaccio.org) is a lightweight private
[NPM](https://www.npmjs.com) proxy registry.

## TL;DR;

```
$ helm repo add verdaccio https://charts.verdaccio.org
$ helm repo update
$ helm install verdaccio/verdaccio
```

> ⚠️ If you are using **stable/verdaccio** chart, [be aware is deprecated](https://github.com/helm/charts/pull/21929), forward all new PR and or issues to this repository.

> If you need support for Helm v2, please use `<=v0.19.0`, be aware we do not support Helm v2 anymore.

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

### Install Verdaccio chart

In this example we use `npm` as release name:

```bash
# Helm v3+
helm install npm verdaccio/verdaccio
```

### Deploy a specific version

```bash
# Helm v3+
helm install npm --set image.tag=4.6.2 verdaccio/verdaccio
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

```bash
# Helm v3+
helm uninstall npm
```

The command removes all the Kubernetes components associated with the chart and
deletes the release.

## Configuration

The following table lists the configurable parameters of the Verdaccio chart
and their default values.

| Parameter                          | Description                                                     | Default               |
| ---------------------------------- | --------------------------------------------------------------- | --------------------- |
| `affinity`                         | Affinity for pod assignment                                     | `{}`                  |
| `existingConfigMap`                | Name of custom ConfigMap to use                                 | `false`               |
| `image.pullPolicy`                 | Image pull policy                                               | `IfNotPresent`        |
| `image.pullSecrets`                | Image pull secrets                                              | `[]`                  |
| `image.repository`                 | Verdaccio container image repository                            | `verdaccio/verdaccio` |
| `image.tag`                        | Verdaccio container image tag                                   | `4.6.2`               |
| `nodeSelector`                     | Node labels for pod assignment                                  | `{}`                  |
| `tolerations`                      | List of node taints to tolerate                                 | `[]`                  |
| `persistence.accessMode`           | PVC Access Mode for Verdaccio volume                            | `ReadWriteOnce`       |
| `persistence.enabled`              | Enable persistence using PVC                                    | `true`                |
| `persistence.existingClaim`        | Use existing PVC                                                | `nil`                 |
| `persistence.mounts`               | Additional mounts                                               | `nil`                 |
| `persistence.size`                 | PVC Storage Request for Verdaccio volume                        | `8Gi`                 |
| `persistence.storageClass`         | PVC Storage Class for Verdaccio volume                          | `nil`                 |
| `persistence.volumes`              | Additional volumes                                              | `nil`                 |
| `podAnnotations`                   | Annotations to add to each pod                                  | `{}`                  |
| `priorityClass.enabled`            | Enable specifying pod priorityClassName                         | `false`               |
| `priorityClass.name`               | PriorityClassName to be specified in pod spec                   | `""`                  |
| `replicaCount`                     | Desired number of pods                                          | `1`                   |
| `resources`                        | CPU/Memory resource requests/limits                             | `{}`                  |
| `service.annotations`              | Annotations to add to service                                   | none                  |
| `service.clusterIP`                | IP address to assign to service                                 | `""`                  |
| `service.externalIPs`              | Service external IP addresses                                   | `[]`                  |
| `service.loadBalancerIP`           | IP address to assign to load balancer (if supported)            | `""`                  |
| `service.loadBalancerSourceRanges` | List of IP CIDRs allowed access to load balancer (if supported) | `[]`                  |
| `service.port`                     | Service port to expose                                          | `4873`                |
| `service.nodePort`                 | Service port to expose                                          | none                  |
| `service.type`                     | Type of service to create                                       | `ClusterIP`           |
| `serviceAccount.enabled`           | Enable service account                                          | `false`               |
| `serviceAccount.name`              | Service account Name                                            | none                  |
| `extraEnvVars`                     | Define environment variables to be passed to the container      | `{}`                  |

Specify each parameter using the `--set key=value[,key=value]` argument to `helm install`. For example,

```bash
# Helm v3+
$ helm install my-release \
  --set service.type=LoadBalancer \
    verdaccio/verdaccio
```

The above command sets the service type LoadBalancer.

Alternatively, a YAML file that specifies the values for the above parameters
can be provided while installing the chart. For example,

```bash
# Helm v3+
$ helm install npm -f values.yaml verdaccio/verdaccio
```

> **Tip**: You can use the default [values.yaml](charts/verdaccio/values.yaml)

### Custom ConfigMap

When creating a new chart with this chart as a dependency, CustomConfigMap can
be used to override the default config.yaml provided. It also allows for
providing additional configuration files that will be copied into
`/verdaccio/conf`. In the parent chart's values.yaml, set the value to true and
provide the file `templates/config.yaml` for your use case.

### Persistence

The Verdaccio image stores persistence under `/verdaccio/storage` path of the
container. A dynamically managed Persistent Volume Claim is used to keep the
data across deployments, by default. This is known to work in GCE, AWS, and
minikube.
Alternatively, a previously configured Persistent Volume Claim can be used.

It is possible to mount several volumes using `Persistence.volumes` and
`Persistence.mounts` parameters.

#### Existing PersistentVolumeClaim

1. Create the PersistentVolume
1. Create the PersistentVolumeClaim
1. Install the chart

```bash
# Helm v3+
$ helm install npm \
    --set persistence.existingClaim=PVC_NAME \
    verdaccio/verdaccio
```
