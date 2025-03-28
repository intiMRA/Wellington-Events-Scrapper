import requests

from DateFormatting import DateFormatting
from EventInfo import EventInfo
from enum import Enum
from datetime import datetime
import json
from dateutil import parser
class TicketmasterScrapper:
    @staticmethod
    def fetch_events() -> [EventInfo]:
        class PossibleKeys(str, Enum):
            id = 'id'
            total = 'total'
            title = 'title'
            discoveryId = 'discoveryId'
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
            endDate = 'endDate'
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
            if r.status_code != 200:
                return events
            try:
                data = r.json()
                count += len(data[PossibleKeys.events])
                for event in data[PossibleKeys.events]:
                    # TODO: get the images
                    startDate = event[PossibleKeys.dates][PossibleKeys.startDate].split("T")[0]
                    startDateObj = parser.parse(startDate)
                    if PossibleKeys.endDate in event[PossibleKeys.dates].keys():
                        endDate = event[PossibleKeys.dates][PossibleKeys.endDate].split("T")[0]
                        endDateObj = parser.parse(endDate)
                        if startDateObj == endDateObj:
                            dates = [startDateObj]
                        else:
                            dates = list(DateFormatting.createRange(startDateObj, endDateObj))
                    else:
                        dates = [startDateObj]
                    if not dates:
                        print(event[PossibleKeys.dates].keys(), PossibleKeys.endDate in event[PossibleKeys.dates].keys())
                    try:
                        venue = f"{event[PossibleKeys.venue][PossibleKeys.name]}, {event[PossibleKeys.venue][PossibleKeys.city]}"
                        events.append(EventInfo(name=event[PossibleKeys.title],
                                                image="https://business.ticketmaster.co.nz/wp-content/uploads/2024/07/Copy-of-TM-Partnership-Branded-Lockup.png",
                                                venue=venue,
                                                dates=dates,
                                                url=event[PossibleKeys.url],
                                                source="ticketmaster",
                                                eventType="Other"))
                    except Exception as v:
                        print("ticket master error")
                        print(v)
                        count += 1
                        continue
                if count >= data[PossibleKeys.total]:
                    break
                page += 1
            except Exception as e:
                print("ticket master error")
                print(e)
                count+=1
        return events
# events = list(map(lambda x: x.to_dict(), sorted(TicketmasterScrapper.fetch_events(), key=lambda k: k.name.strip())))
# with open('wellys.json', 'w') as outfile:
#     json.dump(events, outfile)