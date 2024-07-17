import requests
import json
import importlib
import logging
import os

class AlertManager:
    def __init__(self, logger):
        self.logger = logger
        self.SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL', '')
        self.alerts_processed = 0
        self.alerts_successful = 0
        self.alerts_failed = 0

    def default_enrich(self, alert_item):
        alert_item['enriched_data'] = "Default enriched data"
        return alert_item

    def enrich_by_alertname(self, alert_item):
        alertname = alert_item['labels']['alertname']
        try:
            module = importlib.import_module(alertname)
            handler_class = getattr(module, f"{alertname}Handler")
            handler_instance = handler_class()
            return handler_instance.enrich(alert_item)
        except ModuleNotFoundError:
            self.logger.warning("Module not found for alertname: %s. Using default enrichment.", alertname)
            return self.default_enrich(alert_item)
        except AttributeError:
            self.logger.error("Handler class not found in module: %s", alertname)
            return self.default_enrich(alert_item)
        except Exception as e:
            self.logger.error("Error enriching alert: %s", e)
            return self.default_enrich(alert_item)
        
    def enrich_alert(self, alert):
        for alert_item in alert['alerts']:
            alert_item = self.enrich_by_alertname(alert_item)
        return alert

    def process_alert(self, alert):
        self.alerts_processed += 1
        
        # Split alerts into resolved and others
        resolved_alerts = []
        other_alerts = []
        
        for alert_item in alert['alerts']:
            if alert_item['status'] == 'resolved':
                resolved_alerts.append(alert_item)
            else:
                other_alerts.append(alert_item)

        # Send resolved alerts directly to Slack
        if resolved_alerts:
            resolved_alerts_payload = {'alerts': resolved_alerts}
            try:
                self.send_to_slack(resolved_alerts_payload)
                self.alerts_successful += len(resolved_alerts)
            except Exception as e:
                self.alerts_failed += len(resolved_alerts)
                self.logger.error("Failed to send resolved alerts to Slack: %s", e)
                raise

        # Process and send other alerts
        if other_alerts:
            other_alerts_payload = {'alerts': other_alerts}
            enriched_alert = self.enrich_alert(other_alerts_payload)
            try:
                self.send_to_slack(enriched_alert)
                self.alerts_successful += len(other_alerts)
            except Exception as e:
                self.alerts_failed += len(other_alerts)
                self.logger.error("Failed to send enriched alerts to Slack: %s", e)
                raise

    def send_to_slack(self, alert):
        headers = {'Content-Type': 'application/json'}
        errors = []

        for alert_item in alert['alerts']:
            color = 'good' if alert_item['status'] == 'resolved' else 'danger'
            message = {
                "attachments": [
                    {
                        "color": color,
                        "text": (
                            f"Alert: {alert_item['annotations']['description']}\n"
                            f"Status: {alert_item['status']}\n"
                            f"Priority: {alert_item['labels'].get('priority', 'N/A')}\n"
                            f"Pod: {alert_item['labels']['pod']}\n"
                            f"Namespace: {alert_item['labels']['namespace']}\n"
                            f"Enriched Data: {alert_item.get('enriched_data', '')}"
                        )
                    }
                ]
            }
            response = requests.post(self.SLACK_WEBHOOK_URL, headers=headers, data=json.dumps(message))
            if response.status_code != 200:
                self.logger.error("Failed to send alert to Slack: %s", response.text)
                errors.append({
                    'alert': alert_item,
                    'status_code': response.status_code,
                    'response_text': response.text
                })

        if errors:
            error_messages = [
                f"Alert: {err['alert']['annotations']['description']} returned an error {err['status_code']}:\n{err['response_text']}"
                for err in errors
            ]
            raise ValueError(f"Some requests to Slack failed:\n" + "\n".join(error_messages))
    def get_metrics(self):
        return {
            'alerts_processed': self.alerts_processed,
            'alerts_successful': self.alerts_successful,
            'alerts_failed': self.alerts_failed
        }
