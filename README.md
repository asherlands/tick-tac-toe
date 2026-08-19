# Multiplayer Tic-Tac-Toe

A small two-player Tic-Tac-Toe game built with FastAPI, WebSockets, Jinja2, and vanilla JavaScript.

## Features

- Real-time two-player gameplay over a WebSocket connection
- Three marks per player, with the oldest mark removed for later moves
- Reset and disconnect handling
- Same-origin browser WebSocket protection
- Server-side validation of moves and game state

## Requirements

- Python 3.10 or newer

## Run locally

Create and activate a virtual environment, then install the dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Start the server:

```powershell
python -m uvicorn main:app --host 127.0.0.1 --port 8015
```

Open <http://127.0.0.1:8015> in two browser tabs.

On macOS or Linux, activate the environment with `source .venv/bin/activate`.

## LAN play

To allow other devices on the local network to connect, bind to all interfaces:

```powershell
python -m uvicorn main:app --host 0.0.0.0 --port 8015
```

Then open `http://YOUR-COMPUTER-IP:8015` from the other device. Only expose this on a trusted network and configure a firewall as needed.

## Security notes

This is a learning/demo application, not a production multiplayer service:

- There is no user authentication or authorization beyond the two active WebSocket player slots.
- Game state is held in process memory and is lost when the server restarts.
- There is no persistence, rate limiting, matchmaking, or abuse protection.
- For internet deployment, put the app behind HTTPS/WSS and a reverse proxy, add authentication and rate limiting, and review WebSocket origin and access policies for the hosting environment.
- Do not commit `.env` files, credentials, private keys, or generated logs. The included `.gitignore` excludes common sensitive and generated files.

## Project layout

```text
main.py              FastAPI application and game state
run                  Example local launcher
static/client.js     Browser WebSocket client
static/style.css     Browser styles
templates/index.html HTML page
```
