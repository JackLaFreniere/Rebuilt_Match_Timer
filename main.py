import nt_reader
import asyncio
import threading
import queue
import sys
from mock_fms import MockFMS, run_control_loop
from ws_server import run_websocket_server, broadcast
from http_server import run_http_server
from nt_reader import run

data_queue = queue.Queue()
mock_mode = "--mock" in sys.argv

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

def run_mock_control(mock):
    """Run the mock FMS control loop in a separate thread."""
    run_control_loop(mock)

def run_nt_reader(update):
    """Run the real FMS control look in a seperate thread."""
    run(update)

async def main():
    if mock_mode:
        # Use mock FMS instead of real NetworkTables
        mock = MockFMS(on_update)
        mock.broadcast()
        
        # Start control loop in main thread after servers start
        control_thread = threading.Thread(target=run_mock_control, args=(mock,), daemon=True)
        control_thread.start()
        
        print("[Main] Running in MOCK mode - use control commands to simulate")
    else:
        # Use real NetworkTables
        thread = threading.Thread(target=run_nt_reader, args=(on_update,), daemon=True)
        thread.start()
        
        print("[Main] Running in ROBOT mode - connecting to Team 930")

    await asyncio.gather(
        run_websocket_server(),
        run_http_server(),
        queue_processor(),
    )

if __name__ == "__main__":
    print("FRC 2026 Hub Status Display - Team 930")
    print()
    asyncio.run(main())