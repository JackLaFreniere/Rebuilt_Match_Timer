import asyncio
import json
from websockets import serve

connected_clients = set()
last_state = {}

async def handler(websocket):
    global last_state, connected_clients
    connected_clients.add(websocket)
    
    if last_state:
        await websocket.send(json.dumps(last_state))
    
    try:
        async for message in websocket:
            pass  # We don't need to handle incoming messages from browser
    except Exception:
        pass
    finally:
        connected_clients.discard(websocket)

async def broadcast(data):
    global last_state, connected_clients
    last_state = data
    
    if not connected_clients:
        return
    
    message = json.dumps(data)
    dead = set()
    for client in connected_clients:
        try:
            await client.send(message)
        except Exception:
            dead.add(client)
    connected_clients -= dead

async def run_websocket_server():
    async with serve(handler, "127.0.0.1", 8765):
        print("[WS] Listening on ws://localhost:8765")
        while True:
            await asyncio.sleep(1)
