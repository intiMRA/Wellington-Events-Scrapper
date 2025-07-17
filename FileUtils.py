from typing import List

import FileNames
from EventInfo import EventInfo
import re
import json
from dateutil import parser

def write_to_events_file(data: List[EventInfo]):
    events_dict = {}

    for event in data:
        name = re.sub('\W+', ' ', event.name).replace(" ", "")
        if name not in events_dict:
            events_dict[name] = event
        else:
            if not event.image:
                continue
            events_dict[name] = event

    data = list(events_dict.values())
    event_types = set([event.eventType for event in data])
    if "Other" in event_types:
        event_types.remove("Other")
    sources = set([event.source for event in data])
    data = list(map(lambda x: x.to_dict(), sorted(data, key=lambda k: k.name.strip())))
    data = sorted(data, key=lambda k: k["name"])
    data = sorted(data, key=lambda k: parser.parse(k["dates"][0]))
    event_types = sorted(list(event_types))
    event_types.append("Other")
    filters = {
        "sources": sorted(list(sources)),
        "eventTypes": event_types,
    }
    with open(FileNames.EVENTS, "r") as f:
        with open(FileNames.EVENTS, "r") as copy:
            copy.write(f.read())
    with open(FileNames.EVENTS, "w") as write:
        write.write('{ "events":')
        json.dump(data, write, indent=2)
        write.write(',')
        write.write('"filters":')
        json.dump(filters, write, indent=2)
        write.write('}')

def write_last_scrapper(scrapper_name: str):
    with open(FileNames.LAST_SCRAPPER, mode="w") as f:
        f.write(scrapper_name)

def load_last_scrapper() -> str:
    with open(FileNames.LAST_SCRAPPER, mode="r") as f:
        return f.read()