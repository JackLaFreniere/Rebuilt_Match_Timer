import asyncio
import json
from websockets import serve

# Keeps track of every browser tab currently connected
connected_clients = set()

# Caches the last state so new clients get it immediately on connect
last_state = None


async def handler(websocket):
    """Called once per client that connects. Keeps the connection alive."""
    connected_clients.add(websocket)
    print(f"[WS] Client connected ({len(connected_clients)} total)")

    # Send current state right away so the client isn't blank
    if last_state:
        await websocket.send(json.dumps(last_state))

    try:
        # Just keep the connection open — we don't expect the client to send us anything
        async for message in websocket:
            pass
    except Exception:
        pass
    finally:
        connected_clients.discard(websocket)
        print(f"[WS] Client disconnected ({len(connected_clients)} total)")


async def broadcast(data: dict):
    """Push data to every connected client. This is what nt_reader will call."""
    global last_state
    last_state = data

    if not connected_clients:
        return

    message = json.dumps(data)
    for client in list(connected_clients):
        try:
            await client.send(message)
        except Exception:
            connected_clients.discard(client)


async def run_websocket_server():
    """Starts the server. Runs forever."""
    async with serve(handler, "127.0.0.1", 8765):
        print("[WS] WebSocket server listening on ws://localhost:8765")
        await asyncio.Future()  # Keep it running
