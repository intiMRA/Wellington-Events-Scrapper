import json
from datetime import datetime
from DateFormatting import DateFormatting
import pytz
from CategoryMapping import CategoryMapping
from dateutil import parser
import re
nz_tz = pytz.timezone("Pacific/Auckland")

class EventInfo:
    id: str
    name: str
    image: str
    venue: str
    dates: [str]
    displayDate: str
    url: str
    source: str
    eventType: str

    def __init__(
            self: str,
            name: str,
            image: str,
            venue: str,
            dates: [datetime],
            url: str,
            source: str,
            eventType: str):
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
        self.venue = venue
        ogDates = dates
        try:
            dates = list(filter(lambda date: date >= datetime.now(), dates))
        except:
            dates = list(filter(lambda date: date >= datetime.now(nz_tz), dates))
        dates = list(sorted(dates, key=lambda date: date))
        if not dates:
            print(f"in: {ogDates}")
            print(f"out: {dates}")
            raise Exception(f"No dates found for: {name}")
        self.displayDate = DateFormatting.formatDisplayDate(dates[0]) \
            if len(dates) == 1 \
            else f"{DateFormatting.formatDisplayDate(dates[0])} + more"
        self.dates = list(map(lambda date: DateFormatting.formatDateStamp(date), dates))
        self.url = url
        self.source = source
        self.eventType = CategoryMapping.map_category(eventType)
        with open("potentialWrongs.txt", mode="a") as f:
            if re.findall(r"\d", name):
                f.write(f"name: {name}, url: {url}\n")
            if re.findall(r"\d", venue):
                f.write(f"venue: {venue}, url: {url}\n")

    def to_dict(self):
        """Convert the EventInfo object to a dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "imageUrl": self.image,
            "venue": self.venue,
            "dates": self.dates,
            "displayDate": self.displayDate,
            "url": self.url,
            "source": self.source,
            "eventType": self.eventType
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
                eventType=data["eventType"]
            )
        except:
            return None
