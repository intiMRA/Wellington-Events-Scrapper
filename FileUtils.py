from typing import List, IO, Set

import FileNames
import ScrapperNames
from EventInfo import EventInfo
import json
from dateutil import parser
import re
import pytz
from datetime import datetime

def is_facebook_url_expired_now(image_url: str):
    if not image_url:
        return False
    matches = re.findall(r"oe=[aA-zZ0-9]+", image_url)
    if not matches:
        return False
    try:
        oe_hex = matches[0].split("oe=")[0]
        nz_timezone = pytz.timezone('Pacific/Auckland')
        now_nz = datetime.now(nz_timezone)
        unix_time = int(oe_hex, 16)
        utc_expiry = datetime.fromtimestamp(unix_time, pytz.utc)

        nz_expiry = utc_expiry.astimezone(nz_timezone)

        return now_nz > nz_expiry
    except:
        return False


def write_to_events_file(data: List[EventInfo]):
    events_dict = {}

    for event in data:
        event_id = event.id
        if event_id not in events_dict:
            events_dict[event_id] = event
        else:
            if not event.image:
                continue
            events_dict[event_id] = event

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
        with open(FileNames.EVENTS_COPY, "w") as copy:
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

def load_events(from_file = FileNames.EVENTS) -> List[EventInfo]:
    with open(from_file, mode="r") as f:
        events_json = json.loads(f.read())
        events = []
        for event_json in events_json["events"]:
            event = EventInfo.from_dict(event_json)
            if event and not is_facebook_url_expired_now(event.image):
                events.append(event)
        return events

def get_files_for_scrapper(name: str) -> tuple[IO, IO, IO]:
    return (open(f"{name}Events.json", mode="w"),
            open(f"{name}Urls.json", mode="w"),
            open(f"{name}Banned.json", mode="a"))

def load_from_files(name: str) -> tuple[List[EventInfo], List, List]:
    events: List[EventInfo] = []
    urls = []
    banned_urls = []
    with open(f"{name}Events.json", mode="r") as f:
        events = json.loads(f.read().replace(',\n}', '\n}').replace(',\n]', '\n]'))
    with open(f"{name}Urls.json", mode="r") as f:
        urls = json.loads(f.read().replace(',\n}', '\n}').replace(',\n]', '\n]'))
    with open(f"{name}Banned.json",mode="r") as f:
        file_text = f.read()[0:-2]
        banned_urls = json.loads(f"[{file_text}]")
    return events, urls, banned_urls

def load_banned(name: str) -> Set[str]:
    with open(f"{name}Banned.json",mode="r") as f:
        file_text = f.read()[0:-2]
        return json.loads(f"[{file_text}]")

def all_event_file_names() -> List[str]:
    names = []
    for scrapper in ScrapperNames.ALL_SCRAPER_NAMES:
        names.append(f"{scrapper}Events.json")
    return names
