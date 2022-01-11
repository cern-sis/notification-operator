import kopf
import zulip

client = zulip.Client()

request = {
    "type": "stream",
    "to": "INSPIRE",
}


@kopf.on.event("", "v1", "pods")
def event_notification_handler(event, **_):
    object_container_status = event["object"]["status"].get("containerStatuses")[0]
    if not object_container_status:
        return
    if (
        "terminated" in object_container_status["state"]
        and object_container_status["state"]["terminated"]["reason"] == "Error"
    ):
        object_metadata = event["object"]["metadata"]
        request["topic"] = object_metadata["namespace"]
        resource_kind = object_metadata["ownerReferences"][0]["kind"]
        resource_name = object_metadata["ownerReferences"][0]["name"]
        error_message = object_container_status["state"]["terminated"].get("message")
        zulip_message_content = (
            f":skull_and_crossbones: {resource_kind} **{resource_name}** failed with the following error:\n> {error_message}."
            if error_message
            else f":skull_and_crossbones: {resource_kind} **{resource_name}** failed."
        )

        request["content"] = zulip_message_content
        client.send_message(request)
