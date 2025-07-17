# https://www.cecwellington.ac.nz/w/courses/
from time import sleep
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

import FileNames
import ScrapperNames
from EventInfo import EventInfo
import re
from datetime import datetime
from dateutil import parser
from typing import List, Tuple, Set, Optional
import json


class WellingtonHighschoolScrapper:
    @staticmethod
    def slow_scroll_to_bottom(driver: webdriver):
        prev_height = 0
        while True:
            height = driver.execute_script("return document.body.scrollHeight")
            driver.execute_script(f"window.scrollBy(0, {height});")
            sleep(1)
            if prev_height == height:
                break
            prev_height = height

    @staticmethod
    def get_all_event_dates(driver: webdriver) -> List[datetime]:
        dates = []
        events_list: WebElement = driver.find_element(By.CLASS_NAME, "event-list")
        events = events_list.find_elements(By.XPATH, "//div[contains(@class, 'event ')]")
        for event in events:
            event_text = event.text
            regex = r"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)?\s*(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
            matches = re.search(regex, event_text)
            if not matches:
                continue
            date_day = matches.group(1)
            date_month = matches.group(2)
            matches = re.findall(r"\d{1,2}:\d{1,2}\s*[aAmMpP]{2}", event_text)
            hour = matches[0]
            dates.append(parser.parse(f"{date_day} {date_month} {hour}"))
            print(f"day: {date_day} month: {date_month} hour: {hour}")

        return dates

    @staticmethod
    def get_event(url: str, category: str, driver: webdriver) -> Optional[EventInfo]:
        driver.get(url)
        sleep(1)
        title: str = driver.find_element(By.CLASS_NAME, "page-title").text
        image_element: str = driver.find_element(By.CLASS_NAME, "image-hero").get_attribute("style")
        image_url = re.findall(r'url\("([^"]+)"\)', image_element)[0]
        dates = WellingtonHighschoolScrapper.get_all_event_dates(driver)
        description: str = driver.find_element(By.CLASS_NAME, "content-field-text").text
        print(dates)
        return EventInfo(name=title,
                         image=image_url,
                         venue="Wellington High School, 249 Taranaki Street, Te Aro, Wellington",
                         dates=dates,
                         url=url,
                         source=ScrapperNames.WELLINGTON_HIGH_SCHOOL,
                         event_type=category,
                         description=description)

    @staticmethod
    def get_events(url: str, previous_urls: Set[str], category: str, driver: webdriver, urls_file, out_file) -> List[EventInfo]:
        events: List[EventInfo] = []
        driver.get(url)
        WellingtonHighschoolScrapper.slow_scroll_to_bottom(driver)
        catalog = driver.find_element(By.CLASS_NAME, "catalogue")
        elements = catalog.find_elements(By.CLASS_NAME, "catalogue-item")
        event_urls: Set[str] = set()
        for element in elements:
            event_url = element.find_element(By.TAG_NAME, "a").get_attribute("href")
            if event_url in event_urls or event_url in previous_urls:
                continue
            event_urls.add(event_url)
        json.dump(list(event_urls), urls_file, indent=2)
        for event_url in event_urls:
            print(f"category: {category} url: {event_url}")
            try:
                event = WellingtonHighschoolScrapper.get_event(event_url, category, driver)
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
        return events

    @staticmethod
    def get_categories() -> List[Tuple[str, str]]:
        driver = webdriver.Chrome()
        driver.get("https://www.cecwellington.ac.nz/w/courses/")
        filters = driver.find_elements(By.CLASS_NAME, "radio-filter")
        categories = []
        for f in filters:
            a_tag = f.find_element(By.TAG_NAME, "a")
            category = (f.text, a_tag.get_attribute("href"))
            categories.append(category)
        driver.close()
        return categories

    @staticmethod
    def fetch_events(previous_urls: Set[str], previous_titles: Optional[Set[str]]) -> List[EventInfo]:
        categories = WellingtonHighschoolScrapper.get_categories()
        driver = webdriver.Chrome()
        events = []
        out_file = open(FileNames.WELLINGTON_HIGH_SCHOOL_EVENTS, mode="w")
        urls_file = open(FileNames.WELLINGTON_HIGH_SCHOOL_URLS, mode="w")
        out_file.write("[\n")
        for category in categories:
            category_name, url = category
            events += WellingtonHighschoolScrapper.get_events(url, previous_urls, category_name, driver, urls_file, out_file)
        out_file.write("]\n")
        out_file.close()
        urls_file.close()
        driver.close()
        return events


# events = list(map(lambda x: x.to_dict(), sorted(WelxlingtonHighschoolScrapper.fetch_events(set()), key=lambda k: k.name.strip())))
