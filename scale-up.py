import logging
import sys
from datetime import datetime
import pytz
from kubernetes import client, config
import requests

# adding envs
slack_webhook_url = "<>"

KUBE_CONFIG = "/root/.kube/config"

config.load_config(config_file=KUBE_CONFIG)

# print execution time in IST

utc_now = datetime.utcnow()
ist = pytz.timezone("Asia/Kolkata")
ist_now = utc_now.replace(tzinfo=pytz.utc).astimezone(ist)

# defining the logger
logger = logging.getLogger(__name__)

stream_handler = logging.StreamHandler(sys.stdout)
file_handler = logging.FileHandler("/var/log/scaling-down-workload.log")
log_format = logging.Formatter('[%(asctime)s] %(levelname)s - %(message)s')

logger.addHandler(stream_handler)
stream_handler.setFormatter(log_format)
logger.addHandler(file_handler)
file_handler.setFormatter(log_format)

# define potential deployment sets

user_input = input("Enter the deployment name separated by comma: ")
user_input_list = user_input.split()
if len(user_input_list) == 0:
    logger.error("Invalid deployment name")

print("Input deployment values: ", user_input_list)

deployments = user_input_list
current_namespace = "<namespace_name>"

api_instance = client.AppsV1Api()


# slack alert module
def slack_alert(message):
    payload = {
        "text_msg": message,
        "Content-type": "application/json"
    }
    try:
        response = requests.post(url=slack_webhook_url, json=payload)
        logger.info("slack notified")
    except Exception as e:
        logger.error("Error sending Slack notification:", str(e))


# create a function which takes workloads to scale down to 50%
def scale_up(workloads, namespace):
    for deployment in workloads:
        try:
            deploy_read = api_instance.read_namespaced_deployment(namespace=namespace, name=deployment)
            current_replica_count = int(deploy_read.spec.replicas)
            logger.info("current-replica ", {current_replica_count})
            # to scale to 50% of current replica
            calculate_scaling_up = int(current_replica_count * 2)
            # scaling down
            logger.info('new replica is ', {calculate_scaling_up})
            new_replica_count = calculate_scaling_up
            body = client.V1Scale(spec=client.V1ScaleSpec(replicas=new_replica_count))
            updated_deployment = api_instance.patch_namespaced_deployment_scale(namespace=namespace, name=deployment,
                                                                                body=body)
            print(f"Deployment {deployment} has been scaled up to {new_replica_count} replicas")
        except client.exceptions.ApiException as type_error:
            logger.error(f"Workload is not a valid deployment - {type_error}")


# scale down

scale_up(workloads=deployments, namespace=current_namespace)
logger.info("scale up time in IST:", ist_now.strftime('%Y-%m-%d %H:%M:%S %Z%z'))
slack_alert(f"{user_input_list} has been scaled up.")
