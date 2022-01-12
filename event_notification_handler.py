import logging

import kopf
import zulip

ACCEPTED_NAMESPACES = ["inspire-prod", "inspire-qa"]
ZULIP_CHANNEL_NAME = "inspire"

client = zulip.Client()

zulip_request_payload = {
    "type": "stream",
    "to": ZULIP_CHANNEL_NAME,
}


@kopf.on.startup()
def configure(settings: kopf.OperatorSettings, **_):
    settings.posting.level = logging.ERROR


@kopf.on.field("batch", "v1", "jobs", field="status.conditions")
def event_notification_handler(old, new, status, namespace, **kwargs):
    data = kwargs["body"]
    zulip_request_payload["topic"] = namespace
    resource_kind = data["kind"]
    resource_name = data["metadata"]["name"]
    error_reason = status["conditions"][0]["reason"]
    error_message = status["conditions"][0]["message"]
    zulip_message_content = f":skull_and_crossbones: {resource_kind} **{resource_name}** failed with the following error:\n> {error_reason}: {error_message}."
    zulip_request_payload["content"] = zulip_message_content
    client.send_message(zulip_request_payload)
