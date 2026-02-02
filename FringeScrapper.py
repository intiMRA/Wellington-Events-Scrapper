import json
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By

import CurrentFestivals
import FileUtils
import ScrapperNames
from EventInfo import EventInfo
from dateutil import parser
from typing import List, Set, Optional
from time import sleep

# Wellington Fringe Festival typically runs mid-February to mid-March
FRINGE_START_MONTH = 2
FRINGE_END_MONTH = 3
FRINGE_END_DAY = 15  # Festival typically ends around March 14-15


class FringeScrapper:
    @staticmethod
    def get_event(url: str, driver: webdriver) -> Optional[EventInfo]:
        driver.get(url)
        sleep(3)
        try:
            title = driver.find_element(By.TAG_NAME, "h1").text
        except:
            return None

        try:
            image_element = driver.find_element(By.CLASS_NAME, "card-img-top")
            image_url = image_element.get_attribute("src")
        except:
            image_url = ""

        # Get venue information
        try:
            venue_elements = driver.find_elements(By.TAG_NAME, "h3")
            venue = "Wellington"
            for element in venue_elements:
                text = element.text
                if text and text.strip():
                    # Find the address after the venue name
                    try:
                        parent = element.find_element(By.XPATH, "./..")
                        venue_text = parent.text
                        if venue_text:
                            venue = venue_text.split("\n")[0]
                            # Try to find address
                            address_parts = venue_text.split("\n")
                            if len(address_parts) > 1:
                                venue = f"{address_parts[0]}, {address_parts[1]}"
                            break
                    except:
                        venue = text
                        break
        except:
            venue = "Wellington"

        # Get dates
        dates = []
        try:
            # Look for date information in the page
            page_text = driver.find_element(By.TAG_NAME, "body").text
            # Find dates pattern like "20-21 February 2026"
            import re
            date_patterns = re.findall(r'(\d{1,2}(?:-\d{1,2})?\s+\w+\s+\d{4})', page_text)
            for date_pattern in date_patterns:
                try:
                    # Handle date ranges like "20-21 February 2026"
                    if '-' in date_pattern.split()[0]:
                        day_range = date_pattern.split()[0]
                        rest = ' '.join(date_pattern.split()[1:])
                        start_day, end_day = day_range.split('-')
                        for day in range(int(start_day), int(end_day) + 1):
                            date_str = f"{day} {rest}"
                            dates.append(parser.parse(date_str))
                    else:
                        dates.append(parser.parse(date_pattern))
                except:
                    continue
        except:
            pass

        if not dates:
            # Default to festival dates if no specific dates found
            dates = [parser.parse("20 February 2026")]

        # Get description
        try:
            description_elements = driver.find_elements(By.TAG_NAME, "p")
            description = ""
            for elem in description_elements:
                text = elem.text
                if text and len(text) > 50:
                    description = text
                    break
        except:
            description = ""

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
        # Check if the festival is currently running
        now = datetime.now()
        festival_end = datetime(now.year, FRINGE_END_MONTH, FRINGE_END_DAY)

        # If we're past the festival end date, don't scrape
        if now > festival_end:
            print("Wellington Fringe Festival has ended for this year")
            return []

        # If we're before the festival starts (before February), don't scrape
        if now.month < FRINGE_START_MONTH:
            print("Wellington Fringe Festival has not started yet")
            return []

        out_file, urls_file, banned_file = FileUtils.get_files_for_scrapper(ScrapperNames.FRINGE)
        previous_urls = previous_urls.union(set(FileUtils.load_banned(ScrapperNames.FRINGE)))
        driver = webdriver.Chrome()

        # Get all event URLs from the main page
        event_urls = FringeScrapper.get_festival_urls("https://tickets.fringe.co.nz/events/", driver)
        print(f"Found {len(event_urls)} event URLs")

        # Only add to current festivals if we found events
        if event_urls:
            CurrentFestivals.CURRENT_FESTIVALS.append("WellingtonFringe")
            CurrentFestivals.CURRENT_FESTIVALS_DETAILS.append({
                "id": "WellingtonFringe",
                "name": "Wellington Fringe Festival",
                "icon": "theater",
                "url": "https://raw.githubusercontent.com/intiMRA/Wellington-Events-Scrapper/refs/heads/main/wellington-fringe.json"
            })

        out_file.write("[\n")
        events = FringeScrapper.get_events(event_urls, driver, previous_urls, out_file)
        out_file.write("]\n")

        # Also create festival file
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
