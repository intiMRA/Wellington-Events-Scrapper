import json
from time import sleep
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec

import FileNames
import ScrapperNames
from EventInfo import EventInfo
from dateutil import parser
from typing import List, Set, Optional

class UnderTheRaderScrapper:
    @staticmethod
    def get_event(url: str, driver: webdriver) -> Optional[EventInfo]:
        driver.get(url)
        title: str = driver.find_element(By.CLASS_NAME, "display_title_1").text
        header = driver.find_element(By.CLASS_NAME, "col-md-9").text.split("\n")
        info_texts = driver.find_element(By.CLASS_NAME, "gig-guide-side-bar").text.split("\n")
        time = "1:01AM"
        found_gig_start = False
        for text in info_texts:
            if "GIG STARTS" in text:
                found_gig_start = True
            elif found_gig_start:
                time = text
                break
        date_string = header[2].split(",")[0]
        parts = date_string.split(" ")
        date = parser.parse(f"{parts[1]} {parts[2]} {time}")
        image_url = driver.find_element(By.CLASS_NAME, "img-responsive").get_attribute('src')
        venue = header[4]
        description = driver.find_element(By.CLASS_NAME, "description").text
        return EventInfo(name=title,
                         dates=[date],
                         image=image_url,
                         url=url,
                         venue=venue,
                         source=ScrapperNames.UNDER_THE_RADAR,
                         event_type="Music",
                         description=description)

    @staticmethod
    def fetch_events(previous_urls: Set[str]) -> List[EventInfo]:
        events: List[EventInfo] = []
        event_urls: List[str] = []
        driver = webdriver.Chrome()
        driver.get("https://www.undertheradar.co.nz/utr/gigRegion/Wellington")
        while True:
            try:
                load_mode_button = driver.find_element(By.XPATH, "//a[contains(., 'Load More')]")
                load_mode_button.click()
                sleep(1)
            except:
                break
        wait = WebDriverWait(driver, timeout=10, poll_frequency=1)
        _ = wait.until(ec.presence_of_element_located((By.CLASS_NAME, "vevent")))
        html = driver.find_elements(By.CLASS_NAME, 'vevent')
        for event in html:
            title: WebElement = event.find_element(By.CLASS_NAME, 'gig-title')
            url = title.find_element(By.TAG_NAME, "a").get_attribute("href")
            if url in previous_urls or url in event_urls:
                continue
            event_urls.append(url)
        with open(FileNames.UNDER_THE_RADAR_URLS, mode="w") as f:
            json.dump(event_urls, f)
        out_file = open(FileNames.UNDER_THE_RADAR_EVENTS, mode="w")
        out_file.write("[\n")
        for url in event_urls:
            print(f"url: {url}")
            try:
                event = UnderTheRaderScrapper.get_event(url, driver)
                if event:
                    events.append(event)
                    json.dump(event.to_dict(), out_file)
                    out_file.write(",\n")
            except Exception as e:
                print(e)
            print("-"*100)
        driver.close()
        out_file.write("]\n")
        out_file.close()
        return events

# events = list(map(lambda x: x.to_dict(), sorted(UnderTheRaderScrapper.fetch_events(set()), key=lambda k: k.name.strip())))