import requests

from util import FileUtils
from scrapers.ScrapperNames import ScraperName
from model.EventInfo import EventInfo
import re
from dateutil import parser
from typing import List, Set, Optional
import json


class SanFranScrapper:
    # noinspection PyBroadException
    @staticmethod
    def fetch_events(previous_urls: Set[str], previous_titles: Optional[Set[str]]) -> List[EventInfo]:
        events: List[EventInfo] = []
        page = 1
        out_file, urls_file, banned_file = FileUtils.get_files_for_scrapper(ScraperName.SAN_FRAN)
        _ = previous_urls.union(set(FileUtils.load_banned(ScraperName.SAN_FRAN)))
        out_file.write("[\n")
        while True:
            headers = {
                "accept": "*/*",
                "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
                "priority": "u=1, i",
                "referer": "https://www.sanfran.co.nz/whats-on",
                "sec-ch-ua": '"Not:A-Brand";v="8", "Chromium";v="156", "Google Chrome";v="156"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"macOS"',
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-origin",
                "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36",
            }

            api_url = f'https://www.sanfran.co.nz/__api/search/events?Url=%2Fwhats-on&PageSize=20&Page={page}&culture=en-NZ'

            # sending get request and saving the response as response object
            r = requests.get(url=api_url, headers=headers)
            # extracting data in json format
            if r.status_code != 200:
                if page == 1 and not events:
                    print("[SanFran] failed to retrieve events")
                out_file.close()
                banned_file.close()
                urls_file.close()
                return events
            data = r.json()
            if not data['documents']:
                out_file.write("]\n")
                out_file.close()
                banned_file.close()
                urls_file.close()
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
                                      source=ScraperName.SAN_FRAN,
                                      event_type="Music",
                                      description=event["description"])
                    events.append(event)
                    json.dump(event.to_dict(), out_file, indent=2)
                    out_file.write(",\n")
                    print(f"url: {event_url}")
                except Exception as e:
                    print(f"san fran: {event}")
                    print(e)
                    break
                print("-" * 100)
            page += 1

# events = list(map(lambda x: x.to_dict(), sorted(SanFranScrapper.fetch_events(set(), set()), key=lambda k: k.name.strip())))
