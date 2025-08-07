import FileUtils
import ScrapperFactory
import ScrapperNames
from EventInfo import EventInfo
from typing import List
import FileNames
data: List[EventInfo] = []
previous_events = FileUtils.load_events()
FileUtils.write_to_events_file(previous_events, FileNames.EVENTS_FILTERED)
for scrapper_name in ScrapperNames.ALL_SCRAPER_NAMES:
    FileUtils.write_last_scrapper(scrapper_name)
    print("-" * 200)
    print(f"fetching {scrapper_name}...")
    print("-" * 100)
    scrapper = ScrapperFactory.get_event_scrapper(scrapper_name)
    previous_list, previous_urls, previous_titles = ScrapperFactory.get_previous_events(scrapper_name, previous_events)
    data += (scrapper.fetch_events(previous_urls, previous_titles) + previous_list)
    print(f"fetched: {len(data)} events")
    print("-" * 200)

FileUtils.write_to_events_file(data)