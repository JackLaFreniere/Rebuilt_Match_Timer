import asyncio
import threading
import queue
import sys

from ws_server import run_websocket_server, broadcast
from http_server import run_http_server

data_queue = queue.Queue()

def on_update(data):
    data_queue.put(data)

async def queue_processor():
    while True:
        try:
            data = data_queue.get_nowait()
            broadcast(data)
        except queue.Empty:
            pass
        await asyncio.sleep(0.01)

async def main():
    if "--mock" in sys.argv:
        from mock_fms import MockFMS, run_control_loop
        mock = MockFMS(on_update)
        mock.broadcast()
        threading.Thread(target=run_control_loop, args=(mock,), daemon=True).start()
        print("[Main] Running in MOCK mode")
    else:
        from nt_reader import run
        threading.Thread(target=run, args=(on_update, TEAM_NUMBER), daemon=True).start()
        print(f"[Main] Connecting to Team {TEAM_NUMBER} robot")

    await asyncio.gather(
        run_websocket_server(),
        run_http_server(),
        queue_processor(),
    )

if __name__ == "__main__":
    TEAM_NUMBER = sys.argv[1]
    print(f"FRC 2026 Hub Timer - Team {TEAM_NUMBER}\n")
    asyncio.run(main())
