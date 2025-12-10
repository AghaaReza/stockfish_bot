#!/usr/bin/env python3
import os
import subprocess
from typing import Optional

from flask import Flask, render_template, request, redirect, url_for, jsonify

app = Flask(__name__)

BASE_DIR = os.path.dirname(__file__)
BOT_SCRIPT = os.path.join(BASE_DIR, "bot.py")
LOG_FILE = os.path.join(BASE_DIR, "app.log")

# Global state
bot_process: Optional[subprocess.Popen] = None
current_level: int = 20  # default level


def is_bot_running() -> bool:
    global bot_process
    return bot_process is not None and bot_process.poll() is None


# ----------------- helpers (shared by HTML + API) ----------------- #

def _validate_level(level_value) -> Optional[int]:
    """
    Parse and validate a skill level value. Return int 0–20 or None if invalid.
    """
    try:
        lvl = int(level_value)
    except (TypeError, ValueError):
        return None

    if 0 <= lvl <= 20:
        return lvl
    return None


def _spawn_bot_process() -> None:
    """
    Start the bot process using the current_level.
    Assumes we already checked that it's not running.
    """
    global bot_process, current_level

    env = os.environ.copy()
    # Override here so we IGNORE any bad systemd env
    env["STOCKFISH_PATH"] = "/usr/games/stockfish"  # or whatever `which stockfish` shows

    # Open log file and attach stdout/stderr
    log = open(LOG_FILE, "ab", buffering=0)
    bot_process = subprocess.Popen(
        ["/home/reza/projects/stockfish_bot/venv/bin/python", BOT_SCRIPT, str(current_level)],
        env=env,
        stdout=log,
        stderr=log,
    )


def _stop_bot_process() -> bool:
    """
    Stop the bot process if running. Return True if it was running, False otherwise.
    """
    global bot_process

    if not is_bot_running():
        bot_process = None
        return False

    bot_process.terminate()
    try:
        bot_process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        bot_process.kill()

    bot_process = None
    return True


# ----------------- HTML control panel routes ----------------- #

@app.route("/bot/", methods=["GET"])
def index():
    return render_template(
        "control.html",
        running=is_bot_running(),
        current_level=current_level,
    )


@app.route("/start", methods=["POST"])
def start_bot():
    global current_level

    # Read desired level from form
    level_str = request.form.get("level")
    lvl = _validate_level(level_str)
    if lvl is not None:
        current_level = lvl

    # Start only if not already running
    if not is_bot_running():
        _spawn_bot_process()

    return redirect(url_for("index"))


@app.route("/stop", methods=["POST"])
def stop_bot():
    _stop_bot_process()
    return redirect(url_for("index"))


@app.route("/set_level", methods=["POST"])
def set_level():
    """
    Change level; if bot is running, restart it with the new level.
    """
    global current_level

    level_str = request.form.get("level")
    lvl = _validate_level(level_str)
    if lvl is not None:
        current_level = lvl

    # If bot is running, restart with new level
    if is_bot_running():
        _stop_bot_process()
        _spawn_bot_process()

    return redirect(url_for("index"))


# ----------------- REST API routes ----------------- #

@app.route("/api/bot/status", methods=["GET"])
@app.route("/bot/api/bot/status", methods=["GET"])
def api_bot_status():
    pid = bot_process.pid if is_bot_running() else None

    return jsonify({
        "ok": True,
        "running": is_bot_running(),
        "level": current_level,
        "pid": pid,
    }), 200


@app.route("/api/bot/start", methods=["POST"])
@app.route("/bot/api/bot/start", methods=["POST"])
def api_bot_start():
    global current_level

    data = request.get_json(silent=True) or {}
    if "level" in data:
        lvl = _validate_level(data["level"])
        if lvl is None:
            return jsonify({
                "ok": False,
                "error": "Invalid 'level'. Must be integer 0–20."
            }), 400
        current_level = lvl

    if is_bot_running():
        started = False
    else:
        _spawn_bot_process()
        started = True

    pid = bot_process.pid if is_bot_running() else None

    return jsonify({
        "ok": True,
        "started": started,
        "running": is_bot_running(),
        "level": current_level,
        "pid": pid,
    }), 200


@app.route("/api/bot/stop", methods=["POST"])
@app.route("/bot/api/bot/stop", methods=["POST"])
def api_bot_stop():
    was_running = is_bot_running()
    _stop_bot_process()

    return jsonify({
        "ok": True,
        "stopped": was_running,
        "running": is_bot_running(),
        "level": current_level,
        "pid": None,
    }), 200


@app.route("/api/bot/level", methods=["GET", "POST"])
@app.route("/bot/api/bot/level", methods=["GET", "POST"])
def api_bot_level():
    global current_level

    if request.method == "GET":
        return jsonify({
            "ok": True,
            "level": current_level,
        }), 200

    data = request.get_json(silent=True) or {}
    if "level" not in data:
        return jsonify({
            "ok": False,
            "error": "Missing 'level' in JSON body."
        }), 400

    lvl = _validate_level(data["level"])
    if lvl is None:
        return jsonify({
            "ok": False,
            "error": "Invalid 'level'. Must be integer 0–20."
        }), 400

    current_level = lvl

    return jsonify({
        "ok": True,
        "level": current_level,
        "running": is_bot_running(),
    }), 200


if __name__ == "__main__":
    # No debug=True in production
    app.run(host="127.0.0.1", port=8000)
