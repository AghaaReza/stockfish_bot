#!/usr/bin/env python3
import os
import subprocess
import json
import time
from typing import Optional
from functools import wraps

import requests
from flask import Flask, render_template, request, redirect, url_for, jsonify

app = Flask(__name__)

BASE_DIR = os.path.dirname(__file__)
BOT_SCRIPT = os.path.join(BASE_DIR, "bot.py")
LOG_FILE = os.path.join(BASE_DIR, "app.log")
BOT_STATE_FILE = os.path.join(BASE_DIR, "bot_state.json")

# Global state
bot_process: Optional[subprocess.Popen] = None
current_level: int = 20  # default level

# API key for /api/... endpoints
API_KEY = os.getenv("BOT_PANEL_API_KEY")


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
    env["STOCKFISH_PATH"] = "/usr/games/stockfish"

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


def get_recent_logs(max_lines: int = 200):
    """Return last N lines from the log file as a list of strings."""
    if not os.path.exists(LOG_FILE):
        return []

    try:
        with open(LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        return lines[-max_lines:]
    except Exception:
        return []


def read_bot_state():
    """Read the shared bot_state.json written by bot.py."""
    if not os.path.exists(BOT_STATE_FILE):
        return None
    try:
        with open(BOT_STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception:
        return None


def fetch_bot_stats(max_recent_games: int = 20):
    """
    Fetch stats from Lichess using the same LICHESS_TOKEN.
    Returns a dict or None on error.
    """
    token = os.getenv("LICHESS_TOKEN")
    if not token:
        return None

    try:
        auth_header = {"Authorization": f"Bearer {token}"}

        # Account info: total games, perfs, username
        acc_resp = requests.get(
            "https://lichess.org/api/account",
            headers=auth_header,
            timeout=5,
        )
        acc_resp.raise_for_status()
        acc = acc_resp.json()

        username = acc.get("username")
        total_games = acc.get("count", {}).get("all")
        perfs = acc.get("perfs", {}) or {}

        ratings = {
            "bullet": (perfs.get("bullet") or {}).get("rating"),
            "blitz": (perfs.get("blitz") or {}).get("rating"),
            "rapid": (perfs.get("rapid") or {}).get("rating"),
        }

        # Last N games as NDJSON
        games_url = (
            f"https://lichess.org/api/games/user/{username}"
            f"?max={max_recent_games}&moves=false&evals=false&opening=false"
        )
        headers = {
            **auth_header,
            "Accept": "application/x-ndjson",
        }

        games_resp = requests.get(
            games_url,
            headers=headers,
            timeout=10,
            stream=True,
        )
        games_resp.raise_for_status()

        wins = losses = draws = 0
        last_games = []

        for line in games_resp.iter_lines(decode_unicode=True):
            if not line:
                continue
            try:
                g = json.loads(line)
            except Exception:
                continue

            game_id = g.get("id")
            perf = g.get("perf") or g.get("perfType")
            players = g.get("players", {}) or {}
            winner = g.get("winner")
            status = (g.get("status") or "").lower()

            # Find our color and opponent name
            color = None
            opponent_name = None
            for c in ("white", "black"):
                p = players.get(c, {}) or {}
                user = p.get("user") or {}
                name = user.get("name") or user.get("username")
                if not name:
                    continue
                if username and name.lower() == username.lower():
                    color = c
                else:
                    opponent_name = opponent_name or name

            # Determine result from our point of view
            if winner is None:
                if status in {
                    "draw",
                    "stalemate",
                    "timevsinsufficient",
                    "repetition",
                    "agreed",
                    "50move",
                    "insufficient",
                    "threefold",
                }:
                    result = "draw"
                    draws += 1
                else:
                    result = "unknown"
            else:
                if color and winner == color:
                    result = "win"
                    wins += 1
                elif color and winner != color:
                    result = "loss"
                    losses += 1
                else:
                    result = "unknown"

            last_games.append(
                {
                    "id": game_id,
                    "perf": perf,
                    "result": result,
                    "opponent": opponent_name,
                    "status": status,
                }
            )

        return {
            "username": username,
            "total_games": total_games,
            "ratings": ratings,
            "recent": {
                "games_analyzed": len(last_games),
                "wins": wins,
                "losses": losses,
                "draws": draws,
                "last_games": last_games,
            },
        }

    except Exception as e:
        print("Error fetching bot stats:", e)
        return None


def require_api_key(f):
    """
    Decorator to protect API endpoints with X-API-Key.
    If BOT_PANEL_API_KEY is not set, no auth is enforced.
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not API_KEY:
            return f(*args, **kwargs)
        key = request.headers.get("X-API-Key")
        if key != API_KEY:
            return jsonify({"ok": False, "error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return wrapper


# ----------------- HTML control panel routes ----------------- #

@app.route("/bot/", methods=["GET"])
def index():
    logs = get_recent_logs(200)
    game_state = read_bot_state()
    stats = fetch_bot_stats()

    return render_template(
        "control.html",
        running=is_bot_running(),
        current_level=current_level,
        logs=logs,
        game=game_state,
        stats=stats,
    )


@app.route("/start", methods=["POST"])
def start_bot():
    global current_level

    level_str = request.form.get("level")
    lvl = _validate_level(level_str)
    if lvl is not None:
        current_level = lvl

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

    if is_bot_running():
        _stop_bot_process()
        _spawn_bot_process()

    return redirect(url_for("index"))


@app.route("/restart", methods=["POST"])
def restart_bot():
    """
    Restart the bot from the web page.
    """
    if is_bot_running():
        _stop_bot_process()
    _spawn_bot_process()
    return redirect(url_for("index"))


# ----------------- REST API routes ----------------- #

@app.route("/api/bot/status", methods=["GET"])
@app.route("/bot/api/bot/status", methods=["GET"])
@require_api_key
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
@require_api_key
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
@require_api_key
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
@require_api_key
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


@app.route("/api/bot/restart", methods=["POST"])
@app.route("/bot/api/bot/restart", methods=["POST"])
@require_api_key
def api_bot_restart():
    was_running = is_bot_running()
    if was_running:
        _stop_bot_process()
    _spawn_bot_process()
    pid = bot_process.pid if is_bot_running() else None

    return jsonify({
        "ok": True,
        "restarted": True,
        "was_running": was_running,
        "running": is_bot_running(),
        "level": current_level,
        "pid": pid,
    }), 200


@app.route("/api/logs/recent", methods=["GET"])
@app.route("/bot/api/logs/recent", methods=["GET"])
@require_api_key
def api_logs_recent():
    lines = get_recent_logs(200)
    return jsonify({
        "ok": True,
        "lines": lines,
    }), 200


@app.route("/api/bot/current_game", methods=["GET"])
@app.route("/bot/api/bot/current_game", methods=["GET"])
@require_api_key
def api_bot_current_game():
    state = read_bot_state() or {}
    running = is_bot_running()
    in_game = state.get("status") == "playing" and running

    return jsonify({
        "ok": True,
        "running": running,
        "in_game": in_game,
        "state": state,
    }), 200


@app.route("/api/bot/stats", methods=["GET"])
@app.route("/bot/api/bot/stats", methods=["GET"])
@require_api_key
def api_bot_stats():
    stats = fetch_bot_stats()
    if stats is None:
        return jsonify({
            "ok": False,
            "error": "Unable to fetch stats (check LICHESS_TOKEN).",
        }), 500

    return jsonify({
        "ok": True,
        "stats": stats,
    }), 200


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000)
