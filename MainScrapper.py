from util import FileUtils
from scrapers import ScrapperFactory
from scrapers import ScrapperNames
from model.EventInfo import EventInfo
from classification import TextClassifier
from typing import List
from util import FileNames
from util.Logger import Logger

data: List[EventInfo] = []
new_event_counts: dict[ScrapperNames.ScraperName, int] = {}
previous_events = FileUtils.load_events()
FileUtils.write_to_events_file(previous_events, FileNames.EVENTS_FILTERED)
for scrapper_name in ScrapperNames.ALL_SCRAPER_NAMES:
    FileUtils.write_last_scrapper(scrapper_name)
    Logger.set_source(scrapper_name)
    Logger.divider()
    Logger.info(f"fetching {scrapper_name}...")
    scrapper = ScrapperFactory.get_event_scrapper(scrapper_name)
    previous_list, previous_urls, previous_titles = ScrapperFactory.get_previous_events(scrapper_name, previous_events)
    new_events = scrapper.fetch_events(previous_urls, previous_titles)
    new_event_counts[scrapper_name] = len(new_events)
    data += (new_events + previous_list)
    Logger.info(f"fetched: {len(data)} events so far")

Logger.set_source("")
Logger.info(f"classifying {len(data)} events...")
TextClassifier.classify_events(data)

FileUtils.write_to_events_file(data)

Logger.divider()
Logger.table(["scraper", "new events"],
             [[name, count] for name, count in new_event_counts.items()]
             + [["total", sum(new_event_counts.values())]])
