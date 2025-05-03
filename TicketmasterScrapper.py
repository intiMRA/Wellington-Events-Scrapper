import requests

from DateFormatting import DateFormatting
from EventInfo import EventInfo
from enum import Enum
import json
from dateutil import parser

majorCats = {
    "MusicEvent": ["1", "2", "3", "4", "5", "52", "60", "171", "200", "201", "1001", "1002", "1012", "1201", "1202",
                   "1220", "1221", "1229", "1230", "1231", "1232", "1233", "1234", "1235", "1236", "1237", "1238",
                   "1258",
                   "1259", "1262", "10001", "10006", "10103", "10104"],
    "ComedyEvent": ["39", "264", "1013", "10102"],
    "ChildrensEvent": ["55", "209", "1114", "1115", "1212", "1214", "1240", "1260"],
    "ExhibitionEvent": ["14", "54", "1014", "1213", "1245", "1249", "1250", "1251", "1253", "1254", "10008"],
    "Festival": ["203", "1004", "1005", "1006", "1007", "1123", "1216", "1217", "1218", "1219", "1228", "10101"],
    "FoodEvent": ["1122", "1242"],
    "LiteraryEvent": ["1222"],
    "ScreeningEvent": ["1015"],
    "SportsEvent": ["7", "8", "9", "10", "11", "25", "27", "30", "31", "33", "36", "102", "204", "206", "693", "771",
                    "773", "831", "833", "1102", "1103", "1104", "1105", "1106", "1107", "1109", "1110", "1124", "1204",
                    "1206", "1210", "1211", "1226", "1227", "1239", "10004", "10105"],
    "TheaterEvent": ["12", "13", "22", "23", "32", "207", "1003", "1111", "1116", "1117", "1118", "1241", "10002",
                     "10106"]
}
minorCats = {
    "MusicEvent": ["1", "2", "3", "4", "5", "50", "52", "60", "107", "200", "201", "202", "203", "542", "764", "766",
                   "839", "10001", "KnvZfZ7vAvv", "KnvZfZ7vAve", "KnvZfZ7vAvd", "KnvZfZ7vAvA", "KnvZfZ7vAvk",
                   "KnvZfZ7vAeJ", "KnvZfZ7vAv6", "KnvZfZ7vAvF", "KnvZfZ7vAva", "KnvZfZ7vAv1", "KnvZfZ7vAvJ",
                   "KnvZfZ7vAvE", "KnvZfZ7vAJ6", "KnvZfZ7vAvI", "KnvZfZ7vAvt", "KnvZfZ7vAvn", "KnvZfZ7vAvl",
                   "KnvZfZ7vAev", "KnvZfZ7vAee", "KnvZfZ7vAed", "KnvZfZ7vAe7", "KnvZfZ7vAeA", "KnvZfZ7vAeF",
                   "KZFzniwnSyZfZ7v7nJ", "KZazBEonSMnZfZ7vkE1"],
    "ChildrensEvent": ["29", "KnvZfZ7v7lF", "KnvZfZ7v7lI", "KnvZfZ7v7lv", "KnvZfZ7v7n1", "KnvZfZ7v7na", "KnvZfZ7vAea",
                       "KnvZfZ7vAeE", "KZazBEonSMnZfZ7vFdE", "KnvZfZ7vA1n", "KnvZfZ7vAkF", "KnvZfZ7vAvk"],
    "ComedyEvent": ["51"],
    "EducationEvent": ["104"],
    "ExhibitionEvent": ["14", "105", "218", "514", "514", "592", "754"],
    "Festival": ["54"],
    "ScreeningEvent": ["59"],
    "SportsEvent": ["7", "8", "9", "11", "25", "27", "30", "31", "33", "102", "205", "206", "225", "582", "676", "677",
                    "693", "694", "695", "711", "713", "716", "718", "729", "742", "765", "830", "10004", "KnvZfZ7vAeI",
                    "KnvZfZ7vAet", "KnvZfZ7vAen", "KnvZfZ7vAel", "KnvZfZ7vAdv", "KnvZfZ7vAde", "KnvZfZ7vAdd",
                    "KnvZfZ7vAd7", "KnvZfZ7vAdA", "KnvZfZ7vAdk", "KnvZfZ7vAdF", "KnvZfZ7vAda", "KnvZfZ7vAd1",
                    "KnvZfZ7vAJF", "KnvZfZ7vAdJ", "KnvZfZ7vAJv", "KnvZfZ7vAJ7", "KnvZfZ7vA1l", "KnvZfZ7vAdE",
                    "KnvZfZ7vAdt", "KnvZfZ7vAdn", "KnvZfZ7vAdl", "KnvZfZ7vAdI", "KnvZfZ7vA7v", "KnvZfZ7vA7e",
                    "KnvZfZ7vA77", "KnvZfZ7vA7d", "KnvZfZ7vA7A", "KnvZfZ7vA7k", "KnvZfZ7vA76", "KnvZfZ7vAea",
                    "KnvZfZ7vAJA", "KnvZfZ7vA7a", "KnvZfZ7vA71", "KnvZfZ7vA7J", "KnvZfZ7vAd6", "KnvZfZ7vA7E",
                    "KnvZfZ7vAJd", "KnvZfZ7vA7I", "KnvZfZ7vA7t", "KnvZfZ7vA7n", "KnvZfZ7vA7l", "KnvZfZ7vAAv",
                    "KnvZfZ7vAAe", "KnvZfZ7vAAd", "KnvZfZ7vAA7", "KnvZfZ7vAAA", "KnvZfZ7vAAk", "KZFzniwnSyZfZ7v7nE"],
    "TheaterEvent": ["12", "13", "22", "23", "32", "207", "209", "509", "558", "10002", "KnvZfZ7v7nt", "KnvZfZ7v7na",
                     "KnvZfZ7v7n1", "KnvZfZ7v7nl", "KnvZfZ7v7le", "KnvZfZ7v7lF", "KnvZfZ7v7l1", "KnvZfZ7v7nJ",
                     "KnvZfZ7vAe1", "KnvZfZ7v7nE", "KnvZfZ7v7nI", "KnvZfZ7v7nn", "KnvZfZ7v7lv", "KnvZfZ7v7ld",
                     "KnvZfZ7v7l7", "KnvZfZ7v7lA", "KnvZfZ7v7lk", "KnvZfZ7v7l6", "KnvZfZ7v7la", "KnvZfZ7v7lJ",
                     "KZFzniwnSyZfZ7v7na"]
}


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
                cat = data["events"][0]["majorCategory"]["id"]
                catergoryName = None
                for m in majorCats.keys():
                    key, value = m, majorCats[m]
                    if cat in value:
                        catergoryName = key
                        break
                if not catergoryName:
                    for m in minorCats.keys():
                        key, value = m, minorCats[m]
                        if cat in value:
                            catergoryName = key
                            break

                count += len(data[PossibleKeys.events])
                for event in data[PossibleKeys.events]:
                    # TODO: get the images
                    startDate = event[PossibleKeys.dates][PossibleKeys.startDate]
                    startDateObj = parser.parse(startDate)
                    if PossibleKeys.endDate in event[PossibleKeys.dates].keys():
                        endDate = event[PossibleKeys.dates][PossibleKeys.endDate]
                        endDate = endDate.split("T")[0] + "T" + startDate.split("T")[1]
                        endDateObj = parser.parse(endDate)
                        if startDateObj == endDateObj:
                            dates = [startDateObj]
                        else:
                            dates = list(DateFormatting.createRange(startDateObj, endDateObj))
                    else:
                        dates = [startDateObj]
                    if not dates:
                        print(event[PossibleKeys.dates].keys(),
                              PossibleKeys.endDate in event[PossibleKeys.dates].keys())
                    try:
                        venue = f"{event[PossibleKeys.venue][PossibleKeys.name]}, {event[PossibleKeys.venue][PossibleKeys.city]}"
                        events.append(EventInfo(name=event[PossibleKeys.title],
                                                image="https://business.ticketmaster.co.nz/wp-content/uploads/2024/07/Copy-of-TM-Partnership-Branded-Lockup.png",
                                                venue=venue,
                                                dates=dates,
                                                url=event[PossibleKeys.url],
                                                source="ticketmaster",
                                                eventType=catergoryName if catergoryName else "Other"))
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
                count += 1
        return events


# events = list(map(lambda x: x.to_dict(), sorted(TicketmasterScrapper.fetch_events(), key=lambda k: k.name.strip())))
# with open('wellys.json', 'w') as outfile:
#     json.dump(events, outfile)
