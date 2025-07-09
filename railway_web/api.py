from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# Config: change this to your local machine's public URL (via ngrok)
LOCAL_API_URL = os.environ.get("LOCAL_API_URL", "http://localhost:5000/api/scrape")

@app.route("/webhook", methods=["POST"])
def webhook_forward():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON received"}), 400

    try:
        response = requests.post(LOCAL_API_URL, json=data, timeout=10)
        return jsonify({
            "status": "forwarded",
            "local_response": response.json()
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)