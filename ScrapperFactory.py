import json
from typing import Any, List, Set, Optional

from EventFinderScrapper import EventFinderScrapper
from EventbriteScrapper import EventbriteScrapper
from FacebookScrapper import FacebookScrapper
import FileNames
from HumanitixScrapper import HumanitixScrapper
from RougueScrapper import RougueScrapper
from SanFranScrapper import SanFranScrapper
from TicketekScrapper import TicketekScrapper
from TicketmasterScrapper import TicketmasterScrapper
from UnderTheRaderScrapper import UnderTheRaderScrapper
from ValhallaScrapper import ValhallaScrapper
from WellingtonHighschoolScrapper import WellingtonHighschoolScrapper
from WellingtonNZScrapper import WellingtonNZScrapper
from EventInfo import EventInfo
import ScrapperNames

with open(FileNames.EVENTS, mode="r") as f:
    evts = json.loads(f.read())
    previous_event_titles = evts["events"]


def get_event_scrapper(scrapper_name: str) -> Any:
    if scrapper_name == ScrapperNames.WELLINGTON_NZ:
        return WellingtonNZScrapper
    elif scrapper_name == ScrapperNames.WELLINGTON_HIGH_SCHOOL:
        return WellingtonHighschoolScrapper
    elif scrapper_name == ScrapperNames.VALHALLA:
        return ValhallaScrapper
    elif scrapper_name == ScrapperNames.UNDER_THE_RADAR:
        return UnderTheRaderScrapper
    elif scrapper_name == ScrapperNames.TICKET_MASTER:
        return TicketmasterScrapper
    elif scrapper_name == ScrapperNames.TICKETEK:
        return TicketekScrapper
    elif scrapper_name == ScrapperNames.SAN_FRAN:
        return SanFranScrapper
    elif scrapper_name == ScrapperNames.ROGUE_AND_VAGABOND:
        return RougueScrapper
    elif scrapper_name == ScrapperNames.HUMANITIX:
        return HumanitixScrapper
    elif scrapper_name == ScrapperNames.FACEBOOK:
        return FacebookScrapper
    elif scrapper_name == ScrapperNames.EVENT_FINDER:
        return EventFinderScrapper
    elif scrapper_name == ScrapperNames.EVENT_BRITE:
        return EventbriteScrapper
    raise Exception(f"No scrapper found for {scrapper_name}")


def get_previous_events(scrapper_name: str) -> tuple[List[EventInfo], Set[str], Optional[Set[str]]]:
    previous_scrapper_events = [EventInfo.from_dict(event) for event in previous_event_titles if
                                event["source"] == scrapper_name]
    previous_scrapper_events = [event for event in previous_scrapper_events if event is not None]
    return previous_scrapper_events, set([event.url for event in previous_scrapper_events]), set(
        [event.name for event in previous_scrapper_events])
