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

FileUtils.write_last_scrapper(ScrapperNames.WELLINGTON_NZ)
scrapper = ScrapperFactory.get_event_scrapper(ScrapperNames.WELLINGTON_NZ)
previous_list, previous_urls, previous_titles = ScrapperFactory.get_previous_events(ScrapperNames.WELLINGTON_NZ,
                                                                                    previous_events)
scrapper_events = (scrapper.fetch_events(previous_urls, previous_titles) + previous_list)
data += scrapper_events