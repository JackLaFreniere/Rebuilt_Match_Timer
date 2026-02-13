import asyncio
import json

import websockets
from websockets import serve

_server = None
last_state = {}

async def handler(websocket):
    """One-way: send current state then wait for disconnect."""
    if last_state:
        try:
            await websocket.send(json.dumps(last_state))
        except Exception:
            return
    try:
        await websocket.wait_closed()
    except Exception:
        pass

def broadcast(data):
    """Broadcast data to all connected clients (non-blocking)."""
    global last_state
    last_state = data
    if _server is None:
        return
    clients = _server.connections
    if not clients:
        return
    try:
        websockets.broadcast(clients, json.dumps(data))
    except Exception as e:
        print(f"[WS] Broadcast error: {e}")

async def run_websocket_server():
    global _server
    async with serve(
        handler,
        "127.0.0.1",
        8765,
        ping_interval=5,
        ping_timeout=10,
        close_timeout=2,
    ) as server:
        _server = server
        print("[WS] Listening on ws://localhost:8765")
        await asyncio.Future()  # run forever
