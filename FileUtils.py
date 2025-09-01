from typing import List, IO, Set, Tuple

import CurrentFestivals
import FileNames
import ScrapperNames
from EventInfo import EventInfo
import json
from dateutil import parser
import re
import pytz
from datetime import datetime
import requests


def is_facebook_url_expired_now(image_url: str, source: str):
    if not image_url or source != "Facebook":
        return False
    matches = re.findall(r"oe=([aA-zZ0-9]+)", image_url)
    if not matches:
        return False
    try:
        oe_hex = matches[0].split("oe=")[0]
        nz_timezone = pytz.timezone('Pacific/Auckland')
        now_nz = datetime.now(nz_timezone)
        unix_time = int(oe_hex, 16)
        utc_expiry = datetime.fromtimestamp(unix_time, pytz.utc)

        nz_expiry = utc_expiry.astimezone(nz_timezone)

        expiration = now_nz > nz_expiry
        if expiration:
            return True
        else:
            code = requests.request(url=image_url, method="GET").status_code
            valid_code = code == 200
            if valid_code:
                return False
            print(f"invalid fetch: {image_url}")
            return True
    except:
        return False


def write_to_events_file(data: List[EventInfo], file: str = FileNames.EVENTS):
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
    if file == FileNames.EVENTS:
        with open(FileNames.EVENTS, "r") as f:
            with open(FileNames.EVENTS_COPY, "w") as copy:
                copy.write(f.read())
    with open(FileNames.CURRENT_FESTIVALS, "w") as f:
        json.dump(CurrentFestivals.CURRENT_FESTIVALS, f, indent=2)
    with open(FileNames.CURRENT_FESTIVALS_DETAILS, "w") as f:
        json.dump(CurrentFestivals.CURRENT_FESTIVALS_DETAILS, f, indent=2)
    with open(file, "w") as write:
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


def load_events(from_file=FileNames.EVENTS) -> List[EventInfo]:
    with open(from_file, mode="r") as f:
        events_json = json.loads(f.read())
        events_json = events_json["events"]
        events = []
        skipped = 0
        for event_json in events_json:
            event = EventInfo.from_dict(event_json)
            if event and (from_file != FileNames.EVENTS or not is_facebook_url_expired_now(event.image, event.source)):
                events.append(event)
            else:
                skipped += 1
        print(f"in: {len(events_json)}")
        print(f"out: {len(events)}")
        print(f"skipped: {skipped}")
        return events


def get_files_for_scrapper(name: str) -> Tuple[IO, IO, IO]:
    return (open(f"{name}Events.json", mode="w"),
            open(f"{name}Urls.json", mode="w"),
            open(f"{name}Banned.json", mode="a"))


def load_from_files(name: str) -> Tuple[List[EventInfo], List, List]:
    events: List[EventInfo] = []
    urls = []
    banned_urls = []
    with open(f"{name}Events.json", mode="r") as f:
        events = json.loads(f.read().replace(',\n}', '\n}').replace(',\n]', '\n]'))
    with open(f"{name}Urls.json", mode="r") as f:
        urls = json.loads(f.read().replace(',\n}', '\n}').replace(',\n]', '\n]'))
    with open(f"{name}Banned.json", mode="r") as f:
        file_text = f.read()[0:-2]
        banned_urls = json.loads(f"[{file_text}]")
    return events, urls, banned_urls


def load_banned(name: str) -> Set[str]:
    with open(f"{name}Banned.json", mode="r") as f:
        file_text = f.read()[0:-2]
        return json.loads(f"[{file_text}]")


def all_event_file_names() -> List[str]:
    names = []
    for scrapper in ScrapperNames.ALL_SCRAPER_NAMES:
        names.append(f"{scrapper}Events.json")
    return names
