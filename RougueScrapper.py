from selenium import webdriver
from selenium.webdriver.common.by import By
from time import sleep
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
                        source="Rogue & Vagabond",
                        eventType="Music",
                         description=description)
    @staticmethod
    def fetch_events(previousTitltes: Set[str]) -> List[EventInfo]:
        eventsInfo: List[EventInfo] = []
        driver = webdriver.Chrome()
        event_urls: List[str] = []
        driver.get("https://rogueandvagabond.co.nz/")
        sleep(2)
        titles = driver.find_elements(By.CLASS_NAME, "vevent")
        for title in titles:
            if title.text in previousTitltes:
                continue
            event_urls.append(title.find_element(By.TAG_NAME, "a").get_attribute("href"))
        with open("rougeUrls.json", mode="w") as f:
            json.dump(event_urls, f)
        out_file = open("rougeEvents.json", mode="w")
        out_file.write("[\n")
        for url in event_urls:
            print(f"url: {url}")
            try:
                event = RougueScrapper.get_event(url, driver)
                if event:
                    eventsInfo.append(event)
                    json.dump(event.to_dict(), out_file, indent=2)
                    out_file.write(",\n")
            except Exception as e:
                print(e)
            print("-" * 100)
        out_file.write("]\n")
        driver.close()
        return eventsInfo

# events = list(map(lambda x: x.to_dict(), sorted(RougueScrapper.fetch_events(set()), key=lambda k: k.name.strip())))