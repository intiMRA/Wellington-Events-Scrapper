import requests

from DateFormatting import DateFormatting
from EventInfo import EventInfo
from enum import Enum
import re
from datetime import datetime
import json


class SanFranScrapper:
    # noinspection PyBroadException
    @staticmethod
    def fetch_events() -> [EventInfo]:
        events: [EventInfo] = []

        page = 1
        while True:
            headers = {
                "referer": "https://www.sanfran.co.nz/whats-on",
                "x-site": "sanfran.co.nz",
                "x-culture": "x-culture"
            }
            api_url = f'https://www.sanfran.co.nz/api/search/events?Url=%2Fwhats-on&Page={page}&PageSize=20'

            # sending get request and saving the response as response object
            r = requests.get(url=api_url, headers=headers)
            # extracting data in json format
            if r.status_code != 200:
                return events
            data = r.json()

            for event in data['documents']:
                try:
                    eventURL = f"https://www.sanfran.co.nz{event['localizations'][0]['url']}"
                    date_str = event["eventDate"]
                    date_format = '%Y-%m-%dT%H:%M:%SZ'
                    date = datetime.strptime(date_str, date_format)
                    events.append(EventInfo(name=re.sub('\W+', ' ', event["name"]).strip(),
                                            image=event["image"],
                                            venue="San Fran",
                                            dates=[date],
                                            url=eventURL,
                                            source="sanfran",
                                            eventType="Music"))
                except Exception as e:
                    print(f"san fran: {event}")
                    print(e)
                    break
                page += 1
        return events


# events = list(map(lambda x: x.to_dict(), sorted(SanFranScrapper.fetch_events(), key=lambda k: k.name.strip())))
# with open('wellys.json', 'w') as outfile:
#     json.dump(events, outfile)
