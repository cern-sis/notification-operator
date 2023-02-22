import logging
import os

import kopf
import zulip
from kubernetes import client, config, watch

config.load_incluster_config()
v1=client.AppsV1Api()

client = zulip.Client()


def _prepare_message_for_deployment(replicas_unavailable, deployment, **kwargs):
    namespace = kwargs["body"]["metadata"]["namespace"]
    if namespace not in os.environ.get("ACCEPTED_NAMESPACES", "").split(","):
        return
    deployment_name = deployment.metadata.name
    zulip_msg_content = f":double_exclamation: Detected deployment **{deployment_name}** is failing. \n\n{replicas_unavailable} replica(s) is/are unavailable"
    zulip_request_payload = {
        "type": "stream",
        "to": namespace.split("-")[0],
        "topic": namespace,
        "content": zulip_msg_content,
    }
    client.send_message(zulip_request_payload)


@kopf.on.startup()
def configure(settings: kopf.OperatorSettings, **_):
    settings.posting.enabled = False

# get the deployment object
# get max unavailable and use it to see if the deployment is actually failing => old-new+max_unav should be more than 0
@kopf.on.field("apps", "v1", "deployments", field="status.replicas")
def pod_phase_notification_handler(old, new, body, **kwargs):
    if not old:
        return
    deployment = v1.read_namespaced_deployment(name=body['metadata']['name'], namespace=body['metadata']['namespace'])
    max_unavailable = deployment.spec.strategy.rolling_update.max_unavailable
    replicas_unavailable = (old-new)+max_unavailable
    if replicas_unavailable > 0:
        _prepare_message_for_deployment(replicas_unavailable, deployment, **kwargs)
