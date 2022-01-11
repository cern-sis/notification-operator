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
        request["content"] = {
            "resource_name": object_metadata["ownerReferences"][0]["name"],
            "resource_kind": object_metadata["ownerReferences"][0]["kind"],
            "resource_uid": object_metadata["ownerReferences"][0]["uid"],
            "error": object_container_status["state"]["terminated"]["message"],
        }
        client.send_message(request)
