import logging

import kopf
import zulip
import os


client = zulip.Client()
zulip_request_payload = {"type": "stream"}


class NotificationHandler:
    def prepare_message(self, old, new, status, namespace, **kwargs):
        if namespace not in os.environ.get("ACCEPTED_NAMESPACES").split(','):
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

    def configure(settings: kopf.OperatorSettings, **_):
        settings.posting.level = logging.ERROR


notification_handler = NotificationHandler()

kopf.on.startup()(notification_handler.prepare_message)
kopf.on.field("batch", "v1", "jobs", field="status.conditions")(
    notification_handler.prepare_message
)
kopf.on.field("v1", "pod", field="status.conditions")(
    notification_handler.prepare_message
)
