"""
ws_server.py — WebSocket Server

Manages connected browser clients. Exposes:
  - broadcast(data: dict)  → called by nt_reader to push updates to ALL clients
  - run_websocket_server() → the async server loop

Clients can also SEND data (used by the mock control panel). When a message
comes in from a client, it gets broadcast to all OTHER clients so the main
display picks it up.

On initial connection, the client receives the last known state immediately
so it's up to date even if it connects mid-match.
"""

import asyncio
import json
from websockets import serve

# Global set of all currently connected WebSocket clients
connected_clients: set = set()

# Last known state — sent to new clients on connect so they aren't blank
last_state: dict = {}

async def handler(websocket):
    """Handles a single browser client connection."""
    global last_state, connected_clients

    connected_clients.add(websocket)
    print(f"[WS] Client connected ({len(connected_clients)} total)")

    # Send the current state immediately so the client isn't blank on load
    if last_state:
        await websocket.send(json.dumps(last_state))

    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                last_state = data
                await broadcast_to_others(websocket, data)
            except json.JSONDecodeError:
                print("[WS] Bad JSON from client, ignoring.")
    except Exception:
        pass
    finally:
        connected_clients.discard(websocket)
        print(f"[WS] Client disconnected ({len(connected_clients)} total)")

async def broadcast_to_others(sender, data: dict):
    """Send data to every client EXCEPT the one that sent it."""
    global connected_clients
    message = json.dumps(data)
    dead = set()
    for client in connected_clients:
        if client is sender:
            continue
        try:
            await client.send(message)
        except Exception:
            dead.add(client)
    connected_clients -= dead

async def broadcast(data: dict):
    """
    Push a state update to every connected browser client.
    Called by nt_reader whenever new FMS data arrives.
    """
    global last_state, connected_clients
    last_state = data

    print(f"[WS] Broadcasting to {len(connected_clients)} clients")

    if not connected_clients:
        return

    message = json.dumps(data)
    dead = set()
    for client in connected_clients:
        try:
            await client.send(message)
            print(f"[WS] Sent to client successfully")
        except Exception as e:
            print(f"[WS] Failed to send: {e}")
            dead.add(client)
    connected_clients -= dead

async def run_websocket_server():
    """Starts the WebSocket server. Runs forever."""
    async with serve(handler, "127.0.0.1", 8765):
        print("[WS] WebSocket server listening on ws://localhost:8765")
        # Use a sleep loop instead of Future() to allow other coroutines to run
        while True:
            await asyncio.sleep(1)
