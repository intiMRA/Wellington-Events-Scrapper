from typing import Any, List, Set, Optional, Tuple

from EventFinderScrapper import EventFinderScrapper
from EventbriteScrapper import EventbriteScrapper
from FacebookScrapper import FacebookScrapper
from HumanitixScrapper import HumanitixScrapper
from RougueScrapper import RougueScrapper
from SanFranScrapper import SanFranScrapper
from TicketekScrapper import TicketekScrapper
from TicketmasterScrapper import TicketmasterScrapper
from UnderTheRaderScrapper import UnderTheRaderScrapper
from ValhallaScrapper import ValhallaScrapper
from WellingtonHighschoolScrapper import WellingtonHighschoolScrapper
from WellingtonNZScrapper import WellingtonNZScrapper
from WoapScrapper import WoapScrapper
from RoxyScrapper import RoxyScrapper
from AllEventsInScrapper import AllEventsInScrapper
from EventInfo import EventInfo
import ScrapperNames


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
    elif scrapper_name == ScrapperNames.WOAP:
        return WoapScrapper
    elif scrapper_name == ScrapperNames.ROXY:
        return RoxyScrapper
    elif scrapper_name == ScrapperNames.ALL_EVENTS_IN:
        return AllEventsInScrapper
    raise Exception(f"No scrapper found for {scrapper_name}")


EXCLUDE_PREVIOUS = [ScrapperNames.WOAP]


def get_previous_events(scrapper_name: str, previous_events: List[EventInfo]) -> Tuple[
    List[EventInfo], Set[str], Optional[Set[str]]]:
    if scrapper_name in EXCLUDE_PREVIOUS:
        return [], set(), set()
    previous_scrapper_events = [event for event in previous_events if
                                event.source == scrapper_name]
    previous_scrapper_events = [event for event in previous_scrapper_events if event is not None]
    return previous_scrapper_events, set([event.url for event in previous_scrapper_events]), set(
        [event.name for event in previous_scrapper_events])
