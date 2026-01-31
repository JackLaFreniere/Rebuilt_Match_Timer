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

def buildState(subscribers: dict):
    state = {}
    for sub in subscribers:
        key = sub.getTopic().getName()[9:]
        state[key] = sub.get()
    
    return state

def run(on_update: function):
    global table

    inst = ntcore.NetworkTableInstance.getDefault()
    table = inst.getTable("FMSInfo")
    subscribers = getSubscribers()

    inst.startClient4("example client")
    inst.setServerTeam(930)
    inst.startDSClient()
    
    last_state = None
    while True:
        time.sleep(0.02) #20 milliseconds
        current = buildState(subscribers)

        if last_state != current:
            last_state = current
            on_update(current)
