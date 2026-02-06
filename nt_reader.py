import ntcore
import time

def getInfo(table: ntcore.NetworkTable, key: str, val:str):
    match val:
        case "str":
            return table.getStringTopic(key).subscribe("default")
        case "int":
            return table.getIntegerTopic(key).subscribe(-1)
        case "double":
            return table.getDoubleTopic(key).subscribe(-1.0)
        case "bool":
            return table.getBooleanTopic(key).subscribe(False)

def getSubscribers():
    global table_fms, table_driver_station

    keys_fms = {
        ".type": "str",
        "EventName": "str",
        "isRedAlliance": "bool",
        "MatchNumber": "int",
        "MatchType": "int"
    }

    keys_driver_station = {
        "DSAttatched": "bool",
        "Autonomous": "bool",
        "Enabled": "bool",
        "MatchTime": "double",
        "GameSpecificMessage": "str"
    }

    subscribers = []
    for key in keys_fms:
        subscribers.append(getInfo(table_fms, key, keys_fms[key]))

    for key in keys_driver_station:
        subscribers.append(getInfo(table_driver_station, key, keys_driver_station[key]))

    return subscribers

def strip_name(sub: str):
    name = sub.getTopic().getName()[1:]
    while "/" in name:
        name = name[name.index("/") + 1:]

    return name

def build_state(subscribers):
    state = {}
    for sub in subscribers:
        key = strip_name(sub)
        state[key] = sub.get()
    return state

def compute_phase_and_hubs(state, tracker):
    """Compute match phase and hub states based on raw NT data."""
    ds_attached = state.get("DSAttatched", False)
    enabled = state.get("Enabled", False)
    autonomous = state.get("Autonomous", False)
    match_time = state.get("MatchTime", 0.0)
    gsm = state.get("GameSpecificMessage", "")
    
    # Handle GSM timing - lock in the value once we get it during the match
    if gsm and gsm in ["b", "r"]:
        if tracker.get("gsm_locked") != gsm:
            print(f"[NT] GameSpecificMessage received: {gsm} ({'blue' if gsm == 'b' else 'red'} off first)")
        tracker["gsm_locked"] = gsm
    locked_gsm = tracker.get("gsm_locked", "")
    
    # Determine phase
    if not ds_attached:
        phase = "disconnected"
        tracker["saw_auto"] = False
        tracker["saw_teleop"] = False
        tracker["gsm_locked"] = ""  # Reset GSM on disconnect
    elif not enabled:
        if tracker["saw_teleop"]:
            phase = "match_end"
        elif tracker["saw_auto"]:
            phase = "transition"
        else:
            phase = "pre_match"
            # Reset GSM at match start for safety
            if not tracker.get("saw_auto", False):
                tracker["gsm_locked"] = ""
    elif autonomous:
        phase = "auto"
        tracker["saw_auto"] = True
    else:
        # Teleop
        tracker["saw_teleop"] = True
        if match_time <= 30:
            phase = "endgame"
        else:
            phase = "teleop"
    
    state["phase"] = phase
    state["GameSpecificMessage"] = locked_gsm  # Use locked GSM for display
    
    # Compute hub states
    blue_on = False
    red_on = False
    
    if phase in ["auto", "transition"]:
        blue_on = True
        red_on = True
    elif phase in ["teleop", "endgame"]:
        if match_time > 130:
            # First 10 seconds of teleop - both on
            blue_on = True
            red_on = True
        elif match_time > 30:
            # Alternating periods
            elapsed = 130 - match_time
            period = int(elapsed // 25)
            
            # Use locked GSM, fallback to current alliance if no GSM available
            if locked_gsm:
                blue_off_first = (locked_gsm == "b")
            else:
                # Fallback: Use alliance color - your alliance turns off first
                # This is a reasonable guess when GSM is unavailable
                is_red_alliance = state.get("isRedAlliance", True)
                blue_off_first = not is_red_alliance
                print(f"[WARNING] No GameSpecificMessage available, using alliance fallback: {'blue' if blue_off_first else 'red'} off first")
            
            if period % 2 == 0:
                blue_on = not blue_off_first
                red_on = blue_off_first
            else:
                blue_on = blue_off_first
                red_on = not blue_off_first
        else:
            # Endgame - both on
            blue_on = True
            red_on = True
    
    state["blueHubActive"] = blue_on
    state["redHubActive"] = red_on
    
    return state

def run(on_update):
    global table_fms, table_driver_station

    inst = ntcore.NetworkTableInstance.getDefault()
    table_fms = inst.getTable("FMSInfo")
    table_driver_station = inst.getTable("AdvantageKit/DriverStation")

    subscribers = getSubscribers()

    inst.startClient4("match_timer")
    inst.setServerTeam(930)
    inst.startDSClient()
    print("[NT] Connecting to Team 930 robot")

    last_state = None
    tracker = {"saw_auto": False, "saw_teleop": False, "gsm_locked": ""}

    while True:
        time.sleep(0.02)
        current = build_state(subscribers)
        current = compute_phase_and_hubs(current, tracker)

        if current != last_state:
            on_update(current)
            last_state = current.copy()

if __name__ == "__main__":
    run(print)