import uuid
from flask import Flask, request, jsonify, render_template
import requests
from datetime import datetime

app = Flask(__name__)

def send_single(app_token, event_token, device_id, is_ios, use_s2s):
    url = "https://app.adjust.com/event"

    data = {
        "app_token": app_token,
        "event_token": event_token,
        "environment": "production",
        "currency": "USD",
        "revenue": "4.99"
    }

    if is_ios:
        data["idfa"] = device_id
    else:
        data["gps_adid"] = device_id
        data["android_uuid"] = str(uuid.uuid4())
        data["google_app_set_id"] = str(uuid.uuid4())

    if use_s2s:
        data["s2s"] = "1"

    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    response = requests.post(url, data=data, headers=headers)
    return response.status_code, response.text


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/send-now", methods=["POST"])
def send_now():
    data = request.get_json()

    app_token = data.get("app_token")
    event_token = data.get("event_token")
    device_id = data.get("device_id")
    is_ios = data.get("is_ios")
    use_s2s = data.get("use_s2s")

    if not app_token or not event_token or not device_id:
        return jsonify({"error": "Missing fields"}), 400

    try:
        status, body = send_single(app_token, event_token, device_id, is_ios, use_s2s)
        return jsonify({
            "status": status,
            "response": body,
            "time": datetime.now().strftime("%H:%M:%S")
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
