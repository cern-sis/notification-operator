import logging

import kopf
import zulip

ACCEPTED_NAMESPACES = ["inspire-prod", "inspire-qa"]

client = zulip.Client()

zulip_request_payload = {
    "type": "stream",
    "to": "INSPIRE",
}


@kopf.on.startup()
def configure(settings: kopf.OperatorSettings, **_):
    settings.posting.level = logging.ERROR


@kopf.on.event("", "v1", "pods", field='kind', value='Job')
@kopf.on.event("", "v1", "pods", field='status.phase', value='Failed')
def event_notification_handler(event, **_):
    object_container_status = event["object"]["status"].get("containerStatuses")
    if not object_container_status:
        return
    object_metadata = event["object"]["metadata"]
    zulip_request_payload["topic"] = object_metadata["namespace"]
    resource_kind = object_metadata["ownerReferences"][0]["kind"]
    resource_name = object_metadata["ownerReferences"][0]["name"]
    error_message = object_container_status[0]["state"]["terminated"].get("message")
    zulip_message_content = (
        f":skull_and_crossbones: {resource_kind} **{resource_name}** failed with the following error:\n> {error_message}."
        if error_message
        else f":skull_and_crossbones: {resource_kind} **{resource_name}** failed."
    )
    zulip_request_payload["content"] = zulip_message_content
    client.send_message(zulip_request_payload)
