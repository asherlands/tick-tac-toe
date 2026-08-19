from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import json

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_to(self, websocket: WebSocket, message: dict):
        await websocket.send_text(json.dumps(message))

    async def broadcast(self, message: dict):
        data = json.dumps(message)
        for connection in list(self.active_connections):
            try:
                await connection.send_text(data)
            except Exception:
                pass


manager = ConnectionManager()

GAME = {
    "board": [None] * 9,
    "players": [],
    "symbols": {},
    "turn": None,
    "running": False,

    "history": {
        "X": [],
        "O": []
    }
}


@app.get("/", response_class=HTMLResponse)
async def get(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    origin = websocket.headers.get("origin")
    host = websocket.headers.get("host")
    allowed_origins = {f"http://{host}", f"https://{host}"}
    if origin and origin not in allowed_origins:
        await websocket.close(code=1008, reason="Origin not allowed")
        return

    await manager.connect(websocket)
    ws_id = id(websocket)
    is_player = False

    try:
        if len(GAME["players"]) < 2:
            GAME["players"].append(ws_id)
            is_player = True

            symbol = "X" if len(GAME["players"]) == 1 else "O"
            GAME["symbols"][str(ws_id)] = symbol

            if len(GAME["players"]) == 2:
                GAME["turn"] = "X"
                GAME["running"] = True

            await manager.send_to(websocket, {
                "type": "init",
                "you": symbol,
                "board": GAME["board"],
                "running": GAME["running"],
                "turn": GAME["turn"],
            })

            await manager.broadcast({
                "type": "state",
                "board": GAME["board"],
                "running": GAME["running"],
                "turn": GAME["turn"],
                "players_count": len(GAME["players"]),
            })

        else:
            await manager.send_to(websocket, {"type": "full"})
            await websocket.close(code=1008, reason="Room full")
            return

        while True:
            text = await websocket.receive_text()
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                await manager.send_to(websocket, {
                    "type": "error",
                    "message": "Invalid message"
                })
                continue

            if not isinstance(data, dict) or ws_id not in GAME["players"]:
                await manager.send_to(websocket, {
                    "type": "error",
                    "message": "Invalid message"
                })
                continue

            if data.get("type") == "move":
                index = data.get("index")
                your_symbol = GAME["symbols"].get(str(ws_id))

                if isinstance(index, bool) or not isinstance(index, int):
                    await manager.send_to(websocket, {
                        "type": "error",
                        "message": "Invalid cell"
                    })
                    continue

                if not GAME["running"]:
                    await manager.send_to(websocket, {
                        "type": "error",
                        "message": "Game not running"
                    })
                    continue

                if your_symbol != GAME["turn"]:
                    await manager.send_to(websocket, {
                        "type": "error",
                        "message": "Not your turn"
                    })
                    continue

                if index < 0 or index > 8:
                    await manager.send_to(websocket, {
                        "type": "error",
                        "message": "Invalid cell"
                    })
                    continue

                if GAME["board"][index] is not None:
                    await manager.send_to(websocket, {
                        "type": "error",
                        "message": "Cell already occupied"
                    })
                    continue

                if len(GAME["history"][your_symbol]) == 3:
                    oldest = GAME["history"][your_symbol].pop(0)
                    GAME["board"][oldest] = None

                GAME["board"][index] = your_symbol
                GAME["history"][your_symbol].append(index)

                winner = check_winner(GAME["board"])

                if winner:
                    GAME["running"] = False

                    await manager.broadcast({
                        "type": "end",
                        "winner": winner,
                        "board": GAME["board"]
                    })

                else:
                    GAME["turn"] = "O" if GAME["turn"] == "X" else "X"

                    await manager.broadcast({
                        "type": "update",
                        "board": GAME["board"],
                        "turn": GAME["turn"]
                    })

            elif data.get("type") == "reset":

                GAME["board"] = [None] * 9

                GAME["history"] = {
                    "X": [],
                    "O": []
                }

                GAME["turn"] = "X" if len(GAME["players"]) == 2 else None
                GAME["running"] = len(GAME["players"]) == 2

                await manager.broadcast({
                    "type": "reset",
                    "board": GAME["board"],
                    "running": GAME["running"],
                    "turn": GAME["turn"]
                })

    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)

        if is_player and str(ws_id) in GAME["symbols"]:
            del GAME["symbols"][str(ws_id)]

        if is_player and ws_id in GAME["players"]:
            GAME["players"].remove(ws_id)

        if is_player:
            GAME["board"] = [None] * 9
            GAME["history"] = {"X": [], "O": []}
            GAME["running"] = False
            GAME["turn"] = None

            await manager.broadcast({
                "type": "player_left",
                "players_count": len(GAME["players"])
            })


WIN_LINES = [
    (0, 1, 2),
    (3, 4, 5),
    (6, 7, 8),
    (0, 3, 6),
    (1, 4, 7),
    (2, 5, 8),
    (0, 4, 8),
    (2, 4, 6)
]


def check_winner(board):
    for a, b, c in WIN_LINES:
        if board[a] and board[a] == board[b] == board[c]:
            return board[a]
    return None