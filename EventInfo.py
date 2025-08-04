from datetime import datetime

import Summarizer
from DateFormatting import DateFormatting
import pytz
from CategoryMapping import CategoryMapping
from dateutil import parser
from typing import List, Optional
from CoordinatesMapper import CoordinatesMapper
from bs4 import BeautifulSoup
import re

nz_tz = pytz.timezone("Pacific/Auckland")


class EventInfo:
    locationsCache: dict[str, Optional[dict[str, str]]] = {}

    id: str
    name: str
    image: str
    venue: str
    coordinates: Optional[dict[str, float]]
    dates: List[str]
    displayDate: str
    url: str
    source: str
    eventType: str
    description: str
    long_description: str

    def __init__(
            self: str,
            name: str,
            image: str,
            venue: str,
            dates: List[datetime],
            url: str,
            source: str,
            event_type: str,
            description: str = "",
            long_description = "",
            coordinates: Optional[dict[str, float]] = None,
            loaded_from_dict: bool = False):
        """
        @type name: str
        @param name: The name of the event.
        @type image: str
        @param image: The image of the event.
        @type venue: str
        @param venue: The venue for the event.
        @type dates: str
        @param dates: The date of the event.
        @type displayDate: str
        @param date: The display date of the event.
        @type url: str
        @param url: The url of the event.
        @type source: str
        @param source: The source of the event.
        @type eventType: str
        @param eventType: The type of event.
        """
        self.id = f"{name}-{venue}-{source}"
        self.name = name
        self.image = image
        og_dates = dates
        try:
            dates = list(filter(lambda date: date >= datetime.now(), dates))
        except:
            dates = list(filter(lambda date: date >= datetime.now(nz_tz), dates))
        dates = list(sorted(dates, key=lambda date: date))
        if not dates:
            print(f"in: {og_dates}")
            print(f"out: {dates}")
            raise Exception(f"No dates found for: {name}")
        self.displayDate = DateFormatting.format_display_date(dates[0]) \
            if len(dates) == 1 \
            else f"{DateFormatting.format_display_date(dates[0])} + more"
        self.venue = venue
        if loaded_from_dict:
            self.description = description
            self.coordinates = coordinates
            self.long_description = long_description
        else:
            self.coordinates = coordinates if coordinates else EventInfo.get_location(venue)
            self.long_description = description
            description = EventInfo.clean_html_tags(description)
            description = Summarizer.sumerize(description)
            self.description = description
        self.dates = list(map(lambda date: DateFormatting.format_date_stamp(date), dates))
        self.url = url
        self.source = source
        self.eventType = CategoryMapping.map_category(event_type)


    def to_dict(self):
        """Convert the EventInfo object to a dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "imageUrl": self.image,
            "venue": self.venue,
            "coordinates": self.coordinates,
            "dates": self.dates,
            "displayDate": self.displayDate,
            "url": self.url,
            "source": self.source,
            "eventType": self.eventType,
            "long_description": self.long_description,
            "description": self.description
        }

    @classmethod
    def from_dict(cls, data: dict):
        """Create an EventInfo object from a dictionary."""
        try:
            return cls(
                name=data["name"],
                image=data["imageUrl"],
                venue=data["venue"],
                dates=[parser.parse(date) for date in data["dates"]],
                url=data["url"],
                source=data["source"],
                event_type=data["eventType"],
                coordinates=data["coordinates"],
                description=data["description"],
                long_description=data["long_description"],
                loaded_from_dict=True
            )
        except Exception as e:
            print("failed to load:")
            print(e)
            print("-" * 100)
            if not "No dates found for" in str(e):
                raise e
            return None

    @staticmethod
    def get_location(venue: str) -> Optional[dict[str, str]]:
        if venue in EventInfo.locationsCache.keys():
            return EventInfo.locationsCache[venue]
        else:
            coordinates = CoordinatesMapper.get_coordinates(venue)
            EventInfo.locationsCache[venue] = coordinates
            return coordinates

    @staticmethod
    def clean_html_tags(html_text: str) -> str:
        if not html_text:
            return ""

        soup = BeautifulSoup(html_text, 'html.parser')
        clean_text = soup.get_text()
        clean_text = '\n'.join(line.strip() for line in clean_text.splitlines() if line.strip())
        clean_text = clean_text.strip()
        return clean_text

