from typing import List, Set, Optional, Tuple

from scrapers.EventFinderScrapper import EventFinderScrapper
from scrapers.EventbriteScrapper import EventbriteScrapper
from scrapers.FacebookScrapper import FacebookScrapper
from scrapers.HumanitixScrapper import HumanitixScrapper
from scrapers.RougueScrapper import RougueScrapper
from scrapers.SanFranScrapper import SanFranScrapper
from scrapers.TicketekScrapper import TicketekScrapper
from scrapers.TicketmasterScrapper import TicketmasterScrapper
from scrapers.UnderTheRaderScrapper import UnderTheRaderScrapper
from scrapers.ValhallaScrapper import ValhallaScrapper
from scrapers.WellingtonHighschoolScrapper import WellingtonHighschoolScrapper
from scrapers.WellingtonNZScrapper import WellingtonNZScrapper
from scrapers.WoapScrapper import WoapScrapper
from scrapers.RoxyScrapper import RoxyScrapper
from scrapers.AllEventsInScrapper import AllEventsInScrapper
from scrapers.WellingtonHeritageFestivalScrapper import WellingtonHeritageFestivalScrapper
from scrapers.FringeScrapper import FringeScrapper
from model.EventInfo import EventInfo
from scrapers.ScrapperNames import ScraperName

_SCRAPERS: dict[ScraperName, type] = {
    ScraperName.WELLINGTON_NZ: WellingtonNZScrapper,
    ScraperName.WELLINGTON_HIGH_SCHOOL: WellingtonHighschoolScrapper,
    ScraperName.VALHALLA: ValhallaScrapper,
    ScraperName.UNDER_THE_RADAR: UnderTheRaderScrapper,
    ScraperName.TICKET_MASTER: TicketmasterScrapper,
    ScraperName.TICKETEK: TicketekScrapper,
    ScraperName.SAN_FRAN: SanFranScrapper,
    ScraperName.ROGUE_AND_VAGABOND: RougueScrapper,
    ScraperName.HUMANITIX: HumanitixScrapper,
    ScraperName.FACEBOOK: FacebookScrapper,
    ScraperName.EVENT_FINDER: EventFinderScrapper,
    ScraperName.EVENT_BRITE: EventbriteScrapper,
    ScraperName.WOAP: WoapScrapper,
    ScraperName.ROXY: RoxyScrapper,
    ScraperName.ALL_EVENTS_IN: AllEventsInScrapper,
    ScraperName.WELLINGTON_HERITAGE_FESTIVAL: WellingtonHeritageFestivalScrapper,
    ScraperName.FRINGE: FringeScrapper,
}


def get_event_scrapper(scrapper_name: ScraperName) -> type:
    try:
        return _SCRAPERS[scrapper_name]
    except KeyError:
        raise Exception(f"No scrapper found for {scrapper_name}")


EXCLUDE_PREVIOUS = [ScraperName.WOAP]


def get_previous_events(scrapper_name: ScraperName, previous_events: List[EventInfo]) -> Tuple[
    List[EventInfo], Set[str], Optional[Set[str]]]:
    if scrapper_name in EXCLUDE_PREVIOUS:
        return [], set(), set()
    previous_scrapper_events = [event for event in previous_events if
                                event.source == scrapper_name]
    previous_scrapper_events = [event for event in previous_scrapper_events if event is not None]
    return previous_scrapper_events, set([event.url for event in previous_scrapper_events]), set(
        [event.name for event in previous_scrapper_events])
