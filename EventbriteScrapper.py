# https://www.eventbrite.co.nz/d/new-zealand--wellington/all-events/
from datetime import datetime, timedelta

from selenium.webdriver.remote.webelement import WebElement

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
                    dates.append(DateFormatting.replaceYear(parser.parse(dateString)))
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
                         source="Event Brite",
                         eventType=category,
                         description=description)

    @staticmethod
    def get_events(driver: webdriver, titles: Set[str], category: str) -> List[EventInfo]:
        curentPage = 1
        events = []
        event_urls: Set[str] = set()
        while True:
            nextUrl = re.sub(r"page=\d+", f"page={curentPage}", driver.current_url)
            driver.get(nextUrl)
            try:
                sleep(1)
                pagination = driver.find_element(By.XPATH, "//li[@data-testid='pagination-parent']")
                firstPage, lastPage = pagination.text.split(" of ")
                firstPage = int(firstPage)
                lastPage = int(lastPage)
                if firstPage > lastPage:
                    break
            except Exception as e:
                print(f"error finding paginstion: {e}")
            curentPage += 1
            # search-event
            cards = driver.find_elements(By.XPATH, "//div[@data-testid='search-event']")
            for card in cards:
                titleTag = card.find_element(By.CLASS_NAME, "event-card-link ")
                eventLink = titleTag.get_attribute("href")
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
                title = texts[0]
                if title in titles or eventLink in event_urls:
                    continue
                titles.add(title)
                event_urls.add(eventLink)
        for url in event_urls:
            print(f"url: {url}")
            try:
                event: Optional[EventInfo] = EventbriteScrapper.get_event(url, driver, category)
                if event:
                    events.append(event)
            except Exception as e:
                print(e)
            print("-"*100)
        return events

    # TODO: delete
    @staticmethod
    def test() -> List[EventInfo]:
        events = []
        driver = webdriver.Chrome()
        event_urls: dict = {}
        with open("eventBriteUrls.json", mode="r") as f:
            event_urls = json.loads(f.read())
        for key in event_urls.keys():
            print(key)
            print("_" * 100)
            for url in event_urls[key]:
                print(url)
                try:
                    event: Optional[EventInfo] = EventbriteScrapper.get_event(url, driver, key)
                    if event:
                        events.append(event)
                except Exception as e:
                    print(e)
            print("_" * 100)
        try:
            driver.close()
        except:
            pass
        return events

    @staticmethod
    def fetch_events(previousTitles: Set[str]) -> List[EventInfo]:
        events = []
        driver = webdriver.Chrome()
        driver.get('https://www.eventbrite.co.nz/d/new-zealand--wellington/all-events/')
        cats = EventbriteScrapper.get_categories(driver)
        for cat in cats:
            catName, link = cat
            print("fetching: ", catName)
            print("_"*100)
            driver.get(link)
            start_date = datetime.now()
            end_date = start_date + relativedelta(days=30)
            # &start_date=2025-05-23&end_date=2025-06-29
            new_url = (driver.current_url.replace("/b/", "/d/")
                       + f"/?page=1&start_date={start_date.year}-{start_date.month}-{start_date.day}"
                         f"&end_date={end_date.year}-{end_date.month}-{end_date.day}")
            driver.get(new_url)
            events += EventbriteScrapper.get_events(driver, previousTitles, catName)
        driver.close()
        return events


# events = list(map(lambda x: x.to_dict(), sorted(EventbriteScrapper.test(), key=lambda k: k.name.strip())))
# with open('eventsBrite.json', 'w') as outfile:
#     json.dump(events, outfile)
