import logging

import kopf
import zulip
import os


client = zulip.Client()
zulip_request_payload = {"type": "stream"}


@kopf.on.startup()
def configure(settings: kopf.OperatorSettings, **_):
    settings.posting.level = logging.ERROR


@kopf.on.field("batch", "v1", "jobs", field="status.conditions")
def event_notification_handler(old, new, status, namespace, **kwargs):
    if namespace not in os.environ.get("ACCEPTED_NAMESPACES").split(','):
        return
    data = kwargs["body"]
    zulip_request_payload["to"] = namespace.split("-")[0]
    zulip_request_payload["topic"] = namespace
    resource_kind = data["kind"]
    resource_name = data["metadata"]["name"]
    error_reason = status["conditions"][0]["reason"]
    error_message = status["conditions"][0]["message"]
    zulip_message_content = f":skull_and_crossbones: {resource_kind} **{resource_name}** failed with the following error:\n> {error_reason}: {error_message}."
    zulip_request_payload["content"] = zulip_message_content
    client.send_message(zulip_request_payload)


@kopf.on.field("v1", "pod", field="status.conditions")
def pod_events_notification_handler(old, new, status, namespace, **kwargs):
    if namespace not in ACCEPTED_NAMESPACES:
        return
    data = kwargs["body"]
    zulip_request_payload["to"] = "test"
    zulip_request_payload["topic"] = namespace
    resource_kind = data["kind"]
    resource_name = data["metadata"]["name"]
    error_reason = status["conditions"][0]["reason"]
    error_message = status["conditions"][0]["message"]
    zulip_message_content = f":skull_and_crossbones: {resource_kind} **{resource_name}** failed with the following error:\n> {error_reason}: {error_message}."
    zulip_request_payload["content"] = zulip_message_content
    client.send_message(zulip_request_payload)
