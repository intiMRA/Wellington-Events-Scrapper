import requests
from EventInfo import EventInfo
from enum import Enum
# Crhirst church
class VenuesOtautahiScrapper:
    # noinspection PyBroadException
    @staticmethod
    def fetch_events() -> [EventInfo]:
        class PossibleKeys(str, Enum):
            meta = "meta"
            total_pages = "total_pages"
            pagination = "pagination"
            data = "data"
            id = 'id'
            url = 'url'
            title = 'title'
            image = 'image'
            venue = 'venue'
            startDate = 'startDate'

        events: [EventInfo] = []

        total_count_url = f'https://www.venuesotautahi.co.nz/events.json'

        # sending get request and saving the response as response object
        total_count_response = requests.get(url = total_count_url)

        total_count_data = total_count_response.json()
        total_pages = total_count_data[PossibleKeys.meta][PossibleKeys.pagination][PossibleKeys.total_pages]

        for page in range(1, total_pages + 1):
            api_url = f'https://www.venuesotautahi.co.nz/events.json?pg={page}'

            # sending get request and saving the response as response object
            r = requests.get(url=api_url)
            data = r.json()[PossibleKeys.data]
            for event in data:
                events.append(EventInfo(name=event[PossibleKeys.title], image=event[PossibleKeys.image], venue=event[PossibleKeys.venue],date=event[PossibleKeys.startDate], url=event[PossibleKeys.url]))
        return events