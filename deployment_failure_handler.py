import os
import threading
import time

import kopf
import zulip
from kubernetes import client, config
from tabulate import tabulate

config.load_incluster_config()
v1 = client.AppsV1Api()

client = zulip.Client()

deployment_state = {}
stop_sending = True


def _prepare_message_for_deployment(replicas_unavailable, deployment, **kwargs):
    namespace = kwargs["body"]["metadata"]["namespace"]
    if namespace not in os.environ.get("ACCEPTED_NAMESPACES", "").split(","):
        return
    deployment_name = deployment.metadata.name
    # update the state
    if deployment_name in deployment_state:
        print("not the first time it fails - update the state and return")
        deployment_state[deployment_name]["last_alert_time"] = time.time()
        deployment_state[deployment_name]["alert_count"] += 1
        return

    # there's a new alert
    deployment_state[deployment_name] = {
        "first_alert_time": time.time(),
        "last_alert_time": time.time(),
        "alert_count": 1,
        "resolved": False,
    }
    zulip_msg_content = f"""
                        :double_exclamation: Detected deployment
                        **{deployment_name}** is failing.\n
                        \n{replicas_unavailable} replica(s) is/are unavailable
                        """
    print("sending new message to zulip...")
    zulip_request_payload = {
        "type": "stream",
        "to": namespace.split("-")[0],
        "topic": namespace,
        "content": zulip_msg_content,
    }
    client.send_message(zulip_request_payload)
    global stop_sending
    stop_sending = False


def send_resolve_message(deployment, **kwargs):
    namespace = kwargs["body"]["metadata"]["namespace"]
    if namespace not in os.environ.get("ACCEPTED_NAMESPACES", "").split(","):
        return
    deployment_name = deployment.metadata.name
    zulip_msg_content = f"""
                        :check: Deployment **{deployment_name}** has been fixed.
                        """
    zulip_request_payload = {
        "type": "stream",
        "to": namespace.split("-")[0],
        "topic": namespace,
        "content": zulip_msg_content,
    }
    print("sending resolve message to zulip")
    client.send_message(zulip_request_payload)
    global stop_sending
    stop_sending = True


@kopf.on.startup()
def configure(settings: kopf.OperatorSettings, **_):
    settings.posting.enabled = False


# send notification if the deployment is failing
@kopf.on.field("apps", "v1", "deployments", field="status.replicas")
def pod_phase_notification_handler(old, new, body, **kwargs):
    if not old:
        print("not old")
        return
    deployment = v1.read_namespaced_deployment(
        name=body["metadata"]["name"], namespace=body["metadata"]["namespace"]
    )
    max_unavailable = deployment.spec.strategy.rolling_update.max_unavailable
    replicas_unavailable = old - new
    print(type(max_unavailable))
    print(max_unavailable)
    print(type(replicas_unavailable))
    print(replicas_unavailable)
    # send alert if deployment is failing
    if replicas_unavailable > max_unavailable:
        print("deployment is failing")
        _prepare_message_for_deployment(replicas_unavailable, deployment, **kwargs)

    # send notification about the resolved issue
    else:
        print("issue is resolved")
        deployment_name = deployment.metadata.name
        if deployment_name in deployment_state:
            deployment_state[deployment_name]["resolved"] = True
            send_resolve_message(deployment, **kwargs)


# generate the table
def generate_table_content():
    table_content = []
    for deployment_name, state in deployment_state.items():
        table_row = [
            deployment_name,
            time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime(int(state["first_alert_time"]))
            ),
            time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime(int(state["last_alert_time"]))
            ),
            state["alert_count"],
            "Yes" if state["resolved"] else "No",
        ]
        table_content.append(table_row)
    return table_content


def send_table_periodically():
    print("thread spawned for sending the tabular summary periodically")
    while not stop_sending:
        table_content = generate_table_content()

        zulip_msg_content = "Deployment Alert Summary: \n\n" + tabulate(table_content)
        zulip_request_payload = {
            "type": "stream",
            "to": "test",
            "topic": "Deployment Alerts",
            "content": zulip_msg_content,
        }
        client.send_message(zulip_request_payload)

        # Sleep for 15 minutes
        time.sleep(900)


table_thread = threading.Thread(target=send_table_periodically)
table_thread.start()

table_thread.join()
