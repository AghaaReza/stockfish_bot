#!/usr/bin/env python3
import os
import subprocess
from typing import Optional

from flask import Flask, render_template, request, redirect, url_for

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


@app.route("/bot/", methods=["GET"])
def index():
    return render_template(
        "control.html",
        running=is_bot_running(),
        current_level=current_level,
    )


@app.route("/start", methods=["POST"])
def start_bot():
    global bot_process, current_level

    # Read desired level from form
    level_str = request.form.get("level")
    if level_str:
        try:
            lvl = int(level_str)
            if 0 <= lvl <= 20:
                current_level = lvl
        except ValueError:
            pass  # ignore bad input

    # Start only if not already running
    if not is_bot_running():
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

    return redirect(url_for("index"))


@app.route("/stop", methods=["POST"])
def stop_bot():
    global bot_process
    if is_bot_running():
        bot_process.terminate()
        try:
            bot_process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            bot_process.kill()
    bot_process = None
    return redirect(url_for("index"))


@app.route("/set_level", methods=["POST"])
def set_level():
    """
    Change level; if bot is running, restart it with the new level.
    """
    global current_level, bot_process

    level_str = request.form.get("level")
    if level_str:
        try:
            lvl = int(level_str)
            if 0 <= lvl <= 20:
                current_level = lvl
        except ValueError:
            pass

    # If bot is running, restart with new level
    if is_bot_running():
        bot_process.terminate()
        try:
            bot_process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            bot_process.kill()
        bot_process = None

        env = os.environ.copy()
        env["STOCKFISH_PATH"] = "/usr/games/stockfish"  # same as above
        log = open(LOG_FILE, "ab", buffering=0)
        bot_process = subprocess.Popen(
            ["/home/reza/projects/stockfish_bot/venv/bin/python", BOT_SCRIPT, str(current_level)],
            env=env,
            stdout=log,
            stderr=log,
        )

    return redirect(url_for("index"))


if __name__ == "__main__":
    # No debug=True in production
    app.run(host="127.0.0.1", port=8000)
