import logging
import os

import kopf
import zulip

client = zulip.Client()


DANGEROUS_POD_STATUSES = ["Pending", "Failed", "Unknown"]


def _prepare_container_status_message(container_status_info):
    container_status = set(container_status_info.keys()).pop()
    container_status_reason = container_status_info[container_status].get("reason")
    container_status_message = container_status_info[container_status].get("message")
    if all([container_status, container_status_reason, container_status_message]):
        container_status_msg_content = f"**Container status info**:\n* status: *{container_status}*\n\n* reason: *{container_status_reason}*\n\n* message: *{container_status_message}*"
        return container_status_msg_content


def _prepare_message_for_pod(container_status_info, pod_phase, **kwargs):
    namespace = kwargs["body"]["metadata"]["namespace"]
    if namespace not in os.environ.get("ACCEPTED_NAMESPACES", "").split(","):
        return
    resource_name = kwargs["body"]["metadata"]["name"]

    zulip_msg_content = f":double_exclamation: Detected suspicious state transition for pod **{resource_name}**\n\nPod phase: **{pod_phase}**\n\n"
    container_status_msg_content = _prepare_container_status_message(
        container_status_info
    )
    if not container_status_msg_content:
        return

    zulip_msg_content += container_status_msg_content

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


@kopf.on.field("v1", "pod", field="status")
def pod_phase_notification_handler(old, new, status, **kwargs):
    if not old:
        return

    if new["phase"] in DANGEROUS_POD_STATUSES and old["phase"] != new["phase"]:
        container_status_info = new["containerStatuses"][0]["state"]
        pod_phase = new["phase"]
        _prepare_message_for_pod(container_status_info, pod_phase, **kwargs)
