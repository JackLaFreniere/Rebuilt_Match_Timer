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
        self.match_time = 0.0
        self.phase = "disconnected"
        
        # Hub state
        self.blue_hub_active = False
        self.red_hub_active = False
    
    def get_state(self):
        return {
            "EventName": self.event_name,
            "MatchNumber": self.match_number,
            "MatchType": self.match_type,
            "isRedAlliance": self.is_red_alliance,
            "GameSpecificMessage": self.game_specific_message,
            "DSAttached": self.ds_attached,
            "Enabled": self.enabled,
            "MatchTime": self.match_time,
            "phase": self.phase,
            "blueHubActive": self.blue_hub_active,
            "redHubActive": self.red_hub_active,
        }
    
    def broadcast(self):
        self.on_update(self.get_state())
    
    def connect_ds(self):
        self.ds_attached = True
        self.phase = "pre_match"
        self.broadcast()
    
    def disconnect_ds(self):
        self.ds_attached = False
        self.phase = "disconnected"
        self.enabled = False
        self.broadcast()
    
    def set_alliance(self, is_red):
        self.is_red_alliance = is_red
        self.broadcast()
    
    def set_event(self, name):
        self.event_name = name
        self.broadcast()
    
    def set_match(self, number, match_type=2):
        self.match_number = number
        self.match_type = match_type
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
        self.phase = "pre_match"
        self.blue_hub_active = False
        self.red_hub_active = False
        self.game_specific_message = ""
        self.broadcast()
    
    def _run_match(self, first_off):
        """Runs the full match timing sequence."""
        tick = 0.05  # 50ms ticks
        
        # === AUTO (20 seconds) ===
        self.phase = "auto"
        self.enabled = True
        self.blue_hub_active = True
        self.red_hub_active = True
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
        self.phase = "transition"
        self.enabled = False
        self.match_time = 0.0
        self.broadcast()
        
        time.sleep(3.0)
        if not self.running:
            return
        
        # === TELEOP START ===
        self.phase = "teleop"
        self.enabled = True
        self.match_time = 140.0  # 2:20
        
        # First 10 seconds: Both hubs on, send GSM
        self.game_specific_message = first_off
        self.blue_hub_active = True
        self.red_hub_active = True
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
        # first_off = "b" means blue turns off first
        blue_off_first = (first_off == "b")
        
        for period in range(4):
            if not self.running:
                return
            
            # Determine which hub is on this period
            # Period 0: first_off is off
            # Period 1: other is off
            # Period 2: first_off is off again
            # etc.
            if period % 2 == 0:
                # First hub off
                self.blue_hub_active = not blue_off_first
                self.red_hub_active = blue_off_first
            else:
                # Second hub off
                self.blue_hub_active = blue_off_first
                self.red_hub_active = not blue_off_first
            
            self.broadcast()
            
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
        self.phase = "endgame"
        self.blue_hub_active = True
        self.red_hub_active = True
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
        self.phase = "match_end"
        self.enabled = False
        self.match_time = 0.0
        self.blue_hub_active = False
        self.red_hub_active = False
        self.broadcast()


# Control interface for the mock
def run_control_loop(mock: MockFMS):
    """Simple CLI control for the mock FMS."""
    import time
    time.sleep(0.5)  # Wait for other startup messages
    
    print("\n=== Mock FMS Control Panel ===")
    print("Commands:")
    print("  c        - Connect DS")
    print("  d        - Disconnect DS")
    print("  r        - Set Red Alliance")
    print("  b        - Set Blue Alliance")
    print("  s [b|r]  - Start match (b=blue off first, r=red off first)")
    print("  x        - Stop match")
    print("  e <name> - Set event name")
    print("  m <num>  - Set match number")
    print("  q        - Quit")
    print("==============================\n")
    
    while True:
        try:
            cmd = input("> ").strip().lower()
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
                mock.set_match(num)
                print(f"Match: {num}")
            elif cmd == "q":
                break
            else:
                print("Unknown command")
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
