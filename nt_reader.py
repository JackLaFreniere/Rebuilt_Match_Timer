import ntcore
import time

def getInfo(keys: dict, key: str):
    match keys[key]:
        case "str":
            return table.getStringTopic(key).subscribe("default")
        case "int":
            return table.getIntegerTopic(key).subscribe(-1)
        case "bool":
            return table.getBooleanTopic(key).subscribe(False)

def getSubscribers():
    keys = {
        ".type": "str",
        "EventName": "str",
        "GameSpecificMessage": "str",
        "isRedAlliance": "bool",
        "MatchNumber": "int",
        "MatchType": "int"
    }
    subscribers = []
    for key in keys:
        subscribers.append(getInfo(keys, key))

    return subscribers

def build_state(subscribers):
    state = {}
    for sub in subscribers:
        key = sub.getTopic().getName()[9:]  # strips "/FMSInfo/"
        state[key] = sub.get()
    return state

def run(on_update):
    global table

    inst = ntcore.NetworkTableInstance.getDefault()
    table = inst.getTable("FMSInfo")
    subscribers = getSubscribers()

    inst.startClient4("example client")
    inst.setServerTeam(930)
    inst.startDSClient()

    last_state = None

    while True:
        time.sleep(0.02)
        current = build_state(subscribers)

        if current != last_state:
            on_update(current)
            last_state = current.copy()
            print(current)


if __name__ == "__main__":
    # When run directly, just print. This is your test mode.
    run(print)

# import ntcore
# import time


# def getInfo(keys: dict, key: str):
#     match keys[key]:
#         case "str":
#             return fms_table.getStringTopic(key).subscribe("default")
#         case "int":
#             return fms_table.getIntegerTopic(key).subscribe(-1)
#         case "bool":
#             return fms_table.getBooleanTopic(key).subscribe(False)


# def getDoubleSub(table, key: str):
#     return table.getDoubleTopic(key).subscribe(-1.0)


# def getBoolSub(table, key: str):
#     return table.getBooleanTopic(key).subscribe(False)


# def getSubscribers():
#     keys = {
#         ".type": "str",
#         "EventName": "str",
#         "GameSpecificMessage": "str",
#         "isRedAlliance": "bool",
#         "MatchNumber": "int",
#         "MatchType": "int"
#     }
#     subscribers = []
#     for key in keys:
#         subscribers.append(getInfo(keys, key))

#     return subscribers


# def build_state(fms_subs, ds_subs, state_tracker):
#     state = {}

#     # Read FMSInfo table
#     for sub in fms_subs:
#         key = sub.getTopic().getName()[9:]  # strips "/FMSInfo/"
#         state[key] = sub.get()

#     # Read AdvantageKit/DriverStation values
#     ds_attached = ds_subs["DSAttached"].get()
#     enabled = ds_subs["Enabled"].get()
#     match_time = ds_subs["MatchTime"].get()

#     state["DSAttached"] = ds_attached
#     state["Enabled"] = enabled
#     state["MatchTime"] = match_time

#     # --- State machine logic ---
#     prev = state_tracker["phase"]

#     if not ds_attached:
#         state_tracker["phase"] = "WAITING"
#         state_tracker["saw_auto"] = False
#         state_tracker["saw_teleop"] = False

#     elif not enabled:
#         if state_tracker["saw_teleop"]:
#             # Was in teleop and now disabled = match ended
#             state_tracker["phase"] = "MATCH_END"
#             state_tracker["saw_auto"] = False
#             state_tracker["saw_teleop"] = False
#         elif state_tracker["saw_auto"]:
#             # Was in auto and now disabled = transition period
#             state_tracker["phase"] = "TRANSITION"
#         else:
#             # Haven't seen a match yet, just waiting
#             state_tracker["phase"] = "WAITING"

#     elif enabled:
#         if not state_tracker["saw_auto"] and 0 <= match_time <= 20:
#             # First time seeing enabled + time in auto range = auto started
#             state_tracker["phase"] = "AUTO"
#             state_tracker["saw_auto"] = True
#         elif state_tracker["saw_auto"] and match_time > 20:
#             # Saw auto before, now time is above 20 = teleop started
#             state_tracker["phase"] = "TELEOP"
#             state_tracker["saw_teleop"] = True

#     # Pass phase and match time to frontend
#     state["phase"] = state_tracker["phase"]

#     return state

# def run(on_update):
#     global fms_table

#     inst = ntcore.NetworkTableInstance.getDefault()
#     fms_table = inst.getTable("FMSInfo")
#     ds_table = inst.getTable("AdvantageKit/DriverStation")

#     fms_subs = getSubscribers()

#     # AdvantageKit/DriverStation subscriptions
#     ds_subs = {
#         "DSAttached": getBoolSub(ds_table, "DSAttached"),
#         "Enabled": getBoolSub(ds_table, "Enabled"),
#         "MatchTime": getDoubleSub(ds_table, "MatchTime"),
#     }

#     # Tracks state across updates so we can detect transitions
#     state_tracker = {
#         "phase": "WAITING",
#         "saw_auto": False,
#         "saw_teleop": False,
#     }

#     inst.startClient4("example client")
#     inst.setServerTeam(930)
#     inst.startDSClient()

#     while True:
#         time.sleep(0.02)
#         current = build_state(fms_subs, ds_subs, state_tracker)
#         on_update(current)


# if __name__ == "__main__":
#     run(print)