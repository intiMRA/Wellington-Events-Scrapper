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
import json
import re

san_fran_events: [EventInfo] = SanFranScrapper.fetch_events()
ticket_events: [EventInfo] = TicketekScrapper.fetch_events()
ticket_master_events: [EventInfo] = TicketmasterScrapper.fetch_events()
under_the_radar_events: [EventInfo] = UnderTheRaderScrapper.fetch_events()
valhalla_events: [EventInfo] = ValhallaScrapper.fetch_events()
event_finder_event: [EventInfo] = EventFinderScrapper.fetch_events()
rogue_events = RougueScrapper.fetch_events()
wellyNZ_events = WellingtonNZScrapper.fetch_events()
humanitix_events = HumanitixScrapper.fetch_events()

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
data =  (san_fran_events
         + ticket_events
         + ticket_master_events
         + under_the_radar_events
         + valhalla_events
         + event_finder_event
         + rogue_events
         + wellyNZ_events
         + humanitix_events)

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
data = list(map(lambda x: x.to_dict(), sorted(data, key=lambda k: k.name.strip())))
eventsWithNoDate = list(filter(lambda x: not x["dates"], data))
events = list(filter(lambda x: x not in eventsWithNoDate, data))
with open( "evens.json" , "w" ) as write:
    write.write('{ "eventsWithNoDate":')
    json.dump(eventsWithNoDate, write)
    write.write(',')
    write.write('"events":')
    json.dump( data , write )
    write.write('}')