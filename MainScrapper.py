from EventInfo import EventInfo
from SanFranScrapper import SanFranScrapper
from TicketekScrapper import TicketekScrapper
from TicketmasterScrapper import TicketmasterScrapper
from UnderTheRaderScrapper import UnderTheRaderScrapper
from ValhallaScrapper import ValhallaScrapper
from EventFinderScrapper import EventFinderScrapper
from RougueScrapper import RougueScrapper
import json

san_fran_events: [EventInfo] = SanFranScrapper.fetch_events()
ticket_events: [EventInfo] = TicketekScrapper.fetch_events()
ticket_master_events: [EventInfo] = TicketmasterScrapper.fetch_events()
under_the_radar_events: [EventInfo] = UnderTheRaderScrapper.fetch_events()
valhalla_events: [EventInfo] = ValhallaScrapper.fetch_events()
event_finder_event: [EventInfo] = EventFinderScrapper.fetch_events()
rogue_events = RougueScrapper.fetch_events()

print(len(san_fran_events))
print(len(ticket_events))
print(len(ticket_master_events))
print(len(under_the_radar_events))
print(len(valhalla_events))
print(len(event_finder_event))
print(len(rogue_events))
data =  san_fran_events + ticket_events + ticket_master_events + under_the_radar_events + valhalla_events + event_finder_event + rogue_events
data = list(map(lambda x: x.to_dict(), data))
with open( "evens.json" , "w" ) as write:
    json.dump( data , write )
with open( "evens.json" , "r" ) as read:
    print(json.loads(read.read()))