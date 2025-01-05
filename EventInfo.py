class EventInfo:
    name: str
    image: str
    venue: str
    date: str
    url: str

    def __init__(self, name: str, image: str, venue: str, date: str, url):
        """
        @type name: str
        @param name: The name of the event.
        @type image: str
        @param image: The image of the event.
        @type venue: str
        @param venue: The venue for the event.
        @type date: str
        @param date: The date of the event.
        @type url: str
        @param url: The url of the event.
        """
        self.name = name
        self.image = image
        self.venue = venue
        self.date = date
        self.url = url

    def to_dict(self):
        """Convert the EventInfo object to a dictionary."""
        return {
            "name": self.name,
            "imageUrl": self.image,
            "venue": self.venue,
            "date": self.date,
            "url": self.url
        }

    @classmethod
    def from_dict(cls, data: dict):
        """Create an EventInfo object from a dictionary."""
        return cls(
            name=data["name"],
            image=data["imageUrl"],
            venue=data["venue"],
            date=data["date"],
            url=data["url"]
        )