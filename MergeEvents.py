import json
from typing import List
import FileNames
from EventInfo import EventInfo
import re
from dateutil import parser

data: List[EventInfo] = []
for file in FileNames.ALL_EVENT_FILES:
    print(f"proccessing {file}")
    with open(file, mode="r") as f:
        file_json = json.loads(f.read())
        for event_dict in file_json:
            try:
                event = EventInfo.from_dict(event_dict)
                if event:
                    print(event.name)
                    data.append(event)
            except Exception as e:
                if "No dates found for" in str(e):
                    pass
                raise e
            print("-" * 100)

filtered = []

eventsDict = {}

for event in data:
    name = re.sub('\W+', ' ', event.name).replace(" ", "")
    if name not in eventsDict:
        eventsDict[name] = event
    else:
        if not event.image:
            continue
        eventsDict[name] = event

data = list(eventsDict.values())
eventTypes = set([event.eventType for event in data])
if "Other" in eventTypes:
    eventTypes.remove("Other")
sources = set([event.source for event in data])
data = list(map(lambda x: x.to_dict(), sorted(data, key=lambda k: k.name.strip())))
data = sorted(data, key=lambda k: k["name"])
data = sorted(data, key=lambda k: parser.parse(k["dates"][0]))
eventTypes = sorted(list(eventTypes))
eventTypes.append("Other")
filters = {
    "sources": sorted(list(sources)),
    "eventTypes": eventTypes,
}
with open("events.json", "w") as write:
    write.write('{ "events":')
    json.dump(data, write, indent=2)
    write.write(',')
    write.write('"filters":')
    json.dump(filters, write, indent=2)
    write.write('}')
