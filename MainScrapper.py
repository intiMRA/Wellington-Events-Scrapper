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
from WellingtonHighschoolScrapper import WellingtonHighschoolScrapper
from EventbriteScrapper import EventbriteScrapper
import json
import re
from dateutil import parser

with open("events.json", mode="r") as f:
    evts = json.loads(f.read())
    previousEventTitles = evts["events"]
# cacheFile = open("cached.json", mode="w")
# cacheFile.write("{\n")

print("fetching wellington NZ")
wellingtonNZPrevious = [EventInfo.from_dict(event) for event in previousEventTitles if event["source"] == "Wellington NZ"]
wellingtonNZPrevious = [event for event in wellingtonNZPrevious if event is not None]
wellyNZ_events = WellingtonNZScrapper.fetch_events(set([event.name for event in wellingtonNZPrevious])) + wellingtonNZPrevious
# json.dump([e.to_dict() for e in wellyNZ_events], cacheFile)
# cacheFile.write(",\n")

print("fetching facebook")
facebookPrevious = [EventInfo.from_dict(event) for event in previousEventTitles if event["source"] == "Ticket Master"]
facebookPrevious = [event for event in facebookPrevious if event is not None]
facebook_events = FacebookScrapper.fetch_events()
for e in facebookPrevious:
    contains = False
    for e2 in facebook_events:
        if e.name == e2.name:
            contains = True
            break
    if contains:
        continue
    facebook_events.append(e)
# json.dump([e.to_dict() for e in facebook_events], cacheFile)
# cacheFile.write(",\n")

print("fetching san fran")
san_fran_events: [EventInfo] = SanFranScrapper.fetch_events()
# json.dump([e.to_dict() for e in san_fran_events], cacheFile)
# cacheFile.write(",\n")

print("fetching tiket")
ticket_events: [EventInfo] = TicketekScrapper.fetch_events()
# json.dump([e.to_dict() for e in ticket_events], cacheFile)
# cacheFile.write(",\n")

print("fetching ticket master")
ticketMasterPrevious = [EventInfo.from_dict(event) for event in previousEventTitles if event["source"] == "Ticket Master"]
ticketMasterPrevious = [event for event in ticketMasterPrevious if event is not None]
ticket_master_events: [EventInfo] = TicketmasterScrapper.fetch_events(set([event.name for event in ticketMasterPrevious])) + ticketMasterPrevious
# json.dump([e.to_dict() for e in ticket_master_events], cacheFile)
# cacheFile.write(",\n")

print("fetching under the radar")
utrPrevious = [EventInfo.from_dict(event) for event in previousEventTitles if event["source"] == "Under The Radar"]
utrPrevious = [event for event in utrPrevious if event is not None]
under_the_radar_events: [EventInfo] = UnderTheRaderScrapper.fetch_events(set([event.name for event in utrPrevious])) + utrPrevious
# json.dump([e.to_dict() for e in under_the_radar_events], cacheFile)
# cacheFile.write(",\n")

print("fetching valhalla")
valhalla_events: [EventInfo] = ValhallaScrapper.fetch_events()
# json.dump([e.to_dict() for e in valhalla_events], cacheFile)
# cacheFile.write(",\n")

print("fetching event finder")
eventFinderPrevious = [EventInfo.from_dict(event) for event in previousEventTitles if event["source"] == "Event Finder"]
eventFinderPrevious = [event for event in eventFinderPrevious if event is not None]
event_finder_event: [EventInfo] = EventFinderScrapper.fetch_events(set([event.name for event in eventFinderPrevious])) + eventFinderPrevious
# json.dump([e.to_dict() for e in event_finder_event], cacheFile)
# cacheFile.write(",\n")

print("fetching rogue")
roguePrevious = [EventInfo.from_dict(event) for event in previousEventTitles if event["source"] == "Rogue & Vagabond"]
roguePrevious = [event for event in roguePrevious if event is not None]
rogue_events = RougueScrapper.fetch_events(set([event.name for event in roguePrevious])) + roguePrevious
# json.dump([e.to_dict() for e in rogue_events], cacheFile)
# cacheFile.write(",\n")

print("fetching humanitix")
humanitixPrevious = [EventInfo.from_dict(event) for event in previousEventTitles if event["source"] == "Humanitix"]
humanitixPrevious = [event for event in humanitixPrevious if event is not None]
humanitix_events = HumanitixScrapper.fetch_events(set([event.name for event in humanitixPrevious])) + humanitixPrevious
# json.dump([e.to_dict() for e in humanitix_events], cacheFile)
# cacheFile.write(",\n")

print("fetching wellington High School")
wellingtonHighschoolPrevious = [EventInfo.from_dict(event) for event in previousEventTitles if event["source"] == "Wellington High School"]
wellingtonHighschoolPrevious = [event for event in wellingtonHighschoolPrevious if event is not None]
wellingtonHighschool_events = WellingtonHighschoolScrapper.fetch_events(set([event.name for event in wellingtonHighschoolPrevious])) + wellingtonHighschoolPrevious
# json.dump([e.to_dict() for e in wellingtonHighschool_events], cacheFile)
# cacheFile.write("\n}")
# cacheFile.close()

print("fetching event brite")
eventBritePrevious = [EventInfo.from_dict(event) for event in previousEventTitles if event["source"] == "Event Brite"]
eventBritePrevious = [event for event in eventBritePrevious if event is not None]
eventbrite_events = EventbriteScrapper.fetch_events(set([event.name for event in eventBritePrevious])) + eventBritePrevious

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
print("wellington High School: ", len(wellingtonHighschool_events))
print("event brite: ", len(eventbrite_events))

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
        + humanitix_events
        + wellingtonHighschool_events
        + eventbrite_events)

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
eventTypes = sorted(list(eventTypes))
eventTypes.append("Other")
filters = {
    "sources": sorted(list(sources)),
    "eventTypes": eventTypes,
}
with open("events.json", "w") as write:
    write.write('{ "events":')
    json.dump(data, write)
    write.write(',')
    write.write('"filters":')
    json.dump(filters, write)
    write.write('}')
