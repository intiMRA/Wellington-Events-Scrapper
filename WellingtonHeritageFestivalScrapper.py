import json
import re

from tensorflow.python.data.experimental.ops.testing import sleep
from dateutil import parser
import FileUtils
import ScrapperNames
from EventInfo import EventInfo
from typing import List, Set, Optional
from datetime import datetime
import requests
import CurrentFestivals
from DateFormatting import DateFormatting


class WellingtonHeritageFestivalScrapper:

    @staticmethod
    def fetch_events(previous_urls: Set[str], previous_titles: Optional[Set[str]]) -> List[EventInfo]:
        out_file, urls_file, banned_file = FileUtils.get_files_for_scrapper(ScrapperNames.WELLINGTON_HERITAGE_FESTIVAL)
        previous_urls = previous_urls.union(set(FileUtils.load_banned(ScrapperNames.WELLINGTON_HERITAGE_FESTIVAL)))
        festival_name = "heritage-festival"
        CurrentFestivals.CURRENT_FESTIVALS.append("HeritageFestival")
        CurrentFestivals.CURRENT_FESTIVALS_DETAILS.append({
            "id": "RoxyFestival",
            "name": festival_name,
            "icon": "movie",
            f"url": f"https://raw.githubusercontent.com/intiMRA/Wellington-Events-Scrapper/refs/heads/main/{festival_name}.json"
        })
        url = 'https://wellingtonheritagefestival.co.nz/page-data/events/page-data.json'
        headers = {
            'accept': '*/*',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
            'referer': 'https://wellingtonheritagefestival.co.nz/events/',
            'sec-fetch-site': 'same-origin',
            'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
        }

        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        events_json_list = data["result"]["data"]["allContentfulEvent"]["nodes"]
        message_json = json.loads(data["result"]["data"]["contentfulLandingPage"]["content"]["raw"])
        dates_message = message_json["content"][0]["content"][1]["value"]
        start_date_string, end_date_string = dates_message.split(" until the ")
        start_date, end_date = parser.parse(start_date_string + " 1:01AM"), parser.parse(end_date_string + " 1:01AM")
        if datetime.now() > end_date:
            return []
        festival_range = [parser.parse(DateFormatting.format_date_stamp(date)) for date in DateFormatting.create_range(start_date, end_date)]
        event_list = []
        for event_json in events_json_list:
            keep_event = False
            for tag in event_json["metadata"]["tags"]:
                year_id: str = tag["contentful_id"]
                try:
                    number: int = int(re.sub("events", "", year_id))
                    if number >= datetime.now().year:
                        keep_event = True
                except:
                    continue
            if not keep_event:
                continue
            title = event_json["title"]
            image_url = "https://wellingtonheritagefestival.co.nz/" + event_json["bannerImg"]["img"]["gatsbyImage"]["images"]["sources"][0]["srcSet"]
            dates = []
            for time in event_json["times"]:
                if time["fullFestivalDuration"]:
                    dates = festival_range
                    break
                dates.append(parser.parse(DateFormatting.format_date_stamp(parser.parse(time["startDate"]))))
            venue = event_json["location"]
            url = "https://wellingtonheritagefestival.co.nz/event/" + event_json["slug"]
            intro_contents = json.loads(event_json["intro"]["raw"])["content"][0]["content"]
            intro = ""
            for intro_content in intro_contents:
                if "content" in intro_content.keys():
                    for intro_content_sub in intro_content["content"]:
                        intro += intro_content_sub["value"] + "\n"
                else:
                    intro += intro_content["value"] + "\n"
            description_contents = json.loads(event_json["description"]["raw"])["content"][0]["content"]
            description = ""
            for description_content in description_contents:
                if "content" in description_content.keys():
                    for description_content_sub in description_content["content"]:
                        description += description_content_sub["value"] + "\n"
                else:
                    description += description_content["value"] + "\n"
            description = description + intro
            event = EventInfo(name=title,
                             dates=dates,
                             image=image_url,
                             url=url,
                             venue=venue,
                             source=ScrapperNames.WELLINGTON_HERITAGE_FESTIVAL,
                             event_type="Community & Culture",
                             description=description)
            if event:
                event_list.append(event)
        print(len(event_list))
        with open("heritage-festival.json", mode="w") as festival_file:
            json.dump([event.to_dict() for event in event_list], festival_file, indent=2)
        return []

# events = list(map(lambda x: x.to_dict(), sorted(WellingtonHeritageFestivalScrapper.fetch_events(set(), set()), key=lambda k: k.name.strip())))