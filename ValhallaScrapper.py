import json

from future.backports.datetime import timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

import FileUtils
import ScrapperNames
from EventInfo import EventInfo
from dateutil import parser
from typing import List, Set, Optional
from datetime import datetime
from time import sleep


class ValhallaScrapper:
    @staticmethod
    def get_dates(driver: webdriver) -> List[datetime]:
        start_time = driver.find_elements(By.CLASS_NAME, "event-time-localized-start")
        if start_time:
            date = driver.find_element(By.CLASS_NAME, 'event-date').text
            start_time_text = start_time[0].text
            return [parser.parse(f"{date} {start_time_text}")]
        times = driver.find_elements(By.CLASS_NAME, "eventitem-meta-time")
        dates = driver.find_elements(By.CLASS_NAME, 'event-date')
        start_time = parser.parse(f"{dates[0].text} {times[0].text}")
        end_time = parser.parse(f"{dates[1].text} {times[1].text}")
        if end_time.day != start_time.day and abs(end_time - start_time) > timedelta(hours=5):
            return [start_time, end_time]
        return [start_time]

    @staticmethod
    def get_event(url: str, image_url: str, driver: webdriver) -> Optional[EventInfo]:
        driver.get(url)
        sleep(1)
        info_column: WebElement = driver.find_element(By.CLASS_NAME, "eventitem-column-meta")
        title = info_column.find_element(By.XPATH, "//*[contains(@class, 'eventitem-title')]").text
        dates = ValhallaScrapper.get_dates(driver)
        driver.execute_script(f"window.scrollBy(0, 1000);")
        sleep(1)
        venue = "Valhalla, Wellington"
        description = driver.find_element(By.CLASS_NAME, "sqs-html-content").text
        return EventInfo(name=title,
                         dates=dates,
                         image=image_url,
                         url=url,
                         venue=venue,
                         source=ScrapperNames.VALHALLA,
                         event_type="Music",
                         description=description)

    @staticmethod
    def slow_scroll_to_bottom(driver, previous_urls: Set[str], out_file, urls_file, banned_file, scroll_increment=300) -> List[EventInfo]:
        events: List[EventInfo] = []
        height = driver.execute_script("return document.body.scrollHeight")
        scrolled_amount = 0
        event_urls: Set[tuple[str, str]] = set()
        urls_file.write("[\n")
        while True:
            if scrolled_amount > height:
                break
            driver.execute_script(f"window.scrollBy(0, {scroll_increment});")

            scrolled_amount += scroll_increment
            html = driver.find_elements(By.CLASS_NAME, 'eventlist-event')
            for event in html:
                title_element: WebElement = event.find_element(By.CLASS_NAME, 'eventlist-title')
                if not title_element.text:
                    continue
                url = title_element.find_element(By.TAG_NAME, "a").get_attribute("href")
                if url in previous_urls:
                    continue
                previous_urls.add(url)
                image_url = event.find_element(By.TAG_NAME, "img").get_attribute("src")
                event_urls.add((url, image_url))
                json.dump((url, image_url), urls_file, indent=2)
                urls_file.write(",\n")
        urls_file.write("]\n")
        out_file.write("[\n")
        for part in event_urls:
            print(f"url: {part[0]}")
            try:
                event = ValhallaScrapper.get_event(part[0], part[1], driver)
                if event:
                    events.append(event)
                    json.dump(event.to_dict(), out_file, indent=2)
                    out_file.write(",\n")
            except Exception as e:
                if "No dates found for" in str(e):
                    print("-" * 100)
                    print(e)
                    json.dump(part[0], banned_file, indent=2)
                    banned_file.write(",\n")
                else:
                    print("-" * 100)
                    raise e
            print("-" * 100)
        out_file.write("]\n")
        out_file.close()
        driver.close()
        return events

    @staticmethod
    def fetch_events(previous_urls: Set[str], previous_titles: Optional[Set[str]]) -> List[EventInfo]:
        out_file, urls_file, banned_file = FileUtils.get_files_for_scrapper(ScrapperNames.VALHALLA)
        previous_urls = previous_urls.union(set(FileUtils.load_banned(ScrapperNames.VALHALLA)))
        driver = webdriver.Chrome()
        driver.get("https://www.valhallatavern.com/events-1")
        events = ValhallaScrapper.slow_scroll_to_bottom(driver, previous_urls,out_file, urls_file, banned_file, scroll_increment=1000)
        out_file.close()
        urls_file.close()
        banned_file.close()
        return events


# events = list(map(lambda x: x.to_dict(), sorted(ValhallaScrapper.fetch_events(set()), key=lambda k: k.name.strip())))
