import datetime
import logging
import kopf
import kubernetes
import os
import time


POD_CREATION_TIMEOUT = float(os.environ.get("POD_CREATION_TIMEOUT", 5.0))
POD_CREATION_INTERVAL = float(os.environ.get("POD_CREATION_INTERVAL", 30.0))


@kopf.on.startup()
def configure(settings: kopf.OperatorSettings, **_):
    settings.posting.enabled = False


@kopf.timer("node",
            interval=POD_CREATION_INTERVAL,
            sharp=True,
            labels={
                "node-role.kubernetes.io/master": kopf.ABSENT
            })
def test_node_scheduling(logger, name, **_):
    k8s = kubernetes.client.CoreV1Api()

    pod_namespace = "notification-operator"
    pod_name = "node-scheduling-test-" + name

    # If the pod from the previous check is still around,
    # the deletion probably failed and something is wrong
    # with the node
    if pod_exists(logger, k8s, pod_namespace, pod_name):
        return status_failure("podAlreadyExists")

    if not create_pod(logger, k8s, name, pod_namespace, pod_name):
        return status_failure("podCreationFailed")

    time.sleep(POD_CREATION_TIMEOUT)

    if not pod_succeeded(logger, k8s, pod_namespace, pod_name):
        return status_failure("podDidntSucceed")

    # If the pod deletion fails, something is probably wrong.
    if not delete_pod(logger, k8s, pod_namespace, pod_name):
        return status_failure("podDeletionFailed")

    return status_success()


def create_pod(logger, client, node,  namespace, name):
    manifest = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": { "name": name },
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

    try:
        client.create_namespaced_pod(
            namespace=namespace,
            body=manifest
        )
        return True
    except Exception as e:
        logger.exception(e)
        return False


def get_pod_status(logger, client, namespace, name):
    try:
        return client.read_namespaced_pod_status(
            namespace=namespace,
            name=name
        )
    except Exception as e:
        logger.exception(e)
        return False


def delete_pod(logger, client, namespace, name):
    try:
        client.delete_namespaced_pod(
            namespace=namespace,
            name=name
        )
        return True
    except Exception as e:
        logger.exception(e)
        return False


def pod_exists(*args):
    return get_pod_status(*args) != False


def pod_succeeded(*args):
    status = get_pod_status(*args)
    return status.phase == "Succeeded"


def iso_utc_now():
    datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat()


def status_failure(reason):
    return {
        "status": "failed",
        "reason": reason,
        "last": iso_utc_now()
    }


def status_success():
    return {
        "status": "succeeded",
        "last": iso_utc_now()
    }
