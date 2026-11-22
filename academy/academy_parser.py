from academy.exceptions import ParseError
from academy.models import Event, SiiObject
from academy.sii_parser import array_values


def academy_events(objects: dict[str, SiiObject]) -> list[Event]:
    containers = [o for o in objects.values() if o.object_type == "academy_save_container"]
    if containers:
        refs = [o.fields.get("log") for o in containers]
        logs = []
        for ref in refs:
            obj = objects.get(ref)
            if obj is None or obj.object_type != "academy_log":
                raise ParseError("Brak dziennika kontenera Academy")
            if obj not in logs:
                logs.append(obj)
    else:
        logs = [o for o in objects.values() if o.object_type == "academy_log"]
    if not logs:
        raise ParseError("Nie znaleziono academy_log")
    events = []
    for log in logs:
        for ref in array_values(log, "entries"):
            obj = objects.get(ref)
            if obj is None or obj.object_type != "academy_log_entry":
                raise ParseError("Brak obiektu wpisu dziennika")
            f = obj.fields
            if not isinstance(f.get("time"), int) or not isinstance(f.get("type"), str):
                raise ParseError("Niepoprawny czas lub typ zdarzenia")
            result = objects.get(f.get("link"))
            result_fields = None
            if result and result.object_type == "academy_scenario_result":
                result_fields = {"values": result.fields, "raw": result.raw_fields}
            events.append(Event(f["type"], f["time"], obj.object_id, f.get("link"),
                                {"values": f, "raw": obj.raw_fields}, result_fields))
    return events
