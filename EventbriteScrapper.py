from datetime import datetime
import FileUtils
from selenium.webdriver.remote.webelement import WebElement

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
            except:
                try:
                    availability_button: WebElement = driver.find_element(By.XPATH, "//button[contains(., 'Check availability')]")
                    availability_button.click()
                    sleep(5)
                    print("finding from modem")
                    iframe_element = driver.find_element(By.XPATH, "//iframe[contains(@id, 'eventbrite-widget-modal')]")
                    driver.switch_to.frame(iframe_element)
                    dates = []
                    cards: List[WebElement] = driver.find_elements(By.XPATH, "//div[contains(@class, 'eds-card')]")
                    for card in cards:
                        day = card.find_element(By.XPATH, "//p[@data-spec='date-thumbnail-day']").text
                        month = card.find_element(By.XPATH, "//p[@data-spec='date-thumbnail-month']").text
                        hour = "1:01AM"
                        hour_element = card.find_elements(By.XPATH, "//div[@data-spec='series-event-card-date-string']")
                        if hour_element:
                            hour_element_string = hour_element[0].text
                            matches = re.findall(r"\d{1,2}\S*:\s*{d{1,2}\s*[aAmMpP]{2}", hour_element_string)
                            if matches:
                                hour = matches[0]
                        print(f"date: {day} {month} {hour}")
                        dates.append(parser.parse(f"{day} {month} {hour}"))
                    return dates
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
    def get_event(url: str, driver: webdriver, category: str, banned_file) -> Optional[EventInfo]:
        driver.get(url)
        try:
            button: WebElement = driver.find_element(By.XPATH, "//button[@data-testid='view-event-details-button']")
            button.click()
        except:
            pass
        try:
            location_text: str = driver.find_element(By.CLASS_NAME, "location-info__address").text
        except:
            return None
        if "leadflake" in location_text.lower():
            print(f"banning: {url}")
            json.dump(url, banned_file, indent=2)
            banned_file.write(",\n")
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
        try:
            image_url = driver.find_element(By.XPATH, "//img[@data-testid='hero-img']").get_attribute("src")
        except:
            image_url = ""
        event_link: str = url
        description: str = driver.find_element(By.ID, "event-description").text
        dates: List[datetime] = EventbriteScrapper.get_all_dates(driver)
        if not dates:
            date_matches = re.findall(r"\d{1,2}\s\w+\d{0,4}", title)
            hour = "1:01AM"
            hour_matches = re.findall(r"\d{1,2}\s:\d{2}[aAmMpP]{0,2}", title)
            if hour_matches:
                hour = hour_matches[0]
            for date_match in date_matches:
                try:
                    dates.append(parser.parse(f"{date_match} {hour}"))
                except:
                    continue

        if "copyright" in description:
            print(f"banning: {url}")
            json.dump(url, banned_file, indent=2)
            banned_file.write(",\n")
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
    def get_events(driver: webdriver, previous_urls: Set[str], category: str, out_file, urls_file, banned_file) -> List[EventInfo]:
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
                previous_urls.add(event_url)
                event_urls.add(event_url)
                json.dump(event_url, urls_file)
                urls_file.write(",\n")
        for url in event_urls:
            print(f"category: {category} url: {url}")
            try:
                event: Optional[EventInfo] = EventbriteScrapper.get_event(url, driver, category, banned_file)
                if event:
                    events.append(event)
                    json.dump(event.to_dict(), out_file, indent=2)
                    out_file.write(",\n")
            except Exception as e:
                if "No dates found for" in str(e):
                    json.dump(url, banned_file, indent=2)
                    banned_file.write(",\n")
                    previous_urls.add(url)
                    print("-" * 100)
                    print(e)
                else:
                    print("-" * 100)
                    raise e
            print("_" * 100)
        return events

    @staticmethod
    def fetch_events(previous_urls: Set[str], previous_titles: Optional[Set[str]]) -> List[EventInfo]:
        events = []
        driver = webdriver.Chrome()
        driver.get('https://www.eventbrite.co.nz/d/new-zealand--wellington/all-events/')
        cats = EventbriteScrapper.get_categories(driver)
        out_file, urls_file, banned_file = FileUtils.get_files_for_scrapper(ScrapperNames.EVENT_BRITE)
        previous_urls = previous_urls.union(set(FileUtils.load_banned(ScrapperNames.EVENT_BRITE)))
        out_file.write("[\n")
        urls_file.write("[\n")
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
            events += EventbriteScrapper.get_events(driver, previous_urls, cat_name, out_file, urls_file, banned_file)
        driver.close()
        out_file.write("]\n")
        urls_file.write("]\n")
        out_file.close()
        urls_file.close()
        return events

# events = list(map(lambda x: x.to_dict(), sorted(EventbriteScrapper.test(), key=lambda k: k.name.strip())))
