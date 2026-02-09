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
        self.match_type = 2  # 2 = Qualification
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
    
    def set_alliance(self, is_red):
        self.is_red_alliance = is_red
        self.broadcast()
    
    def set_event(self, name):
        self.event_name = name
        self.broadcast()
    
    def set_match_number(self, number):
        self.match_number = number
        self.broadcast()

    def set_match_type(self, type):
        self.match_type = type
        self.broadcast()
    
    def start_match(self, first_off="b"):
        """Start a full match simulation. first_off = 'b' or 'r' for which hub turns off first."""
        if self.match_thread and self.match_thread.is_alive():
            return  # Already running
        
        self.running = True
        self.match_thread = threading.Thread(target=self._run_match, args=(first_off,), daemon=True)
        self.match_thread.start()
    
    def stop_match(self):
        self.running = False
        self.enabled = False
        self.autonomous = False
        self.game_specific_message = ""
        self.broadcast()
    
    def _run_match(self, first_off):
        """Runs the full match timing sequence."""
        tick = 0.02  # 50ms ticks
        
        # === AUTO (20 seconds) ===
        self.enabled = True
        self.autonomous = True
        self.match_time = 20.0
        self.broadcast()
        
        for _ in range(int(20 / tick)):
            if not self.running:
                return
            time.sleep(tick)
            self.match_time -= tick
            if self.match_time <= 0:
                self.match_time = 0.0
                self.broadcast()
                break
            self.broadcast()
        
        # === TRANSITION (~3 seconds) ===
        self.enabled = False
        self.autonomous = False
        self.match_time = 0.0
        self.broadcast()
        
        time.sleep(3.0)
        if not self.running:
            return
        
        # === TELEOP START ===
        self.enabled = True
        self.autonomous = False
        self.match_time = 140.0  # 2:20
        
        # Send GSM
        self.game_specific_message = first_off
        self.broadcast()
        
        for _ in range(int(10 / tick)):
            if not self.running:
                return
            time.sleep(tick)
            self.match_time -= tick
            if self.match_time <= 130:
                self.match_time = 130.0
                self.broadcast()
                break
            self.broadcast()

        # === ALTERNATING PERIODS (4x 25 seconds = 100 seconds) ===
        for period in range(4):
            if not self.running:
                return
            
            for _ in range(int(25 / tick)):
                if not self.running:
                    return
                time.sleep(tick)
                self.match_time -= tick
                # Check if we've reached the next phase boundary
                if self.match_time <= 30 or (period == 3 and self.match_time <= 30):
                    break
                self.broadcast()
        
        # === ENDGAME (30 seconds) ===
        # Still in teleop mode, just final 30 seconds
        self.broadcast()
        
        for _ in range(int(30 / tick)):
            if not self.running:
                return
            time.sleep(tick)
            self.match_time -= tick
            if self.match_time <= 0:
                self.match_time = 0.0
                self.broadcast()
                break
            self.broadcast()
        
        # === MATCH END ===
        self.enabled = False
        self.autonomous = False
        self.match_time = 0.0
        self.broadcast()


# Control interface for the mock
def run_control_loop(mock: MockFMS):
    """Simple CLI control for the mock FMS."""
    import time
    time.sleep(0.5)  # Wait for other startup messages
    
    print("\n========== Mock FMS Control Panel ==========")
    print("Commands:")
    print("  c        - Connect DS")
    print("  d        - Disconnect DS")
    print("  r        - Set Red Alliance")
    print("  b        - Set Blue Alliance")
    print("  s [b|r]  - Start match (b=blue off first, r=red off first)")
    print("  x        - Stop match")
    print("  e <name> - Set event name")
    print("  m <num>  - Set match number")
    print("  t <num>  - Set match type")
    print("  q        - Quit")
    print("============================================\n")
    
    while True:
        try:
            cmd = input("> ").strip()
            if not cmd:
                continue
            
            if cmd == "c":
                mock.connect_ds()
                print("DS Connected")
            elif cmd == "d":
                mock.disconnect_ds()
                print("DS Disconnected")
            elif cmd == "r":
                mock.set_alliance(True)
                print("Set to Red Alliance")
            elif cmd == "b":
                mock.set_alliance(False)
                print("Set to Blue Alliance")
            elif cmd.startswith("s"):
                parts = cmd.split()
                first_off = parts[1] if len(parts) > 1 else "b"
                mock.start_match(first_off)
                print(f"Match started ({first_off} hub off first)")
            elif cmd == "x":
                mock.stop_match()
                print("Match stopped")
            elif cmd.startswith("e "):
                name = cmd[2:].strip()
                mock.set_event(name)
                print(f"Event: {name}")
            elif cmd.startswith("m "):
                num = int(cmd[2:].strip())
                mock.set_match_number(num)
                print(f"Match: {num}")
            elif cmd.startswith("t "):
                num = int(cmd[2:].strip())
                mock.set_match_type(num)
                print(f"Match: {num}")
            elif cmd == "q":
                break
            else:
                print("Unknown command")
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
