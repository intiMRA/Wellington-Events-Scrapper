import requests

from DateFormatting import DateFormatting
from EventInfo import EventInfo
from enum import Enum
import re
from datetime import datetime


class SanFranScrapper:
    # noinspection PyBroadException
    @staticmethod
    def fetch_events() -> [EventInfo]:
        class PossibleKeys(str, Enum):
            id = 'id'
            agePolicy = 'agePolicy'
            alternativeDates = 'alternativeDates'
            allTicketStatus = 'allTicketStatus'
            announceDateUtc = 'announceDateUtc'
            contentType = 'contentType'
            encodedName = 'encodedName'
            encodedKeywords = 'encodedKeywords'
            externalDataO2Priority = 'externalDataO2Priority'
            eventDate = 'eventDate'
            eventDateUtc = 'eventDateUtc'
            eventDateTo = 'eventDateTo'
            eventDateToUtc = 'eventDateToUtc'
            eventSortDateUtc = 'eventSortDateUtc'
            modified = 'modified'
            festivalId = 'festivalId'
            curfewTime = 'curfewTime'
            doorTime = 'doorTime'
            showTime = 'showTime'
            genres = 'genres'
            image = 'image'
            imageAltTag = 'imageAltTag'
            imagePlacement = 'imagePlacement'
            includeInVoucherProgram = 'includeInVoucherProgram'
            isDeleted = 'isDeleted'
            isNewEvent = 'isNewEvent'
            isInternational = 'isInternational'
            ianaTimeZone = 'ianaTimeZone'
            lineup = 'lineup'
            localizations = 'localizations'
            promoter = 'promoter'
            promoterId = 'promoterId'
            promoterIds = 'promoterIds'
            siteId = 'siteId'
            tickets = 'tickets'
            eventListingText = 'eventListingText'
            externalUrl = 'externalUrl'
            venue = 'venue'
            mainEventInfo = 'mainEventInfo'
            additionalEventInformation = 'additionalEventInformation'
            cultureName = 'cultureName'
            description = 'description'
            alertType = 'alertType'
            alertText = 'alertText'
            alertValidFromUtc = 'alertValidFromUtc'
            alertValidToUtc = 'alertValidToUtc'
            listingsText = 'listingsText'
            mainEventInformation = 'mainEventInformation'
            agePolicyText = 'agePolicyText'
            name = 'name'
            url = 'url'
            overridenTickets = 'overridenTickets'
            documents = "documents"
            address = 'address'

        events: [EventInfo] = []

        page = 1
        while True:
            headers = {
                "referer": "https://www.sanfran.co.nz/whats-on",
                "x-site": "sanfran.co.nz",
                "x-culture": "x-culture"
            }
            api_url = f'https://www.sanfran.co.nz/api/search/events?Url=%2Fwhats-on&Page={page}&PageSize=20'

            # sending get request and saving the response as response object
            r = requests.get(url=api_url, headers=headers)

            # extracting data in json format
            try:
                data = r.json()
                for event in data[PossibleKeys.documents]:
                    eventURL = f"https://www.sanfran.co.nz{event[PossibleKeys.localizations][0][PossibleKeys.url]}"
                    date_str = event[PossibleKeys.eventDate]
                    date_format = '%Y-%m-%dT%H:%M:%SZ'
                    date = datetime.strptime(date_str, date_format)
                    displayDate = DateFormatting.formatDisplayDate(date)
                    dateStamp = DateFormatting.formatDateStamp(date)
                    events.append(EventInfo(name=re.sub('\W+', ' ', event[PossibleKeys.name]).strip(),
                                            image=event[PossibleKeys.image],
                                            venue="San Fran",
                                            dates=[dateStamp],
                                            displayDate=displayDate,
                                            url=eventURL,
                                            source="sanfran",
                                            eventType="Music"))
                page += 1
            except Exception as e:
                print("san fran")
                print(e)
                break

        return events
