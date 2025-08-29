import random
from time import sleep
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
import FileUtils
import ScrapperNames
from EventInfo import EventInfo
from dateutil import parser
from typing import List, Set, Optional, Tuple
import json


class AllEventsInScrapper:
    @staticmethod
    def get_event(url: str, category: Optional[str], driver: webdriver) -> Optional[EventInfo]:
        driver.get(url)
        title =  driver.find_element(By.CLASS_NAME, "eps-heading-1").text
        image: WebElement = driver.find_element(By.CLASS_NAME, "event-banner")
        image_url = image.get_attribute("src")
        venue_texts = [event_text.text for event_text in driver.find_elements(By.XPATH, "//p[contains(@class, 'event-location')]")]
        venue = ",".join(venue_texts)
        print(f"venue: {venue}")
        date_strings = driver.find_element(By.XPATH, "//p[contains(@class, 'event-time-label')]").text.split(" - ")
        dates = []
        for date_string in date_strings:
            date_string = " ".join(date_string.split(",")[1:])
            date_string = date_string.split(" (")[0]
            dates.append(parser.parse(date_string))
        description = driver.find_element(By.XPATH, "//div[contains(@class, 'event-description')]").text
        print(category)
        return EventInfo(name=title,
                         dates=dates,
                         image=image_url,
                         url=url,
                         venue=venue,
                         source=ScrapperNames.ROXY,
                         event_type=category,
                         description=description)

    @staticmethod
    def get_urls_for_category(category_url, driver: webdriver, previous_urls: Set[str], category_name: str, urls_file) -> Set[Tuple[str, str]]:
        event_urls = set()
        driver.get(category_url)
        sleep(random.uniform(2, 3))
        try:
            driver.find_element(By.CLASS_NAME, "cat-not-found-section")
            return set()
        except:
            pass
        container: WebElement = driver.find_element(By.XPATH, "//div[contains(@class, 'eventlist-container')]")
        height = driver.execute_script("return arguments[0].scrollHeight", container)
        scrolled_amount = 0
        more_count = 0
        height = max(height, 800)
        while True:
            print(height)
            if scrolled_amount > height or more_count > 1:
                print("finished scroll")
                break
            driver.execute_script(f"window.scrollBy(0, {400});")
            scrolled_amount += 400
            sleep(1)
            try:
                container: WebElement = driver.find_element(By.XPATH, "//div[contains(@class, 'eventlist-container')]")
                height = driver.execute_script("return arguments[0].scrollHeight", container)
            except:
                pass
            try:
                view_more_button = container.find_element(By.ID, "show_more_events")
                view_more_button.click()
                container: WebElement = driver.find_element(By.XPATH, "//div[contains(@class, 'eventlist-container')]")
                height = driver.execute_script("return arguments[0].scrollHeight", container)
                sleep(2)
                more_count += 1
                print("loaded more")
            except:
                pass
        sleep(2)
        container: WebElement = driver.find_element(By.XPATH, "//div[contains(@class, 'eventlist-container')]")
        events = container.find_elements(By.XPATH, "//li[contains(@class, 'link')]")
        print(f"event count: {len(events)}")
        for event in events:
            event_url = event.get_attribute("data-link")
            if event_url in previous_urls:
                continue
            previous_urls.add(event_url)
            event_tuple = (category_name, event_url)
            event_urls.add(event_tuple)
            json.dump(event_tuple, urls_file)
            urls_file.write(",\n")
        return event_urls
    @staticmethod
    def get_urls(city_url, previous_urls: Set[str], categories: Set[Tuple[str, str]], urls_file) -> Set[Tuple[str, str]]:
        event_urls = set()
        cat_count = len(categories)
        current_cat = 1
        for category in sorted(categories):
            driver = webdriver.Chrome()
            category_name = category[0]
            category_url = category[1]
            print(f"fetching: {category_name} for {city_url} {current_cat} of {cat_count}")
            current_cat += 1
            event_urls = event_urls.union(AllEventsInScrapper.get_urls_for_category(category_url, driver, previous_urls, category_name, urls_file))
            driver.close()
        return event_urls

    @staticmethod
    def get_categories(url: str, driver: webdriver) -> Set[Tuple[str, str]]:
        categories = set()
        driver.get(url)
        sleep(1)
        show_categories_button = driver.find_element(By.CLASS_NAME, "remaining-cat-count")
        show_categories_button.click()
        sleep(1)
        category_items: List[WebElement] = driver.find_elements(By.XPATH, "//a[contains(@class, 'cat-item')]")
        for category_item in category_items:
            category_name = category_item.text
            category_url = category_item.get_attribute("href").split("?")[0]
            categories.add((category_name, category_url))
        return categories
    @staticmethod
    def fetch_events(previous_urls: Set[str], previous_titles: Optional[Set[str]]) -> List[EventInfo]:
        fetch_urls = False
        event_urls = set()
        if not fetch_urls:
            event_urls = FileUtils.load_from_files(ScrapperNames.ALL_EVENTS_IN)[1]
        out_file, urls_file, banned_file = FileUtils.get_files_for_scrapper(ScrapperNames.ALL_EVENTS_IN)
        previous_urls = previous_urls.union(set(FileUtils.load_banned(ScrapperNames.ALL_EVENTS_IN)))
        city_urls = [
            "https://allevents.in/wellington",
            "https://allevents.in/lower-hutt",
            "https://allevents.in/upper-hutt",
            "https://allevents.in/porirua",
            "https://allevents.in/waikanae",
            "https://allevents.in/paraparaumu",
        ]
        driver = webdriver.Chrome()
        if fetch_urls:
            urls_file.write("[\n")
            for city_url in city_urls:
                categories = AllEventsInScrapper.get_categories(city_url, driver)
                event_urls = event_urls.union(AllEventsInScrapper.get_urls(city_url, previous_urls, categories, urls_file))
            urls_file.write("]\n")
        else:
            json.dump(list(event_urls), urls_file, indent=2)
        print("Done fetching urls")

        out_file.write("[\n")
        events = []
        for event_urlParts in event_urls:
            category_name = event_urlParts[0]
            event_url = event_urlParts[1]
            print(f"category: {category_name} url: {event_url}")
            try:
                event = AllEventsInScrapper.get_event(event_url, category_name, driver)
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

        driver.close()
        out_file.close()
        banned_file.close()
        urls_file.close()
        return []

events = list(map(lambda x: x.to_dict(), sorted(AllEventsInScrapper.fetch_events(set(), set()), key=lambda k: k.name.strip())))
