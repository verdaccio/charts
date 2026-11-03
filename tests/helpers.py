"""Shared helpers for rendering chart manifests and inspecting workloads."""
import os
from pathlib import Path
import subprocess

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


def container(documents, workload):
    kind = "StatefulSet" if workload == "statefulset" else "Deployment"
    return next(c for c in documents[(kind, "verdaccio")]["spec"]["template"]["spec"]["containers"]
                if c["name"] == "verdaccio")
