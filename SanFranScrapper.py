import requests
from EventInfo import EventInfo
import re
from dateutil import parser
from typing import List

class SanFranScrapper:
    # noinspection PyBroadException
    @staticmethod
    def fetch_events() -> List[EventInfo]:
        events: List[EventInfo] = []
        page = 1
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
                return events
            for event in data['documents']:
                try:
                    eventURL = f"https://www.sanfran.co.nz{event['localizations'][0]['url']}"
                    date_str = event["eventDate"]
                    date = parser.parse(date_str)

                    events.append(EventInfo(name=re.sub('\W+', ' ', event["name"]).strip(),
                                            image=event["image"],
                                            venue="San Fran",
                                            dates=[date],
                                            url=eventURL,
                                            source="San Fran",
                                            eventType="Music"))
                except Exception as e:
                    print(f"san fran: {event}")
                    print(e)
                    break
            page += 1


# events = list(map(lambda x: x.to_dict(), sorted(SanFranScrapper.fetch_events(), key=lambda k: k.name.strip())))
# with open('wellys.json', 'w') as outfile:
#     json.dump(events, outfile)
