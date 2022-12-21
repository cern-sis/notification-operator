import logging
import os

import kopf
import zulip


client = zulip.Client()


def _prepare_container_state_message(container_state):
    state = set(container_state.keys()).pop()
    state_data = container_state[state]
    reason = state_data['reason']
    message = state_data['message']
    container_status_msg_content = f"**Container state:\n* state: *{state}*\n\n* message: *{message}*\n\n* reason: *{reason}*"
    return container_status_msg_content


def _prepare_message_for_pod(container_state, pod_phase, **kwargs):
    namespace = kwargs["body"]["metadata"]["namespace"]
    if namespace not in os.environ.get("ACCEPTED_NAMESPACES", "").split(","):
        return
    resource_name = kwargs["body"]["metadata"]["name"]

    zulip_msg_content = f":double_exclamation: Detected dangerous container state for pod **{resource_name}**\n\nPod phase: **{pod_phase}**\n\n"
    container_status_msg_content = _prepare_container_state_message(
        container_state
    )

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
    # check container state
    new_container_state= new["containerStatuses"][0]["state"]
    old_container_state= old["containerStatuses"][0]["state"]
    if new_container_state == old_container_state:
        return
    new_phase = new['phase']
    if 'waiting' in new_container_state or 'terminated' in new_container_state:
        _prepare_message_for_pod(new_container_state, new_phase, **kwargs)
