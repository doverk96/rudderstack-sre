# rudderstack-sre
A framework for managing alerts programmatically with defined actions, as part of the SRE assignment for RudderStack. This project includes receiving alerts via a webhook, enriching alert data, and taking appropriate actions such as sending notifications to Slack.

# AlertManager Webhook Server

This project implements a webhook server designed to handle alerts, specifically focusing on taking actions once an alert is received. It enriches alerts with additional information and suggests actions to resolve issues. The server is containerized for easy deployment.

## Features

- **Alert Handling**: Processes incoming alerts and enriches them with actionable insights.
- **Image Pull Error Handling**: Specifically targets image pull errors, suggesting fixes and attempting to patch deployments with updated images.
- **Kubernetes Integration**: Interacts with Kubernetes to read pod details and update deployments.
- **Logging**: Utilizes structured logging for better observability.

## Components

- `webhook_server.py`: The main Flask application that receives and processes alerts.
- `alert_manager.py`: Manages alert processing logic.
- `ImagePullError.py`: Contains logic for handling image pull errors, including Kubernetes interactions.
- `Dockerfile`: Defines the container image for running the webhook server.
- Kubernetes YAML files for deploying the webhook server:
    - `webhook_server_deployment.yaml`: Deployment configuration for the webhook server.
    - `webhook_server_deployment_crashloop.yaml`: Example deployment configuration simulating a crashloop scenario.
    - `webhook_server_role.yaml`: Defines the necessary permissions for the webhook server.
    - `webhook_server_role_binding.yaml`: Binds the role to the webhook server service account.
    - `webhook_server_service.yaml`: Exposes the webhook server as a service within the cluster.

## Getting Started

### Prerequisites

- Docker
- Kubernetes cluster
- `kubectl` configured to interact with your cluster

### Deployment

1. **Build the Docker Image**

    Navigate to the project directory and build the Docker image:

    ```sh
    docker build -t webhook-server:latest .
    ```

2. **Deploy to Kubernetes**

    Apply the Kubernetes configurations:

    ```sh
    kubectl apply -f webhook_server_deployment.yaml
    kubectl apply -f webhook_server_role.yaml
    kubectl apply -f webhook_server_role_binding.yaml
    kubectl apply -f webhook_server_service.yaml
    ```

## Adding a New Alert Handling Pipeline

The framework is designed to allow developers to easily add new alert handling flows. The process is based on dynamically loading a Python module corresponding to the `alertname` present in the alert JSON from Prometheus Alertmanager. Here’s how you can add a new handling pipeline:

### Steps to Add a New Handling Pipeline

1. **Create a New Python File**: 
   - Name the file exactly as the `alertname` in the alert JSON.
   - For example, if the `alertname` is `DiskSpaceLow`, create a file named `DiskSpaceLow.py`.

2. **Define a Handler Class**:
   - Within the new file, define a class named `<Alertname>Handler` (e.g., `DiskSpaceLowHandler`).
   - Implement an `enrich` method within this class to handle the alert enrichment logic.

### Example

Here’s an example of a handler class for an alert named `DiskSpaceLow`:

```python
# DiskSpaceLow.py

class DiskSpaceLowHandler:
    def enrich(self, alert_item):
        # Custom enrichment logic for DiskSpaceLow alerts
        alert_item['enriched_data'] = "Custom enriched data for DiskSpaceLow"
        return alert_item
```

### Handling of ImagePullError Alerts - Detailed Explanation

- **Description**: ImagePullError alerts are generated when a pod is unable to pull the image from the container registry. This section enriches the alert data with the suggested action and the action taken summary.
- **Kubernetes Python Client**: Used to interact with the Kubernetes API server.
- **Boto3 Library**: Used to interact with the Amazon ECR API.
- **Service Account Token**: Utilized to authenticate with the Kubernetes API server.
- **Retrieves the Latest Image**: From the Amazon ECR repository.
- **Patches the Deployment**: With the new image.
- **`handle_image_pull_error` Function**: Handles the image pull error.
- **`find_deployment_by_pod_name` Function**: Finds the deployment name based on the pod name.
- **`get_latest_image_from_ecr` Function**: Gets the latest image from the Amazon ECR repository.
- **`update_deployment_image` Function**: Updates the deployment image.

## Configuration

The webhook server listens on port 5000 by default. Modify `webhook_server_deployment.yaml` or `webhook_server_deployment_crashloop.yaml` as needed to fit your environment.

## License

This project is licensed under the MIT License - see the `LICENSE` file for details.