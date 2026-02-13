import asyncio
import json

from websockets import serve

connected_clients = set()
last_state = {}

async def _broadcast_current():
    """Send current state to all connected clients."""
    global connected_clients
    if not last_state or not connected_clients:
        return
    message = json.dumps(last_state)
    dead = set()
    for client in connected_clients:
        try:
            await client.send(message)
        except Exception:
            dead.add(client)
    connected_clients -= dead

async def handler(websocket):
    """One-way handler: sends state to client, no incoming messages expected."""
    global connected_clients
    connected_clients.add(websocket)

    if last_state:
        await websocket.send(json.dumps(last_state))

    try:
        await websocket.wait_closed()
    finally:
        connected_clients.discard(websocket)

async def broadcast(data):
    global last_state
    last_state = data
    await _broadcast_current()

async def run_websocket_server():
    async with serve(handler, "127.0.0.1", 8765):
        print("[WS] Listening on ws://localhost:8765")
        while True:
            await asyncio.sleep(1)
