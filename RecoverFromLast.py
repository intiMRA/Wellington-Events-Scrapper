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
encountered_last_crapper = False
previous_events = FileUtils.load_events(FileNames.EVENTS_FILTERED)
for scrapper_name in ScrapperNames.ALL_SCRAPER_NAMES:
    if scrapper_name == last_scrapper:
        encountered_last_crapper = True
    if encountered_last_crapper:
        FileUtils.write_last_scrapper(scrapper_name)
        print("-" * 200)
        print(f"fetching {scrapper_name}...")
        print("-" * 100)
        scrapper = ScrapperFactory.get_event_scrapper(scrapper_name)
        previous_list, previous_urls, previous_titles = ScrapperFactory.get_previous_events(scrapper_name,
                                                                                            previous_events)
        scrapper_events = (scrapper.fetch_events(previous_urls, previous_titles) + previous_list)
        for event in scrapper_events:
            loaded_urls.add(event.url)
        data += scrapper_events
        print(f"fetched: {len(data)} events")
        print("-" * 200)
    else:
        previous_list, _, _ = ScrapperFactory.get_previous_events(scrapper_name, previous_events)
        for event in previous_list:
            loaded_urls.add(event.url)
        data += previous_list

for file in FileUtils.all_event_file_names():
    print(f"processing: {file}")
    with open(file, mode="r") as f:
        file_text = f.read()
        if not file_text:
            continue
        file_json = json.loads(file_text.replace(',\n}', '\n}').replace(',\n]', '\n]'))
        for event_dict in file_json:
            try:
                event = EventInfo.from_dict(event_dict)
                if event and event.url not in loaded_urls:
                    print(event.name)
                    data.append(event)
            except Exception as e:
                if "No dates found for" in str(e):
                    pass
                raise e
            print("-" * 100)

FileUtils.write_to_events_file(data)
