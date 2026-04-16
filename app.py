from flask import Flask, request, jsonify
import os
import json
from UserReports import Report

app = Flask(__name__)

@app.route('/generate-report', methods=['POST'])
def generate_report_endpoint():
    data = request.get_json()

    # Validate input
    if not data or 'token' not in data:
        return jsonify({"error": "Token is required"}), 400

    user_token = data['token']

    try:
        # Generate report (string JSON)
        report_text = Report(user_token)

        # Convert string → JSON object
        report_json = json.loads(report_text)

        return jsonify({
            "status": "success",
            "data": report_json
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))