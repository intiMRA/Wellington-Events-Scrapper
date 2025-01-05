import requests
from EventInfo import EventInfo
from enum import Enum
from datetime import datetime

class TicketmasterScrapper:
    @staticmethod
    def fetch_events() -> [EventInfo]:
        class PossibleKeys(str, Enum):
            id = 'id'
            total = 'total'
            title = 'title'
            discoveryId ='discoveryId'
            dates = 'dates'
            presaleDates = 'presaleDates'
            url = 'url'
            partnerEvent = 'partnerEvent'
            isPartner = 'isPartner'
            showTmButton = 'showTmButton'
            venue = 'venue'
            timeZone = 'timeZone'
            cancelled = 'cancelled'
            postponed = 'postponed'
            rescheduled = 'rescheduled'
            tba = 'tba'
            local = 'local'
            sameRegion = 'sameRegion'
            soldOut = 'soldOut'
            limitedAvailability = 'limitedAvailability'
            ticketingStatus = 'ticketingStatus'
            eventChangeStatus = 'eventChangeStatus'
            virtual = 'virtual'
            artists = 'artists'
            price = 'price'
            startDate = 'startDate'
            name = 'name'
            events = 'events'
            city = 'city'

        events: [EventInfo] = []
        headers = {
            "accept": "*/*",
            "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
            "priority": "u=1, i",
            "referer": "https://www.ticketmaster.co.nz/search?q=wellington",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
            "x-tmregion": "750",
            "Cache-Control": "no-cache",
            "Host": "www.ticketmaster.co.nz",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive"
        }
        page = 0
        count = 0
        while True:
            api_url = f'https://www.ticketmaster.co.nz/api/search/events?q=wellington&region=750&sort=date&page={page}'
            r = requests.get(url=api_url, headers=headers)
            try:
                data = r.json()
                count += len(data[PossibleKeys.events])
                for event in enumerate(sorted(data[PossibleKeys.events], key = lambda x: x[PossibleKeys.dates][PossibleKeys.startDate])):
                    # TODO: get the images
                    index = event[0]
                    event = event[1]
                    date_str = event[PossibleKeys.dates][PossibleKeys.startDate]
                    date_format = '%Y-%m-%dT%H:%M:%SZ'
                    try:
                        date = datetime.strptime(date_str, date_format)
                        current_date = datetime.utcnow()
                        if (date - current_date).days > 14:
                            if index == 0:
                                return events
                            continue
                        formatted_date = date.strftime("%a %d %b %Y %I:%M%p").lower()
                        venue = f"{event[PossibleKeys.venue][PossibleKeys.name]}, {event[PossibleKeys.venue][PossibleKeys.city]}"
                        events.append(EventInfo(name=event[PossibleKeys.title], image=None, venue=venue, date=formatted_date, url=event[PossibleKeys.url]))
                    except ValueError:
                        print(ValueError)
                        continue
                if count >= data[PossibleKeys.total]:
                    break
                page += 1
            except Exception as e:
                print(e)
                break
        return events