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

def run(on_update, sim_mode=False):
    global table_fms, table_driver_station

    inst = ntcore.NetworkTableInstance.getDefault()
    table_fms = inst.getTable("FMSInfo")
    table_driver_station = inst.getTable("AdvantageKit/DriverStation")

    subscribers = getSubscribers()

    inst.startClient4("match_timer")
    
    if sim_mode:
        inst.setServer("127.0.0.1")
        print("[NT] Connecting to simulation on localhost")
    else:
        inst.setServerTeam(930)
        inst.startDSClient()
        print("[NT] Connecting to Team 930 robot")

    last_state = None

    while True:
        time.sleep(0.02)
        current = build_state(subscribers)

        if current != last_state:
            on_update(current)
            last_state = current.copy()

if __name__ == "__main__":
    import sys
    sim = "--sim" in sys.argv
    run(print, sim_mode=sim)