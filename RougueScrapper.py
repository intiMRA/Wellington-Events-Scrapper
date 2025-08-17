from selenium import webdriver
from selenium.webdriver.common.by import By
from time import sleep

import FileUtils
import ScrapperNames
from EventInfo import EventInfo
from dateutil import parser
from typing import List, Set, Optional
import json


class RougueScrapper:
    @staticmethod
    def get_event(url: str, driver: webdriver) -> Optional[EventInfo]:
        driver.get(url)
        title: str = driver.find_element(By.CLASS_NAME, "display_title_1").text
        date_string = driver.find_element(By.CLASS_NAME, "col-md-9").text.split("\n")[2].split(",")[0]
        info_texts = driver.find_element(By.CLASS_NAME, "gig-guide-side-bar").text.split("\n")
        time = "1:01AM"
        found_gig_start = False
        for text in info_texts:
            if "GIG STARTS" in text:
                found_gig_start = True
            elif found_gig_start:
                time = text
                break
        parts = date_string.split(" ")
        date = parser.parse(f"{parts[1]} {parts[2]} {time}")
        image_url = driver.find_element(By.CLASS_NAME, "img-responsive").get_attribute('src')
        venue = "The Rogue & Vagabond"
        description = driver.find_element(By.CLASS_NAME, "description").text
        return EventInfo(name=title,
                         dates=[date],
                         image=image_url,
                         url=url,
                         venue=venue,
                         source=ScrapperNames.ROGUE_AND_VAGABOND,
                         event_type="Music",
                         description=description)

    @staticmethod
    def get_urls(driver: webdriver, previous_urls, urls_file) -> Set[str]:
        urls_file.write("[\n")
        event_urls: Set[str] = set()
        driver.get("https://rogueandvagabond.co.nz/")
        sleep(2)
        titles = driver.find_elements(By.CLASS_NAME, "vevent")
        for title in titles:
            event_url = title.find_element(By.TAG_NAME, "a").get_attribute("href")
            if event_url in previous_urls or event_url in event_urls:
                continue
            event_urls.add(event_url)
            json.dump(event_url, urls_file, indent=2)
            urls_file.write(",\n")
        urls_file.write("]\n")
        return event_urls
    @staticmethod
    def fetch_events(previous_urls: Set[str], previous_titles: Optional[Set[str]]) -> List[EventInfo]:
        out_file, urls_file, banned_file = FileUtils.get_files_for_scrapper(ScrapperNames.ROGUE_AND_VAGABOND)
        previous_urls = previous_urls.union(set(FileUtils.load_banned(ScrapperNames.ROGUE_AND_VAGABOND)))
        driver = webdriver.Chrome()
        event_urls = RougueScrapper.get_urls(driver, previous_urls, urls_file)
        events = []
        out_file.write("[\n")
        for url in event_urls:
            print(f"url: {url}")
            try:
                event = RougueScrapper.get_event(url, driver)
                if event:
                    events.append(event)
                    json.dump(event.to_dict(), out_file, indent=2)
                    out_file.write(",\n")
            except Exception as e:
                if "No dates found for" in str(e):
                    print("-" * 100)
                    print(e)
                else:
                    print("-" * 100)
                    raise e
            print("-" * 100)
        out_file.write("]\n")
        out_file.close()
        urls_file.close()
        banned_file.close()
        driver.close()
        return events

# events = list(map(lambda x: x.to_dict(), sorted(RougueScrapper.fetch_events(set()), key=lambda k: k.name.strip())))
