import ntcore
import time

from ntcore import NetworkTable

FMS_KEYS = {
    "EventName": "str",
    "isRedAlliance": "bool",
    "MatchNumber": "int",
    "MatchType": "int",
}

DS_KEYS = {
    "DSAttatched": "bool",
    "Autonomous": "bool",
    "Enabled": "bool",
    "MatchTime": "double",
    "GameSpecificMessage": "str",
}

def _subscribe(table: NetworkTable, key: str, type_name: str):
    """Create a subscriber for a single NetworkTables key."""

    match type_name:
        case "str": return table.getStringTopic(key).subscribe("")
        case "int": return table.getIntegerTopic(key).subscribe(-1)
        case "double": return table.getDoubleTopic(key).subscribe(-1.0)
        case "bool": return table.getBooleanTopic(key).subscribe(False)

def _key_name(sub: NetworkTable) -> str:
    """Extract the leaf key name from a subscriber's topic path."""

    return sub.getTopic().getName().rsplit("/", 1)[-1]

def run(on_update, team_number):
    inst = ntcore.NetworkTableInstance.getDefault()
    table_fms = inst.getTable("FMSInfo")
    table_ds = inst.getTable("AdvantageKit/DriverStation")

    subscribers = [_subscribe(table_fms, k, t) for k, t in FMS_KEYS.items()]
    subscribers += [_subscribe(table_ds, k, t) for k, t in DS_KEYS.items()]

    inst.startClient4("match_timer")
    inst.setServerTeam(team_number)
    inst.startDSClient()

    last_state = None
    while True:
        time.sleep(0.02)
        current = {_key_name(s): s.get() for s in subscribers}
        if current != last_state:
            on_update(current)
            last_state = current.copy()
