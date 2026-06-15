"""
SEC Scanner - Cloud web server.
Serves the dashboard and provides a /refresh endpoint to pull fresh data.
"""
import os
import subprocess
from pathlib import Path
from flask import Flask, send_from_directory, jsonify

ROOT      = Path(__file__).resolve().parent
DASHBOARD = ROOT / "outputs" / "dashboard"

app = Flask(__name__)


@app.route("/")
def index():
    return send_from_directory(str(DASHBOARD), "index.html")


@app.route("/style.css")
def style():
    return send_from_directory(str(DASHBOARD), "style.css")


@app.route("/data/<filename>")
def data(filename):
    return send_from_directory(str(DASHBOARD / "data"), filename)


@app.route("/refresh")
def refresh():
    """Pull fresh data from FMP + SEC and rebuild the dashboard."""
    env = {**os.environ}
    if not env.get("FMP_API_KEY"):
        return jsonify({"status": "error", "message": "FMP_API_KEY not set"}), 500
    try:
        subprocess.run(
            ["python", str(ROOT / "scripts" / "live-pull.py")],
            env=env, check=True, timeout=180
        )
        subprocess.run(
            ["python", str(ROOT / "scripts" / "gen-screener.py")],
            env=env, check=True, timeout=60
        )
        subprocess.run(
            ["python", str(ROOT / "outputs" / "dashboard" / "render.py")],
            env=env, check=True, timeout=60
        )
        return jsonify({"status": "ok", "message": "Dashboard refreshed with latest data"})
    except subprocess.CalledProcessError as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    except subprocess.TimeoutExpired:
        return jsonify({"status": "error", "message": "Refresh timed out"}), 504


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
