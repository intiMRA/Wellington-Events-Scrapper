from EventInfo import EventInfo
from SanFranScrapper import SanFranScrapper
from TicketekScrapper import TicketekScrapper
from TicketmasterScrapper import TicketmasterScrapper
from UnderTheRaderScrapper import UnderTheRaderScrapper
from ValhallaScrapper import ValhallaScrapper
from EventFinderScrapper import EventFinderScrapper
from RougueScrapper import RougueScrapper
from WellingtonNZScrapper import WellingtonNZScrapper
from HumanitixScrapper import HumanitixScrapper
from FacebookScrapper import FacebookScrapper
import json
import re
from dateutil import parser
from datetime import datetime

print("fetching wellington NZ")
wellyNZ_events = WellingtonNZScrapper.fetch_events()
print("fetching facebook")
facebook_events = FacebookScrapper.fetch_events()
print("fetching san fran")
san_fran_events: [EventInfo] = SanFranScrapper.fetch_events()
print("fetching tiket")
ticket_events: [EventInfo] = TicketekScrapper.fetch_events()
print("fetching ticket master")
ticket_master_events: [EventInfo] = TicketmasterScrapper.fetch_events()
print("fetching under the radar")
under_the_radar_events: [EventInfo] = UnderTheRaderScrapper.fetch_events()
print("fetching valhalla")
valhalla_events: [EventInfo] = ValhallaScrapper.fetch_events()
print("fetching event finder")
event_finder_event: [EventInfo] = EventFinderScrapper.fetch_events()
print("fetching rogue")
rogue_events = RougueScrapper.fetch_events()
print("fetching mumanitix")
humanitix_events = HumanitixScrapper.fetch_events()

print("facebook: ", len(facebook_events))
print("san fran: ", len(san_fran_events))
print("ticket: ", len(ticket_events))
print("ticket master: ", len(ticket_master_events))
print("under the radar: ", len(under_the_radar_events))
print("valhalla: ", len(valhalla_events))
print("event finder: ", len(event_finder_event))
print("rogue: ", len(rogue_events))
print("wellington nz: ", len(wellyNZ_events))
print("humanitix: ", len(humanitix_events))

# data = event_finder_event
data = (facebook_events
        + san_fran_events
        + ticket_events
        + ticket_master_events
        + under_the_radar_events
        + valhalla_events
        + event_finder_event
        + rogue_events
        + wellyNZ_events
        + humanitix_events)

filtered = []

eventsDict = {}

for event in data:
    name = re.sub('\W+', ' ', event.name).replace(" ", "")
    if name not in eventsDict:
        eventsDict[name] = event
    else:
        if not event.image:
            continue
        eventsDict[name] = event

data = list(eventsDict.values())
eventTypes = set([event.eventType for event in data])
if "Other" in eventTypes:
    eventTypes.remove("Other")
sources = set([event.source for event in data])
data = list(map(lambda x: x.to_dict(), sorted(data, key=lambda k: k.name.strip())))
data = sorted(data, key=lambda k: k["name"])
data = sorted(data, key=lambda k: parser.parse(k["dates"][0]))
eventTypes = list(eventTypes)
eventTypes.append("Other")
filters = {
    "sources": sorted(list(sources)),
    "eventTypes": sorted(eventTypes),
}
with open("events.json", "w") as write:
    write.write('{ "events":')
    json.dump(data, write)
    write.write(',')
    write.write('"filters":')
    json.dump(filters, write)
    write.write('}')
