import asyncio
import threading
import queue
import sys
from ws_server import run_websocket_server, broadcast
from http_server import run_http_server
import nt_reader

data_queue = queue.Queue()
sim_mode = "--sim" in sys.argv

def on_update(data):
    data_queue.put(data)

async def queue_processor():
    while True:
        try:
            data = data_queue.get_nowait()
            await broadcast(data)
        except queue.Empty:
            pass
        await asyncio.sleep(0.01)

async def main():
    thread = threading.Thread(target=nt_reader.run, args=(on_update, sim_mode), daemon=True)
    thread.start()

    await asyncio.gather(
        run_websocket_server(),
        run_http_server(),
        queue_processor(),
    )

if __name__ == "__main__":
    asyncio.run(main())