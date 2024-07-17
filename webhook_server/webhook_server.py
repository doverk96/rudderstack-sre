from alert_manager import AlertManager
from flask import Flask, request, jsonify
import logging

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize AlertManager with the logger
alert_manager = AlertManager(logger)

# Route configuration
@app.route('/alert', methods=['POST'])
def receive_alert():
    alert = request.json
    try:
        alert_manager.process_alert(alert)
        return jsonify({"status": "success"}), 200
    except Exception as e:
        logger.error("Error processing alert: %s", e)
        return jsonify({"status": "failure", "error": str(e)}), 500

@app.route('/metrics', methods=['GET'])
def get_metrics():
    metrics = alert_manager.get_metrics()
    return jsonify(metrics), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
