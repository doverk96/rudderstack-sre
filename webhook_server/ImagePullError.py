# ImagePullError.py

from kubernetes import client, config
from kubernetes.client.rest import ApiException
import json
import boto3
import logging
import urllib3
from urllib3.exceptions import InsecureRequestWarning

urllib3.disable_warnings(InsecureRequestWarning)

class ImagePullErrorHandler:
    def __init__(self):
        # Initialize Kubernetes client with service account token
        config.load_incluster_config()
        self.configuration = client.Configuration()
        self.configuration.host = "https://kubernetes.default.svc"
        self.configuration.verify_ssl = False
        self.configuration.debug = False

        # Load service account token from the pod environment
        self.configuration.api_key = {'authorization': f'Bearer {self.get_service_account_token()}'}
        self.api_client = client.CoreV1Api(client.ApiClient(self.configuration))
        self.k8s_client = client.AppsV1Api(client.ApiClient(self.configuration))
        self.ecr_client = boto3.client('ecr', region_name='ap-south-1')
        logging.getLogger('botocore').setLevel(logging.CRITICAL)
        logging.getLogger('boto3').setLevel(logging.CRITICAL)
        logging.getLogger('urllib3').setLevel(logging.CRITICAL)
        
    def enrich(self, alert_item):
        alert_details = {'documentation_link': 'https://kubernetes.io/docs/concepts/containers/images/#updating-images'}
        
        try:
            namespace = alert_item['labels']['namespace']
            pod_name = alert_item['labels']['pod']
            container_name = alert_item['labels']['container']

            pod = self.api_client.read_namespaced_pod(pod_name, namespace)
            for container in pod.spec.containers:
                if container.name == container_name:
                    alert_details['suggested_action'] = f'Verify the image {container.image}. Ensure the image exists in the registry and the node has access to it.'
                    handle_result = self.handle_image_pull_error(container.image, namespace, pod_name, container_name, pod)
                    
                    if not handle_result:
                        print(f"No stable or latest image found for the given repository. Deployment patching failed.")
                        alert_details['action_taken_summary'] = 'No stable or latest image found for the given repository. Deployment patching failed.'
                    else:
                        print(f"Deployment has been updated with a new image - {handle_result['patched_image']}")
                        alert_details['action_taken_summary'] = f'Deployment has been updated with a new image - {handle_result["patched_image"]}'
                    break
                
        except ApiException as e:
            alert_details['suggested_action'] = f"Exception when calling CoreV1Api->read_namespaced_pod: {e}, please check the logs for more details"
        except KeyError as e:
            alert_details['suggested_action'] = f"KeyError: Missing key {str(e)} in alert_item labels"
        
        alert_item['enriched_data'] = json.dumps(alert_details, indent=4)
        return alert_item
    
    def get_service_account_token(self):
        with open("/var/run/secrets/kubernetes.io/serviceaccount/token", "r") as token_file:
            return token_file.read().strip()

    def handle_image_pull_error(self, alert_image, namespace, pod_name, container_name, pod):
        alert_image_name = alert_image.split(':')[0]  # Remove the tag part
        repository_parts = alert_image_name.split('/')
        registry_url = '/'.join(repository_parts[:-2])  # Get the registry URL
        repository_name = '/'.join(repository_parts[-2:])  # Get the repository name
        
        latest_image_repository = self.get_latest_image_from_ecr(repository_name)
        latest_image = f"{registry_url}/{latest_image_repository}"
        if not latest_image:
            return None
        
        deployment_name = self.find_deployment_by_pod_name(pod_name, namespace, pod)
        if not deployment_name:
            return None
        
        try:

            self.update_deployment_image(deployment_name, namespace, container_name, latest_image)
            return {'patched_image': latest_image}
        except ApiException as e:
            print(f"Exception when patching deployment: {e}")
            return None

    def find_deployment_by_pod_name(self, pod_name, namespace, pod):
        try:
            owner_references = pod.metadata.owner_references
            for owner in owner_references:
                if owner.kind == 'ReplicaSet':
                    replicaset_name = owner.name
                    replicaset = self.k8s_client.read_namespaced_replica_set(replicaset_name, namespace)
                    for owner in replicaset.metadata.owner_references:
                        if owner.kind == 'Deployment':
                            return owner.name
        except ApiException as e:
            print(f"Exception when retrieving deployment name: {e}")
        return None

    def get_latest_image_from_ecr(self, repository_name):
        try:
            paginator = self.ecr_client.get_paginator('describe_images')

            response_iterator = paginator.paginate(repositoryName=repository_name, filter={'tagStatus': 'TAGGED'})

            latest_image = None
            latest_pushed_at = None

            for response in response_iterator:
                for image_detail in response.get('imageDetails', []):
                    if not latest_pushed_at or image_detail['imagePushedAt'] > latest_pushed_at:
                        latest_pushed_at = image_detail['imagePushedAt']
                        latest_image = image_detail

            if not latest_image or not latest_image.get('imageTags'):
                return None
            
            latest_tag = latest_image['imageTags'][0]
            return f"{repository_name}:{latest_tag}"
        except self.ecr_client.exceptions.RepositoryNotFoundException:
            print(f"Repository {repository_name} not found in ECR \n")
            return None
        except Exception as e:
            print(f"Exception when retrieving latest image from ECR: {e} \n")
            return None

    def update_deployment_image(self, deployment_name, namespace, container_name, latest_image):
        try:
            deployment = self.k8s_client.read_namespaced_deployment(deployment_name, namespace)
            for container in deployment.spec.template.spec.containers:
                if container.name == container_name:
                    container.image = latest_image
                    break
            self.k8s_client.patch_namespaced_deployment(deployment_name, namespace, deployment)
        except ApiException as e:
            print(f"Exception when patching deployment: {e}")
