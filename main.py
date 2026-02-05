import asyncio
import threading
from ws_server import run_websocket_server, broadcast
from http_server import run_http_server
import nt_reader
import queue

# Thread-safe queue for passing data from NT thread to asyncio
data_queue = queue.Queue()

def on_update(data):
    data_queue.put(data)
    print(f"[Main] Queued data")

async def queue_processor():
    """Process data from the queue and broadcast to websocket clients"""
    while True:
        try:
            # Check queue without blocking
            data = data_queue.get_nowait()
            print(f"[Main] Processing queued data")
            await broadcast(data)
        except queue.Empty:
            pass
        await asyncio.sleep(0.01)  # Small delay to prevent busy loop

async def main():
    thread = threading.Thread(target=nt_reader.run, args=(on_update,), daemon=True)
    thread.start()

    # Run all tasks concurrently
    await asyncio.gather(
        run_websocket_server(),
        run_http_server(),
        queue_processor(),
    )

if __name__ == "__main__":
    asyncio.run(main())