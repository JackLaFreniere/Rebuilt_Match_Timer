import asyncio
import json

from websockets import serve

connected_clients = set()
last_state = {}
gsm_override = None

def _state_with_override(data: dict):
    """Return a copy of data with override field attached."""
    out = data.copy()
    out['GSMOverride'] = gsm_override
    return out

async def _broadcast_current():
    """Send current state (with override) to all connected clients."""
    global connected_clients
    if not last_state or not connected_clients:
        return
    message = json.dumps(_state_with_override(last_state))
    dead = set()
    for client in connected_clients:
        try:
            await client.send(message)
        except Exception:
            dead.add(client)
    connected_clients -= dead

async def handler(websocket):
    global gsm_override, connected_clients
    connected_clients.add(websocket)

    if last_state:
        await websocket.send(json.dumps(_state_with_override(last_state)))

    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                if data.get('type') == 'gsm_override':
                    value = data.get('value', '').lower()
                    if value in ('r', 'b'):
                        gsm_override = value
                        color = 'blue' if value == 'b' else 'red'
                        print(f"[WS] GSM Override set to '{value}' ({color} off first)")
                    elif value == 'clear':
                        gsm_override = None
                        print("[WS] GSM Override cleared")
                    else:
                        continue
                    await _broadcast_current()
            except json.JSONDecodeError:
                pass
            except Exception as e:
                print(f"[WS] Error: {e}")
    except Exception:
        pass
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
