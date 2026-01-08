from flask import Flask, render_template, jsonify
from flask_cors import CORS
import requests
import json
import config
from requests.auth import HTTPBasicAuth
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static")
)
CORS(app)  # Allow cross-origin requests if needed


dot_count = 0

# --- Routes ---
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/trigger_build", methods=["POST"])
def trigger_build():
    try:
        url = f"{config.JENKINS_URL}/job/{config.JOB_NAME}/build"
        response = requests.post(url, auth=HTTPBasicAuth(config.USER, config.API_TOKEN), timeout=5)
        return jsonify({"status": "success", "message": f"Build triggered: {response.status_code}"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


@app.route("/stop_build", methods=["POST"])
def stop_build():
    try:
        url = f"{config.JENKINS_URL}/job/{config.JOB_NAME}/lastBuild/api/json"
        response = requests.get(url, auth=HTTPBasicAuth(config.USER, config.API_TOKEN), timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("building", False):
                build_number = data.get("number", 0)
                stop_url = f"{config.JENKINS_URL}/job/{config.JOB_NAME}/{build_number}/stop"
                stop_response = requests.post(stop_url, auth=HTTPBasicAuth(config.USER, config.API_TOKEN), timeout=5)
                if stop_response.status_code in [200, 201, 302]:
                    return jsonify({"status": "success", "message": f"Build #{build_number} stopped"})
                else:
                    return jsonify({"status": "error", "message": f"Failed to stop build #{build_number}"})
            else:
                return jsonify({"status": "error", "message": "No running build"})
        else:
            return jsonify({"status": "error", "message": "Error fetching build info"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
        
@app.route("/console", methods=["GET"])
def console_output():
    try:
        url = f"{config.JENKINS_URL}/job/{config.JOB_NAME}/lastBuild/consoleText"
        response = requests.get(url, auth=HTTPBasicAuth(config.USER, config.API_TOKEN))

        if response.status_code != 200:
            return jsonify({
                "status": "error",
                "message": "Failed to fetch Jenkins console"
            })

        lines = response.text.splitlines()

        marker = "T E S T S"
        filtered_lines = []
        started = False

        for line in lines:
            if marker in line:
                started = True
            if started:
                filtered_lines.append(line)

        if not filtered_lines:
            return jsonify({
                "status": "success",
                "console": ["Waiting for Test Suite to start..."]
            })

        return jsonify({
            "status": "success",
            "console": filtered_lines
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        })

@app.route("/status", methods=["GET"])

def status():
    global dot_count
    try:
        url = f"{config.JENKINS_URL}/job/{config.JOB_NAME}/lastBuild/api/json"
        response = requests.get(url, auth=HTTPBasicAuth(config.USER, config.API_TOKEN), timeout=5)
        if response.status_code == 200:
            data = response.json()
            building = data.get("building", False)
            number = data.get("number", 0)
            result = data.get("result", "UNKNOWN")
            if building:
                dots = "." * (dot_count % 4)
                dot_count += 1
                return jsonify({"status": "running", "message": f"RUNNING (Build #{number}) {dots}", "color": "blue"})
            else:
                color = "green" if result == "SUCCESS" else "red"
                return jsonify({"status": "finished", "message": f"{result} (Build #{number})", "color": color})
        else:
            return jsonify({"status": "error", "message": "Error fetching build info", "color": "red"})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Error: {str(e)}", "color": "red"})


if __name__ == "__main__":
    app.run(host="localhost", port=5000)



