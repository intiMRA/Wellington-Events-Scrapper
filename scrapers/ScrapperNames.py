from datetime import datetime
from enum import StrEnum


class ScraperName(StrEnum):
    WELLINGTON_NZ = "Wellington NZ"
    WELLINGTON_HIGH_SCHOOL = "Wellington High School"
    WELLINGTON_HERITAGE_FESTIVAL = "Wellington Heritage Festival"
    VALHALLA = "Valhalla"
    UNDER_THE_RADAR = "Under The Radar"
    TICKET_MASTER = "Ticket Master"
    TICKETEK = "Ticketek"
    SAN_FRAN = "San Fran"
    ROGUE_AND_VAGABOND = "Rogue & Vagabond"
    HUMANITIX = "Humanitix"
    FACEBOOK = "Facebook"
    EVENT_FINDER = "Event Finder"
    EVENT_BRITE = "Event Brite"
    WOAP = "WOAP"
    ROXY = "Roxy Cinema"
    ALL_EVENTS_IN = "All Events In"
    FRINGE = "Fringe"


now = datetime.now()
ALL_SCRAPER_NAMES: list[ScraperName] = [
    ScraperName.EVENT_BRITE,
    ScraperName.WELLINGTON_HIGH_SCHOOL,
    ScraperName.VALHALLA,
    ScraperName.UNDER_THE_RADAR,
    ScraperName.TICKET_MASTER,
    ScraperName.TICKETEK,
    ScraperName.SAN_FRAN,
    ScraperName.ROGUE_AND_VAGABOND,
    ScraperName.HUMANITIX,
    ScraperName.FACEBOOK,
    ScraperName.EVENT_FINDER,
    ScraperName.ALL_EVENTS_IN,
    ScraperName.WELLINGTON_NZ,
    ScraperName.ROXY,
    ScraperName.WELLINGTON_HERITAGE_FESTIVAL,
    ScraperName.FRINGE,
]

if now.month <= 8 or now.month >= 6:
    ALL_SCRAPER_NAMES.append(ScraperName.WOAP)
