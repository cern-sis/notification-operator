import logging

import kopf
import kubernetes
import os
import zulip




@kopf.on.startup()
@kopf.timer("node", interval=30.0, sharp=True,
            labels={"node-role.kubernetes.io/master": kopf.ABSENT})
def test_node_scheduling(name, **_):
    phase = create_pod(node_name)

    if phase != "Succeeded":
       send_zulip_notification(node_name) 


def create_pod(node_name: str):
    pod_name = "node-scheduling-test-" ++ node_name
    pod_namespace = "notification-operator"
    pod_manifest = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": { "name": pod_name },
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

    client = kubernetes.client.CoreV1Api()
    resp = client.create_namespaced_pod(body=pod_manifest,
                                        namespace=pod_namespace)

    time.sleep(10)

    resp = client.read_namespaced_pod(name=pod_name,
                                      namespace=pod_namespace)

    client.delete_namespaced_pod(name=pod_name,
                                 namespace=pod_namespace)

    return resp.status.phase


def send_zulip_notification(node_name: str):
    client = zulip.Client()
    client.send_message(
        {"type": "stream",
         "to": "infrastructure",
         "topic": "cluster",
         "content": f":skull_and_crossbones: Node **{node_name}** appears to be unhealthy."
        }
    )
