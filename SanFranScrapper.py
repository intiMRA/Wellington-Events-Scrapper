from time import sleep

import requests

import FileNames
import ScrapperNames
from EventInfo import EventInfo
import re
from dateutil import parser
from typing import List, Set
import json

class SanFranScrapper:
    # noinspection PyBroadException
    @staticmethod
    def fetch_events(previous_urls: Set[str]) -> List[EventInfo]:
        events: List[EventInfo] = []
        page = 1
        out_file = open(FileNames.SAN_FRAN_EVENTS, mode="w")
        out_file.write("[\n")
        while True:
            headers = {
                "accept": "*/*",
                "cache-control": "no-cache",
                "pragma": "no-cache",
                "priority": "u=1, i",
                "referer": "https://www.sanfran.co.nz/whats-on",
                "sec-ch-ua": '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
                "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
                "x-culture": "en-NZ",
                "x-site": "www.sanfran.co.nz"
            }
            api_url = f'https://www.sanfran.co.nz/api/search/events?Url=%2Fwhats-on&Page={page}&PageSize=20'

            # sending get request and saving the response as response object
            r = requests.get(url=api_url, headers=headers)
            # extracting data in json format
            if r.status_code != 200:
                return events
            data = r.json()
            if not data['documents']:
                out_file.write("]\n")
                out_file.close()
                return events
            for event in data['documents']:
                try:
                    event_url = f"https://www.sanfran.co.nz{event['localizations'][0]['url']}"
                    date_str = event["eventDate"]
                    date = parser.parse(date_str)
                    event = EventInfo(name=re.sub('\W+', ' ', event["name"]).strip(),
                                      image=event["image"],
                                      venue="San Fran, Wellington",
                                      dates=[date],
                                      url=event_url,
                                      source=ScrapperNames.SAN_FRAN,
                                      event_type="Music",
                                      description=event["description"])
                    events.append(event)
                    json.dump(event.to_dict(), out_file)
                    out_file.write(",\n")
                    print(f"url: {event_url}")
                except Exception as e:
                    print(f"san fran: {event}")
                    print(e)
                    break
                print("-"*100)
            page += 1

# events = list(map(lambda x: x.to_dict(), sorted(SanFranScrapper.fetch_events(), key=lambda k: k.name.strip())))