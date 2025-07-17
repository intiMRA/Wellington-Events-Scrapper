import FileUtils
import ScrapperFactory
import ScrapperNames
from EventInfo import EventInfo
from typing import List
data: List[EventInfo] = []
for scrapper_name in ScrapperNames.ALL_SCRAPER_NAMES:
    FileUtils.write_last_scrapper(scrapper_name)
    print("-" * 200)
    print(f"fetching {scrapper_name}...")
    print("-" * 100)
    scrapper = ScrapperFactory.get_event_scrapper(scrapper_name)
    previous_list, previous_urls = ScrapperFactory.get_previous_events(scrapper_name)
    data += (scrapper.fetch_events(previous_urls) + previous_list)
    print(f"fetched: {len(data)} events")
    print("-" * 200)

FileUtils.write_to_events_file(data)