import asyncio
import threading
import queue
import sys
from ws_server import run_websocket_server, broadcast
from http_server import run_http_server

data_queue = queue.Queue()
mock_mode = "--mock" in sys.argv
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

def run_mock_control(mock):
    """Run the mock FMS control loop in a separate thread."""
    from mock_fms import run_control_loop
    run_control_loop(mock)

async def main():
    if mock_mode:
        # Use mock FMS instead of real NetworkTables
        from mock_fms import MockFMS
        mock = MockFMS(on_update)
        
        # Send initial disconnected state
        mock.broadcast()
        
        # Start control loop in main thread after servers start
        control_thread = threading.Thread(target=run_mock_control, args=(mock,), daemon=True)
        control_thread.start()
        
        print("[Main] Running in MOCK mode - use control commands to simulate")
    else:
        # Use real NetworkTables
        import nt_reader
        thread = threading.Thread(target=nt_reader.run, args=(on_update, sim_mode), daemon=True)
        thread.start()
        
        if sim_mode:
            print("[Main] Running in SIMULATION mode - connecting to localhost")
        else:
            print("[Main] Running in ROBOT mode - connecting to Team 930")

    await asyncio.gather(
        run_websocket_server(),
        run_http_server(),
        queue_processor(),
    )

if __name__ == "__main__":
    print("Usage: python main.py [--mock | --sim]")
    print("  --mock : Use fake FMS data with manual control")
    print("  --sim  : Connect to WPILib simulation on localhost")
    print("  (none) : Connect to real robot")
    print()
    asyncio.run(main())