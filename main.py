import asyncio
import threading
from ws_server import run_websocket_server, broadcast
from http_server import run_http_server
import nt_reader

loop = None

def on_update(data):
    asyncio.run_coroutine_threadsafe(broadcast(data), loop)

async def main():
    global loop
    loop = asyncio.get_event_loop()

    thread = threading.Thread(target=nt_reader.run, args=(on_update,), daemon=True)
    thread.start()

    # Run both servers concurrently
    await asyncio.gather(
        run_websocket_server(),
        run_http_server(),
    )

if __name__ == "__main__":
    asyncio.run(main())