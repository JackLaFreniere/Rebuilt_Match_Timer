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

if __name__ == "__main__":
    run(print)