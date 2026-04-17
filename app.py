import uuid
import threading
import time
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template
import requests

app = Flask(__name__)

jobs = {}
job_id_counter = 0
lock = threading.Lock()


def send_single(app_token, event_token, device_id, is_ios, use_s2s):
    url = "https://app.adjust.com/event"

    headers = {
        "accept-encoding": "gzip",
        "client-sdk": "android4.36.0",
        "connection": "Keep-Alive",
        "content-type": "application/x-www-form-urlencoded",
        "host": "app.adjust.com"
    }

    data = {
        "app_token": app_token,
        "event_token": event_token,
        "environment": "production",
        "created_at": "",
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

    r = requests.post(url, data=data, headers=headers)
    return r.status_code, r.text


def scheduler(job_id):
    job = jobs[job_id]

    while True:
        if job["cancelled"]:
            return

        now = datetime.now()
        remaining = (job["target"] - now).total_seconds()

        if remaining <= 0:
            break

        time.sleep(1)

    if job["cancelled"]:
        return

    status, body = send_single(
        job["app_token"],
        job["event_token"],
        job["device_id"],
        job["is_ios"],
        job["use_s2s"]
    )

    job["done"] = True
    job["result"] = "Success" if status == 200 else body


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/schedule", methods=["POST"])
def schedule():
    global job_id_counter

    data = request.get_json()

    app_token = data["app_token"]
    event_token = data["event_token"]
    device_id = data["device_id"]
    is_ios = data["is_ios"]
    use_s2s = data["use_s2s"]

    mode = data["mode"]

    if mode == "hours":
        hrs = float(data["hours"])
        target = datetime.now() + timedelta(hours=hrs)
    else:
        target = datetime.fromisoformat(data["datetime"])

    with lock:
        job_id_counter += 1
        jid = job_id_counter

        jobs[jid] = {
            "id": jid,
            "target": target,
            "app_token": app_token,
            "event_token": event_token,
            "device_id": device_id,
            "is_ios": is_ios,
            "use_s2s": use_s2s,
            "cancelled": False,
            "done": False,
            "result": ""
        }

    threading.Thread(target=scheduler, args=(jid,), daemon=True).start()

    return jsonify({"status": "scheduled"})


@app.route("/jobs")
def get_jobs():
    result = []

    for j in jobs.values():
        remaining = int((j["target"] - datetime.now()).total_seconds())
        if remaining < 0:
            remaining = 0

        result.append({
            "id": j["id"],
            "remaining": remaining,
            "done": j["done"],
            "result": j["result"]
        })

    return jsonify(result)


@app.route("/cancel/<int:jid>", methods=["POST"])
def cancel(jid):
    if jid in jobs:
        jobs[jid]["cancelled"] = True
        return jsonify({"status": "cancelled"})
    return jsonify({"error": "not found"}), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
