import datetime
import logging
import kopf
import kubernetes
import os
import time


CHECK_INTERVAL = float(os.environ.get("CHECK_INTERVAL", 30.0))
POD_CREATION_TIMEOUT = float(os.environ.get("POD_CREATION_TIMEOUT", 10.0))
POD_DELETION_TIMEOUT = float(os.environ.get("POD_DELETION_TIMEOUT", 10.0))


@kopf.on.startup()
def configure(settings: kopf.OperatorSettings, **_):
    settings.posting.enabled = False


@kopf.timer("node",
            interval=CHECK_INTERVAL,
            sharp=True,
            labels={
                "node-role.kubernetes.io/master": kopf.ABSENT
            })
def test_node_scheduling(logger, name, **_):
    k8s = kubernetes.client.CoreV1Api()

    pod_namespace = "notification-operator"
    pod_name = f"node-scheduling-test-{name}"

    k8s.delete_namespaced_pod(
        namespace=pod_namespace,
        name=pod_name
    )

    time.sleep(POD_DELETION_TIMEOUT)

    k8s.create_namespaced_pod(
        namespace=pod_namespace,
        body=pod_manifest
    )

    time.sleep(POD_CREATION_TIMEOUT)

    if pod_succeeded(logger, k8s, pod_namespace, pod_name):
        return {
            "status": "succeeded",
            "last": iso_utc_now()
        }
    else:
        return {
            "status": "failed",
            "last": iso_utc_now()
        }


def pod_manifest(node,  namespace, name):
    return {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {
            "namespace": namespace,
            "name": name
        },
        "spec": {
            "restartPolicy": "Never",
            "nodeName": node,
            "containers": [{
                "image": "busybox",
                "name": "true",
                "args": [
                    "/bin/sh",
                    "-c",
                    "true"
                ]
            }]
        }
    }


def pod_succeeded(client, namespace, name):
    status = client.read_namespaced_pod_status(
        namespace=namespace,
        name=name
    )
    if hasattr(status, "phase"):
        return status.phase == "Succeeded"
    else:
        return False


def iso_utc_now():
    datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat()
