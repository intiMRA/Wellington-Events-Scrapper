import json
import random
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

import CurrentFestivals
from DateFormatting import DateFormatting
import FileUtils
import ScrapperNames
from EventInfo import EventInfo
from dateutil import parser
from typing import List, Set, Optional
from time import sleep

class FringeScrapper:
    @staticmethod
    def get_event(url: str, driver: webdriver) -> Optional[EventInfo]:
        driver.get(url)
        sleep(random.uniform(1,3))
        title = driver.find_element(By.XPATH, "//h2[contains(@class, 'primary-color')]").text

        image_element = driver.find_element(By.XPATH, "//img[contains(@class, 'event-image-square')]")
        image_url = image_element.get_attribute("src")

        venue = driver.find_element(By.XPATH, "//div[contains(@class, 'addres-pin')]").text
        schedule: WebElement = driver.find_element(By.CLASS_NAME, "schedule")
        schedule_elements = schedule.find_elements(By.TAG_NAME, "li")
        dates = schedule_elements[2].text
        date_text = dates.split(" ")
        days = date_text[0].split("-")
        month = date_text[1]
        start_day, end_day = days
        start_date, end_date = parser.parse(start_day + " " + month), parser.parse(end_day + " " + month)
        dates = list(DateFormatting.create_range(start_date, end_date))
        content: WebElement = driver.find_element(By.XPATH, "//div[contains(@class, 'content')]")
        paragraphs = content.find_elements(By.TAG_NAME, "p")
        description = ""
        for paragraph in paragraphs:
            description += paragraph.text + "\n"
        return EventInfo(
            name=title,
            dates=dates,
            image=image_url,
            url=url,
            venue=venue,
            source=ScrapperNames.FRINGE,
            event_type="Arts & Theatre",
            description=description
        )

    @staticmethod
    def get_festival_urls(url: str, driver: webdriver) -> Set[str]:
        driver.get(url)
        sleep(3)

        # Scroll to load all events
        height = driver.execute_script("return document.body.scrollHeight")
        scrolled_amount = 0
        while scrolled_amount < height:
            driver.execute_script(f"window.scrollBy(0, {1200});")
            scrolled_amount += 1200
            sleep(0.5)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height > height:
                height = new_height

        # Find all event links
        event_urls = set()
        try:
            links = driver.find_elements(By.TAG_NAME, "a")
            for link in links:
                href = link.get_attribute("href")
                if href and "/event/" in href:
                    event_urls.add(href)
        except:
            pass

        return event_urls

    @staticmethod
    def get_events(event_urls: Set[str], driver: webdriver, previous_urls: Set[str], out_file) -> List[EventInfo]:
        events = []
        for event_url in event_urls:
            if event_url in previous_urls:
                continue
            print(f"url: {event_url}")
            try:
                event = FringeScrapper.get_event(event_url, driver)
                if event:
                    print(f"Title: {event.name}")
                    print(f"Dates: {event.dates}")
                    print(f"Venue: {event.venue}")
                    print(f"Image: {event.image}")
                    print(f"Description: {event.description[:100]}..." if len(event.description) > 100 else f"Description: {event.description}")
                    print(f"Event Type: {event.eventType}")
                    events.append(event)
                    json.dump(event.to_dict(), out_file, indent=2)
                    out_file.write(",\n")
            except Exception as e:
                if "No dates found for" in str(e):
                    print("-" * 100)
                    print(e)
                else:
                    print("-" * 100)
                    print(f"Error fetching {event_url}: {e}")
            print("-" * 100)
        return events

    @staticmethod
    def fetch_events(previous_urls: Set[str], previous_titles: Optional[Set[str]]) -> List[EventInfo]:

        out_file, urls_file, banned_file = FileUtils.get_files_for_scrapper(ScrapperNames.FRINGE)
        previous_urls = previous_urls.union(set(FileUtils.load_banned(ScrapperNames.FRINGE)))
        driver = webdriver.Chrome()

        # Get all event URLs from the main page
        event_urls = FringeScrapper.get_festival_urls("https://tickets.fringe.co.nz/events/", driver)
        print(f"Found {len(event_urls)} event URLs")

        # Only add to current festivals if we found events

        out_file.write("[\n")
        events = FringeScrapper.get_events(event_urls, driver, previous_urls, out_file)
        out_file.write("]\n")

        if events:
            CurrentFestivals.CURRENT_FESTIVALS.append("WellingtonFringe")
            CurrentFestivals.CURRENT_FESTIVALS_DETAILS.append({
                "id": "WellingtonFringe",
                "name": "Wellington Fringe Festival",
                "icon": "theater",
                "url": "https://raw.githubusercontent.com/intiMRA/Wellington-Events-Scrapper/refs/heads/main/wellington-fringe.json"
            })

        festival_file = open("wellington-fringe.json", mode="w")
        events_dicts = [event.to_dict() for event in events]
        json.dump({"events": sorted(events_dicts, key=lambda evt: evt["name"])}, festival_file, indent=2)
        festival_file.close()

        driver.close()
        out_file.close()
        urls_file.close()
        banned_file.close()
        return events

# events = list(map(lambda x: x.to_dict(), sorted(FringeScrapper.fetch_events(set(), set()), key=lambda k: k.name.strip())))
