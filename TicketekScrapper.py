import json
import random
import subprocess
from selenium.webdriver.chrome.options import Options
from datetime import datetime
from time import sleep
import FileUtils
import ScrapperNames
from EventInfo import EventInfo
import re
from dateutil import parser
from typing import List, Optional, Set
from selenium import webdriver
from selenium.webdriver.common.by import By

class TicketekScrapper:
    @staticmethod
    def extract_date(driver: webdriver) -> List[datetime]:
        dates: List[datetime] = []
        date_string: str = driver.find_element(By.CLASS_NAME, "selectDateBlock").text.split("\n")[1]
        matches: List[str] = re.findall(r"\d{1,2}\s[aA-zZ]{3,4}\s\d{4}", date_string)
        for match in matches:
            dates.append(parser.parse(match))
        return dates

    @staticmethod
    def get_event(url: str, category:str, driver: webdriver, previous_urls: Set[str]) -> Optional[List[EventInfo]]:
        driver.get(url)
        sleep(random.uniform(2, 3))
        sub_events = driver.find_elements(By.CLASS_NAME, "event-item")
        if sub_events:
            sub_driver = webdriver.Chrome()
            print("fetching sub events: ")
            events_info: List[EventInfo] = []
            for event in sub_events:
                venue_text: str = event.find_element(By.CLASS_NAME, "event-venue-dates").text
                if "wellington" in venue_text.lower():
                    url: str = event.find_element(By.CLASS_NAME, "event-buttons").find_element(By.TAG_NAME, "a").get_attribute("href")
                    print(f"sub event url: {url}")
                    parsed_events = TicketekScrapper.get_event(url, category, sub_driver, previous_urls)
                    if parsed_events:
                        for parsed_event in parsed_events:
                            events_info.append(parsed_event)
            if not events_info:
                print("none in wellington")
            sub_driver.close()
            return events_info
        title: str = driver.find_element(By.CLASS_NAME, "sectionHeading").text
        if url in previous_urls:
            return None
        previous_urls.add(url)
        dates = TicketekScrapper.extract_date(driver)
        image_url: str = driver.find_element(By.CLASS_NAME, "desktop-tablet-banner").get_attribute("src")
        venue: str = driver.find_element(By.CLASS_NAME, "selectVenueBlock").text.split("\n")[1]
        description: str = driver.find_element(By.CLASS_NAME, "info-details").text
        print(f"title: {title}")
        return [EventInfo(name=title,
                          dates=dates,
                          image="https://" + image_url,
                          url=url,
                          venue=venue,
                          source=ScrapperNames.TICKETEK,
                          event_type=category,
                          description=description)]

    @staticmethod
    def fetch_events(previous_urls: Set[str], previous_titles: Optional[Set[str]]) -> List[EventInfo]:
        out_file, urls_file, banned_file = FileUtils.get_files_for_scrapper(ScrapperNames.TICKETEK)
        previous_urls = previous_urls.union(set(FileUtils.load_banned(ScrapperNames.TICKETEK)))
        events_info: List[EventInfo] = []
        subprocess.run(['pkill', '-f', 'Google Chrome'])
        options = Options()

        options.add_argument("--profile-directory=Profile 1")  # Specify profile name only

        # For Apple Silicon Macs
        options.binary_location = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

        driver = webdriver.Chrome(options=options)
        driver.get("https://premier.ticketek.co.nz/search/SearchResults.aspx?k=wellington")
        cats = driver.find_elements(By.CLASS_NAME, "cat-nav-item")
        cats = [(cat.text, cat.get_attribute("href").split("c=")[-1]) for cat in cats if len(cat.get_attribute("href").split("c=")) > 1 and len(cat.text) > 0]
        cats.append(("Other", "Other"))
        event_urls: List[tuple[str, str]] = []
        for categoryName, categoryTag in cats:
            print(f"urls for categoryName: {categoryName}, categoryTag: {categoryTag}")
            page = 1
            while True:
                driver.get(f"https://premier.ticketek.co.nz/search/SearchResults.aspx?k=wellington&page={page}&c={categoryTag}")
                buttons = driver.find_elements(By.CLASS_NAME, "resultBuyNow")
                content_events = driver.find_elements(By.CLASS_NAME, "contentEvent")
                for button, content_event in zip(buttons, content_events):
                    event_url = button.find_element(By.TAG_NAME, "a").get_attribute("href")
                    if event_url in previous_urls:
                        continue
                    previous_urls.add(event_url)
                    event_urls.append((event_url, categoryName))
                    json.dump((event_url, categoryName), urls_file, indent=2)
                    urls_file.write(",\n")
                page += 1
                sleep(random.uniform(2, 3))
                try:
                    if driver.find_element(By.CLASS_NAME, "noResultsMessage"):
                        break
                except:
                    pass
                pagination = driver.find_element(By.CLASS_NAME, "paginationResults").text.split("-")[1]
                start, end = pagination.split(" of ")
                if start == end:
                    break
        out_file.write("[\n")
        for part in event_urls:
            print(f"category: {part[1]} url: {part[0]}")
            try:
                events = TicketekScrapper.get_event(part[0], part[1], driver, previous_urls)
                if not events:
                    continue
                for event in events:
                    if event:
                        events_info.append(event)
                        json.dump(event.to_dict(), out_file, indent=2)
                        out_file.write(",\n")
            except Exception as e:
                if "No dates found for" in str(e):
                    print("-" * 100)
                    json.dump(part[0], banned_file, indent=2)
                    banned_file.write(",\n")
                    print(e)
                else:
                    print("-" * 100)
                    raise e
            print("-"*100)
        out_file.write("]\n")
        out_file.close()
        banned_file.close()
        urls_file.close()
        driver.close()
        return events_info

# events = list(map(lambda x: x.to_dict(), sorted(TicketekScrapper.fetch_events(set()), key=lambda k: k.name.strip())))