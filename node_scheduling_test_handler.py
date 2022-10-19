import logging
import kopf
import kubernetes
import os


POD_CREATION_TIMEOUT = os.environ.get(POD_CREATION_TIMEOUT, 5.0)
POD_CREATION_INTERVAL = os.environ.get(POD_CREATION_INTERVAL, 30.0)


@kopf.timer("node",
            interval=POD_CREATION_INTERVAL,
            sharp=True,
            labels={
                "node-role.kubernetes.io/master": kopf.ABSENT
            })
def test_node_scheduling(name, **_):
    k8s = kubernetes.client.CoreV1Api()

    selector = {
        "namespace": "notification-operator",
        "name": "node-scheduling-test-" ++ name
    }

    if pod_exists(k8s, **selector):
        return {"status": "failed", "reason": "podAlreadyExists"}
        
    if not create_pod(k8s, **selector):
        return {"status": "failed", "reason": "podCreationFailed"}

    sleep(POD_CREATION_TIMEOUT)

    if not pod_succeeded(k8s, **selector):
        return {"status": "failed", "reason": "podDidntSucceed"}

    if not delete_pod(k8s, **selector):
        return {"status": "failed", "reason": "podDeletionFailed"}


def create_pod(client, namespace, name):
    manifest = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": { "name": name },
        "spec": {
            "restartPolicy": "Never",
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

    try client.create_namespaced_pod(
        namespace=namespace,
        body=manifest
    ):
        return True
    except Exception:
        return False


def get_pod_status(client, kwargs):
    try:
        return client.read_namespaced_pod_status(kwargs)
    except Exception:
        return False


def delete_pod(client, kwargs):
    try:
        client.delete_namespaced_pod(client, kwargs)
        return True
    except Exception:
        return False


def pod_exists(client, kwargs):
    return get_pod_status(client, kwargs) != False


def pod_succeeded(client, kwargs):
    status = get_pod_status(client, kwargs)
    return status.phase == "Succeeded"
