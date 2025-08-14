import json

import FileNames
import FileUtils
import ScrapperFactory
import ScrapperNames
from EventInfo import EventInfo
from typing import List, Set

data: List[EventInfo] = []
loaded_urls: Set[str] = set()
last_scrapper = FileUtils.load_last_scrapper()
previous_events = FileUtils.load_events(FileNames.EVENTS_FILTERED)

FileUtils.write_last_scrapper(ScrapperNames.EVENT_BRITE)
scrapper = ScrapperFactory.get_event_scrapper(ScrapperNames.EVENT_BRITE)
previous_list, previous_urls, previous_titles = ScrapperFactory.get_previous_events(ScrapperNames.EVENT_BRITE,
                                                                                    previous_events)
scrapper_events = (scrapper.fetch_events(previous_urls, previous_titles) + previous_list)
data += scrapper_events