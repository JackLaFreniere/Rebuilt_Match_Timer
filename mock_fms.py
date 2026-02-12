import time
import threading

class MockFMS:
    def __init__(self, on_update):
        self.on_update = on_update
        self.running = False
        self.match_thread = None
        
        # Match settings
        self.event_name = "Mock Event"
        self.match_number = 1
        self.match_type = 2  # Qualification
        self.is_red_alliance = True
        self.game_specific_message = ""
        
        # State
        self.ds_attached = False
        self.enabled = False
        self.autonomous = False
        self.match_time = 0.0
    
    def get_state(self):
        return {
            "EventName": self.event_name,
            "MatchNumber": self.match_number,
            "MatchType": self.match_type,
            "isRedAlliance": self.is_red_alliance,
            "GameSpecificMessage": self.game_specific_message,
            "DSAttatched": self.ds_attached,
            "Enabled": self.enabled,
            "Autonomous": self.autonomous,
            "MatchTime": self.match_time,
        }
    
    def broadcast(self):
        self.on_update(self.get_state())
    
    def connect_ds(self):
        self.ds_attached = True
        self.broadcast()
    
    def disconnect_ds(self):
        self.ds_attached = False
        self.enabled = False
        self.autonomous = False
        self.broadcast()
    
    def set_alliance(self, is_red: bool):
        self.is_red_alliance = is_red
        self.broadcast()
    
    def set_event(self, name: str):
        self.event_name = name
        self.broadcast()
    
    def set_match_number(self, number):
        self.match_number = number
        self.broadcast()

    def start_match(self, first_off:str = ""):
        """Start a full match. first_off='b'|'r' or '' for no GSM."""

        if self.match_thread and self.match_thread.is_alive():
            return
        
        self.running = True
        self.match_thread = threading.Thread(
            target=self._run_match, args=(first_off,), daemon=True
        )
        self.match_thread.start()
    
    def stop_match(self):
        self.running = False
        self.enabled = False
        self.autonomous = False
        self.game_specific_message = ""
        self.broadcast()
    
    def _countdown(self, start, end=0.0):
        """Count MatchTime from start to end using wall-clock time at ~50Hz."""
        t0 = time.monotonic()
        duration = start - end
        while self.running:
            elapsed = time.monotonic() - t0
            if elapsed >= duration:
                self.match_time = end
                self.broadcast()
                return
            self.match_time = start - elapsed
            self.broadcast()
            time.sleep(0.02)

    def _wait(self, seconds):
        """Wait for a fixed duration, checking for stop."""
        deadline = time.monotonic() + seconds
        while self.running and time.monotonic() < deadline:
            time.sleep(0.02)

    def _run_match(self, first_off):
        """Full match: Auto(20s) -> Transition(3s) -> Teleop(140s) -> End."""
        # Auto
        self.enabled = True
        self.autonomous = True
        self._countdown(20.0)
        if not self.running:
            return

        # Transition (disabled period between auto and teleop)
        self.enabled = False
        self.match_time = 0.0
        self.broadcast()
        self._wait(3.0)
        if not self.running:
            return

        # Teleop (140s: 10s both hubs -> 4x25s alternating -> 30s endgame)
        self.enabled = True
        self.autonomous = False
        if first_off:
            self.game_specific_message = first_off
        self._countdown(140.0)
        if not self.running:
            return

        # Match end
        self.enabled = False
        self.match_time = 0.0
        self.broadcast()


def run_control_loop(mock: MockFMS):
    """CLI control for the mock FMS."""
    time.sleep(0.5)

    print("\n========== Mock FMS Control ==========")
    print("  c        - Connect DS")
    print("  d        - Disconnect DS")
    print("  r        - Set Red Alliance")
    print("  b        - Set Blue Alliance")
    print("  s [b|r|\"\"]  - Start match)")
    print("  x        - Stop match")
    print("  e <name> - Set event name")
    print("  m <num>  - Set match number")
    print("  q        - Quit")
    print("======================================\n")

    while True:
        try:
            cmd = input("> ").strip()
            if not cmd:
                continue

            parts = cmd.split(maxsplit=1)
            key = parts[0]
            arg = parts[1].strip() if len(parts) > 1 else ""

            if key == "c":
                mock.connect_ds()
                print("DS Connected")
            elif key == "d":
                mock.disconnect_ds()
                print("DS Disconnected")
            elif key == "r":
                mock.set_alliance(True)
                print("Red Alliance")
            elif key == "b":
                mock.set_alliance(False)
                print("Blue Alliance")
            elif key == "s":
                mock.start_match(arg)
                print("Match started" + (f" ({arg} off first)" if arg else " (no GSM)"))
            elif key == "x":
                mock.stop_match()
                print("Match stopped")
            elif key == "e" and arg:
                mock.set_event(arg)
                print(f"Event: {arg}")
            elif key == "m" and arg:
                mock.set_match_number(int(arg))
                print(f"Match #{arg}")
            elif key == "q":
                break
            else:
                print("Unknown command")
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
