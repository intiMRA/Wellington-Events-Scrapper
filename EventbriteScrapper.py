from datetime import datetime

from selenium.webdriver.remote.webelement import WebElement

import FileNames
import ScrapperNames
from DateFormatting import DateFormatting

from selenium.webdriver.common.by import By
from EventInfo import EventInfo
from selenium import webdriver
import re
from dateutil.relativedelta import relativedelta
from dateutil import parser
import json
from time import sleep
from typing import List, Tuple, Set, Optional


class EventbriteScrapper:
    @staticmethod
    def get_all_dates(driver: webdriver) -> List[datetime]:
        sleep(1)
        dates = []
        try:
            driver.find_element(By.XPATH, "//div[contains(., 'looking for was not found')]")
            return []
        except:
            pass
        try:
            elements = driver.find_elements(By.CLASS_NAME, "child-event-dates-item")
            if not elements:
                raise Exception("no child-event-dates-item")
            print("multi dates...")
            for e in elements:
                parts = e.text.split("\n")
                if len(parts) > 3:
                    parts = parts[1:]
                    dateString = parts[0] + " " + parts[1] + " " + parts[2]
                    dates.append(DateFormatting.replace_year(parser.parse(dateString)))
            return dates
        except:
            try:
                date_string: str = driver.find_element(By.CLASS_NAME, "date-info__full-datetime").text
                date_string: str = re.sub('NZST', "", date_string)
                parts: List[str] = date_string.split(",")[-1].split("-")
                date_string = parts[0].strip().replace(" · ", " ")
                if not re.findall(r'[AaMmpP]{2}', date_string):
                    amPm = parts[-1].strip()
                    amPm = re.findall(r"[AaMmpP]{2}", amPm)[0]
                    date_string = f"{date_string} {amPm}"
                print(date_string)
                return [parser.parse(date_string)]
            except Exception as e:
                print(e)
                return []

    @staticmethod
    def get_categories(driver: webdriver) -> List[Tuple[str, str]]:
        categories = []
        driver.find_element(By.CLASS_NAME, "filter-toggle").click()
        filters = driver.find_element(By.CLASS_NAME, "filter-choice-items")
        cats = filters.find_elements(By.TAG_NAME, "li")
        for cat in cats:
            link = cat.find_element(By.TAG_NAME, "a").get_attribute("href")
            category = (cat.text, link)
            categories.append(category)
        return categories

    @staticmethod
    def get_event(url: str, driver: webdriver, category: str) -> Optional[EventInfo]:
        driver.get(url)
        try:
            button: WebElement = driver.find_element(By.XPATH, "//button[@data-testid='view-event-details-button']")
            button.click()
        except:
            pass

        location_text: str = driver.find_element(By.CLASS_NAME, "location-info__address").text
        if "leadflake" in location_text:
            return None
        split: List[str] = location_text.split("\n")
        if len(split) == 3:
            venue: str = split[1]
        else:
            venue: str = split[0]
        venue = re.sub(r"#?[Ll](?:evel)?\s?(\d+)|\s*#?(\d+)", "", venue)
        print(venue)
        try:
            title: str = driver.find_element(By.CLASS_NAME, "event-title").text
        except:
            raise Exception("no title")
        image_url = driver.find_element(By.XPATH, "//img[@data-testid='hero-img']").get_attribute("src")
        event_link: str = url
        dates: List[datetime] = EventbriteScrapper.get_all_dates(driver)
        description: str = driver.find_element(By.ID, "event-description").text
        if "copyright" in description:
            return None
        return EventInfo(name=title,
                         image=image_url,
                         venue=venue,
                         dates=dates,
                         url=event_link,
                         source=ScrapperNames.EVENT_BRITE,
                         event_type=category,
                         description=description)

    @staticmethod
    def get_events(driver: webdriver, previous_urls: Set[str], category: str, out_file, urls_file) -> List[EventInfo]:
        current_page = 1
        events = []
        event_urls: Set[str] = set()
        while True:
            next_url = re.sub(r"page=\d+", f"page={current_page}", driver.current_url)
            driver.get(next_url)
            try:
                sleep(1)
                pagination = driver.find_element(By.XPATH, "//li[@data-testid='pagination-parent']")
                first_page, last_page = pagination.text.split(" of ")
                first_page = int(first_page)
                last_page = int(last_page)
                if first_page > last_page:
                    break
            except Exception as e:
                print(f"error finding paginstion: {e}")
            current_page += 1
            # search-event
            cards = driver.find_elements(By.XPATH, "//div[@data-testid='search-event']")
            for card in cards:
                title_tag = card.find_element(By.CLASS_NAME, "event-card-link ")
                event_url = title_tag.get_attribute("href")
                texts = card.text.split("\n")

                tags = [
                    "Sales end soon",
                    "Selling quickly",
                    "Nearly full",
                    "Just added",
                    "Not Yet On Sale"
                ]

                soldTags = [
                    "Sold Out",
                    "Sales Ended",
                    "Unavailable"
                ]
                if texts[0] in soldTags:
                    continue
                if texts[0] in tags:
                    texts = texts[1:]
                if len(texts) < 3:
                    continue
                if event_url in previous_urls or event_url in event_urls:
                    continue
                event_urls.add(event_url)
            json.dump(event_urls, urls_file)
        for url in event_urls:
            print(f"category: {category} url: {url}")
            try:
                event: Optional[EventInfo] = EventbriteScrapper.get_event(url, driver, category)
                if event:
                    events.append(event)
                    json.dump(event.to_dict(), out_file)
                    out_file.write(",\n")
            except Exception as e:
                if "No dates found for" in str(e):
                    print("-" * 100)
                    print(e)
                else:
                    print("-" * 100)
                    raise e
            print("_" * 100)
        return events

    @staticmethod
    def fetch_events(previous_urls: Set[str]) -> List[EventInfo]:
        events = []
        driver = webdriver.Chrome()
        driver.get('https://www.eventbrite.co.nz/d/new-zealand--wellington/all-events/')
        cats = EventbriteScrapper.get_categories(driver)
        out_file = open(FileNames.EVENTBRITE_EVENTS, mode="w")
        urls_file = open(FileNames.EVENTBRITE_URLS, mode="w")
        out_file.write("[\n")
        for cat in cats:
            cat_name, link = cat
            print("fetching: ", cat_name)
            print("_" * 100)
            driver.get(link)
            start_date = datetime.now()
            end_date = start_date + relativedelta(days=30)
            # &start_date=2025-05-23&end_date=2025-06-29
            new_url = (driver.current_url.replace("/b/", "/d/")
                       + f"/?page=1&start_date={start_date.year}-{start_date.month}-{start_date.day}"
                         f"&end_date={end_date.year}-{end_date.month}-{end_date.day}")
            driver.get(new_url)
            events += EventbriteScrapper.get_events(driver, previous_urls, cat_name, out_file, urls_file)
        driver.close()
        out_file.write("]\n")
        out_file.close()
        urls_file.close()
        return events

# events = list(map(lambda x: x.to_dict(), sorted(EventbriteScrapper.test(), key=lambda k: k.name.strip())))
