# Project: Lichess Stockfish Bot + Control Panel

## Overview

- Python Lichess bot using:
  - `berserk` for Lichess API
  - `python-chess` for board/engine
  - Stockfish at `/usr/games/stockfish`
- Bot file: `bot.py`
- Web control panel: `control_panel.py` (Flask)
- Template: `templates/control.html`
- Logs: `app.log`
- Virtualenv: `venv/` (Python 3.12)

## Server Setup

- OS: Ubuntu (user: reza)
- Project folder: `/home/reza/projects/stockfish_bot`
- Flask runs on: `127.0.0.1:8000`
- systemd service: `/etc/systemd/system/bot-panel.service`
- Nginx domain: `https://mazehkhor.com`
- Control panel URL: `https://mazehkhor.com/bot/`

Nginx routes:
- `/bot/` → proxied to Flask (panel)
- `/start`, `/stop`, `/set_level` → proxied to Flask (form actions)

## Current Features

- Start/stop the Lichess bot from the web panel.
- Change Stockfish skill level (0–20) via the panel.
- Bot auto-reconnects to Lichess if the event stream fails.
- Bot logs to `app.log`.

## Next Goals

- Add a REST API to control the bot:
  - e.g. `/api/bot/status`, `/api/bot/start`, `/api/bot/stop`, `/api/bot/level`
- Possibly improve UI and add auth later.

## How to talk to ChatGPT about this project

When starting a new chat, I will paste something like:

> I’m working on a project in `/home/reza/projects/stockfish_bot`. It’s a Lichess Stockfish bot (`bot.py`) with a Flask control panel (`control_panel.py`) behind Nginx at `https://mazehkhor.com/bot/`. There’s a systemd service `bot-panel.service` running the panel. Please read this context and then help me extend the project (e.g. add REST API endpoints to control the bot). The project context is:
>
> (then paste this file’s content or summary)
