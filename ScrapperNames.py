from typing import List
from datetime import datetime

WELLINGTON_NZ: str = "Wellington NZ"
WELLINGTON_HIGH_SCHOOL: str = "Wellington High School"
VALHALLA: str = "Valhalla"
UNDER_THE_RADAR: str = "Under The Radar"
TICKET_MASTER: str = "Ticket Master"
TICKETEK: str = "Ticketek"
SAN_FRAN: str = "San Fran"
ROGUE_AND_VAGABOND: str = "Rogue & Vagabond"
HUMANITIX: str = "Humanitix"
FACEBOOK: str = "Facebook"
EVENT_FINDER: str = "Event Finder"
EVENT_BRITE: str = "Event Brite"
WOAP: str = "WOAP"
ROXY: str = "Roxy Cinema"
ALL_EVENTS_IN = "All Events In"
now = datetime.now()

ALL_SCRAPER_NAMES: List[str] = [
    WELLINGTON_NZ,
    WELLINGTON_HIGH_SCHOOL,
    VALHALLA,
    UNDER_THE_RADAR,
    TICKET_MASTER,
    TICKETEK,
    SAN_FRAN,
    ROGUE_AND_VAGABOND,
    HUMANITIX,
    FACEBOOK,
    EVENT_FINDER,
    EVENT_BRITE,
    ROXY
]

if now.month == 8 or now.month == 7:
    ALL_SCRAPER_NAMES.append(WOAP)
