import uuid
from uuid import uuid4

class EventInfo:
    id: str
    name: str
    image: str
    venue: str
    dates: [str]
    displayDate: str
    url: str
    source: str

    def __init__(self: str, name: str, image: str, venue: str, dates: [str], displayDate: str, url: str, source: str):
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
        """
        self.id = uuid4().urn
        self.name = name
        self.image = image
        self.venue = venue
        self.dates = dates
        self.displayDate = displayDate
        self.url = url
        self.source = source

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
            "source": self.source
        }

    @classmethod
    def from_dict(cls, data: dict):
        """Create an EventInfo object from a dictionary."""
        return cls(
            name=data["name"],
            image=data["imageUrl"],
            venue=data["venue"],
            dates=data["dates"],
            displayDate=data["displayDate"],
            url=data["url"],
            source=data["source"]
        )
