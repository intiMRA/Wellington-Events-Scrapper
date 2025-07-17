from time import sleep
from selenium import webdriver
from selenium.webdriver.common.by import By

import ScrapperNames
from EventInfo import EventInfo
import re
from datetime import datetime, timedelta
from DateFormatting import DateFormatting
from dateutil import parser
from dateutil.relativedelta import relativedelta
from typing import List, Set, Optional
import json


class EventFinderScrapper:
    @staticmethod
    def get_time_from_string(time_string: str) -> Optional[datetime]:
        # Get the current date
        today = datetime.now()

        # Check if the string mentions "Tomorrow" or "Today"
        if "Tomorrow" in time_string:
            target_date = today + timedelta(days=1)  # Add one day for tomorrow
        elif "Today" in time_string:
            target_date = today  # Use today's date
        else:
            return None  # If the string doesn't contain "Today" or "Tomorrow"

        # Extract the time (e.g., 6:30pm)
        time_match = re.search(r'(\d{1,2}):(\d{2})(am|pm)', time_string, re.IGNORECASE)

        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2))
            am_pm = time_match.group(3).lower()

            # Convert to 24-hour format if in PM
            if am_pm == "pm" and hour != 12:
                hour += 12
            if am_pm == "am" and hour == 12:
                hour = 0

            # Combine the target date with the time
            target_time = target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
            return target_time
        return None

    @staticmethod
    def get_event(url: str, category: Optional[str], driver: webdriver) -> Optional[EventInfo]:
        try:
            driver.find_element(By.XPATH, "//*[contains(., 'HTTP')]")
            sleep(60 * 20)
            driver.get(url)
        except:
            pass

        driver.get(url)
        title: str = driver.find_element(By.CLASS_NAME, "value-title").text
        venue: str = driver.find_element(By.CLASS_NAME, "venue").text
        dates = EventFinderScrapper.get_all_event_dates(url, driver)
        description: str = driver.find_element(By.CLASS_NAME, "description").text
        image_url = ""
        try:
            image_url: str = driver.find_element(By.CLASS_NAME, "photo").get_attribute("src")
        except:
            print("no image found")
        return EventInfo(
            name=title,
            dates=dates,
            image=image_url,
            url=url,
            venue=venue,
            source=ScrapperNames.EVENT_FINDER,
            event_type=category if category else "Other",
            description=description)

    @staticmethod
    def get_all_event_dates(url: str, driver) -> List[datetime]:
        date_objects: List[datetime] = []
        try:
            driver.find_element(By.XPATH, "//*[contains(., 'HTTP')]")
            sleep(2)
            driver.get(url)
        except:
            pass
        try:
            all_dates_button = driver.find_element(By.CLASS_NAME, "show-more")
            all_dates_button.click()
        except:
            pass
        i = 0
        dates = []
        while i < 2:
            try:
                date_table = driver.find_element(By.CLASS_NAME, "sessions-info")
                dates = date_table.find_elements(By.TAG_NAME, "time")
                break
            except:
                i += 1
                sleep(1)
        for date in dates:
            date_string = date.get_attribute("datetime")
            try:
                # datetime 2024-08-01, 09:00–13:00
                full_string = date_string
                date_string = date_string.split(",")[0]
                if len(date_string.split("–")) > 1:
                    start, last = date_string.split("–")
                    hour = full_string.split(",")[-1].split("–")[0]
                    start += " " + hour
                    last += " " + hour
                    print(f"start: {start} end: {last}")
                    start_date_obj = parser.parse(start)
                    end_date_obj = parser.parse(last)

                    start_date_obj = DateFormatting.replace_year(start_date_obj)

                    end_date_obj = DateFormatting.replace_year(end_date_obj)
                    date_objects = list(DateFormatting.create_range(start_date_obj, end_date_obj))
                else:
                    date_string = date_string + " " + full_string.split(",")[-1].split("–")[0]
                    print(f"date: {date_string}")
                    date_obj = parser.parse(date_string)
                    date_obj = DateFormatting.replace_year(date_obj)
                    date_objects.append(date_obj)
            except Exception as e:
                print(f"error: {e}")
        return date_objects

    @staticmethod
    def get_events(url: str, previous_urls: Set[str], urls_file, out_file) -> (List[EventInfo], Set[str]):
        events: List[EventInfo] = []
        driver = webdriver.Chrome()
        driver.get(url + f'/page/{2}')
        last_page = 1
        try:
            pagination = driver.find_element(By.CLASS_NAME, 'lead')
            last_page = int(re.sub('\W+', ' ', pagination.text).strip().split("of")[-1])
        except:
            print("error: ", url)
            pass
        current_page = 1
        driver.close()
        driver = webdriver.Chrome()
        event_urls: Set[tuple[str, Optional[str]]] = set()
        while current_page <= last_page:
            page_url = url + f'/page/{current_page}'
            driver.get(page_url)
            i = 0
            html = []
            while i < 10:
                try:
                    html = driver.find_element(By.CLASS_NAME, 'listings-events').find_elements(By.CLASS_NAME, 'card')
                    break
                except:
                    i += 1
                    sleep(1)
            for event in html:
                title_element = event.find_element(By.CLASS_NAME, "card-title").find_element(By.TAG_NAME, "a")
                try:
                    event_url = title_element.get_attribute("href")
                    if event_url in previous_urls:
                        continue
                    previous_urls.add(event_url)
                    category: Optional[str] = None
                    try:
                        category = event.find_element(By.CLASS_NAME, 'category').text
                    except:
                        pass
                    event_urls.add((event_url, category if category else "Other"))

                except:
                    print(f"invalid event")
                    continue
            current_page += 1

        json.dump(event_urls, urls_file, indent=2)
        for parts in event_urls:
            url = parts[0]
            category = parts[1]
            print(f"category: {category} url: {url}")
            try:
                event = EventFinderScrapper.get_event(url, category, driver)
                if event:
                    events.append(event)
                    out_file.write(event.to_dict())
                    out_file.write(",\n")
            except Exception as e:
                print(e)
            print("-" * 100)
        try:
            driver.close()
        except:
            pass
        return events, previous_urls

    @staticmethod
    def fetch_events(previous_urls: Set[str]) -> List[EventInfo]:
        out_file = open("eventFinder.json", mode="w")
        urls_file = open("eventFinderUrls.json", mode="w")
        start_date = datetime.now()
        end_date = start_date + relativedelta(days=30)
        print("getting wellington region")
        print("-" * 100)
        events_url = f"https://www.eventfinda.co.nz/whatson/events/wellington-region/date/to-month/{end_date.month}/to-day/{end_date.day}"
        events, previous_urls = EventFinderScrapper.get_events(events_url, previous_urls, urls_file, out_file)

        print("getting wellington")
        print("-" * 100)
        events_url = f"https://www.eventfinda.co.nz/whatson/events/wellington/date/to-month/{end_date.month}/to-day/{end_date.day}"
        wellington_specific, _ = EventFinderScrapper.get_events(events_url, previous_urls, urls_file, out_file)
        events += wellington_specific
        out_file.write("]\n")
        out_file.close()
        urls_file.close()
        return events

# events = list(map(lambda x: x.to_dict(), sorted(EventFinderScrapper.fetch_events(set()), key=lambda k: k.name.strip())))
