import json
import random
from dotenv import load_dotenv
from time import sleep
from dateutil import parser

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

import FileNames
from EventInfo import EventInfo
import re
from datetime import datetime, timedelta
from pathlib import Path
from dateutil.relativedelta import relativedelta
from typing import List, Optional, Set

dotenv_path = Path('venv/.env')
load_dotenv(dotenv_path=dotenv_path)


class FacebookScrapper:
    @staticmethod
    def parse_day_of_week(day_string: str) -> Optional[str]:
        """Parses a day of the week string into a datetime object representing the next occurrence of that day."""
        try:
            today = datetime.now()
            target_day = parser.parse(day_string).weekday()  # 0=Monday, 6=Sunday

            days_until_target = (target_day - today.weekday()) % 7
            next_occurrence = today + timedelta(days=days_until_target)
            return next_occurrence.strftime("%d %b")

        except:
            return None

    @staticmethod
    def parse_date(date: str) -> List[datetime]:
        print(f"date: {date}")
        week_days = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday"
        ]
        today = datetime.now()
        hour = " 1:01AM"
        if re.findall(r"\d{1,2}:\d{1,2}", date):
            hour: str = re.findall(r"\d{1,2}:\d{1,2}", date)[0]
        print(f"hour: {hour}")
        if "Tomorrow" in date:
            target_date = today + timedelta(days=1)
            return [target_date]
        elif "Today" in date:
            target_date = today
            return [target_date]
        regex = r"\d{1,2}\s\w+\d{0,4}"
        matches = re.findall(regex, date)
        if matches:
            print(f"date: {matches[0]} {hour}")
            return [parser.parse(f"{matches[0]} {hour}")]
        for day_of_the_week in week_days:
            matches = re.findall(fr"{day_of_the_week}", date)
            if matches:
                day = FacebookScrapper.parse_day_of_week(matches[0])
                print(f"day: {day}")
                return [parser.parse(f"{day} {hour}")]
        print(f"facebook: {date}")
        return []
    @staticmethod
    def get_event(url: str, category: str, driver: webdriver) -> Optional[EventInfo]:
        driver.get(url)
        sleep(random.randint(1, 3))
        info = driver.find_element(By.XPATH, "//div[@aria-label='Event permalink']")
        spans = info.find_elements(By.TAG_NAME, "span")
        texts = []
        for span in spans:
            text = span.text
            if text in texts:
                continue
            texts.append(text)
        driver.execute_script(f"window.scrollBy(0, 200);")
        sleep(random.randint(1, 3))
        button = info.find_element(By.XPATH, '//div[@role="button" and text()="See more"]')

        button.click()
        try:
            actions = ActionChains(driver)
            window_size = driver.get_window_size()
            max_x = window_size['width'] - 100
            max_y = window_size['height'] - 100

            # Move mouse randomly 10 times
            for _ in range(10):
                # Generate random coordinates within window bounds
                x = random.randint(0, max_x)
                y = random.randint(0, max_y)

                # Move to the random position
                actions.move_by_offset(x, y).perform()
                sleep(random.uniform(0.1, 0.5))
        except:
            sleep(random.uniform(1.0, 3.0))
        long_desc: str = info.find_element(By.XPATH, "//span[contains(., 'See less')]").text

        if "..." in long_desc:
            long_desc = "\n".join(long_desc.split("\n")[0:-2])
        else:
            long_desc = re.sub(r"See less", "", long_desc)
        address = info.find_element(By.XPATH, "//div[@aria-label='Location information for this event']")
        venue = address.text.split("\n")[-1]
        image_url = driver.find_element(By.XPATH, "//img[@data-imgperflogname='profileCoverPhoto']").get_attribute(
            "src")
        dates = FacebookScrapper.parse_date(texts[0])
        title = texts[1]
        print(title)
        print(venue)
        return EventInfo(name=title,
                          image=image_url,
                          venue=venue,
                          dates=dates,
                          url=url,
                          source="Facebook",
                          event_type=category,
                          description=long_desc)
    @staticmethod
    def slow_scroll_to_bottom_other(driver, previous_urls: Set[str], out_urls_file, scroll_increment=300) -> Set[tuple[str, str]]:
        event_urls: Set[tuple[str, str]] = set()
        while True:
            html = driver.find_elements(By.TAG_NAME, 'a')
            old_length = len(html)
            while len(html) < 400:
                driver.execute_script(f"window.scrollBy(0, {scroll_increment});")
                sleep(2)
                html = driver.find_elements(By.TAG_NAME, 'a')
                if old_length == len(html):
                    break
                else:
                    old_length = len(html)

            print(f"facebook finished finding html {len(html)}")
            for event in html:
                try:
                    event_url = event.get_attribute('href')
                    regex = r'https://www.facebook.com/events/\d+'
                    event_url = re.findall(regex, event_url)[0]
                    if event_url in previous_urls:
                        continue
                    event_urls.add((event_url, "Other"))
                    json.dump((event_url, "Other"), out_urls_file)
                    out_urls_file.write(",\n")
                except:
                    continue
            return event_urls

    @staticmethod
    def slow_scroll_to_bottom(driver: webdriver, category: str, previous_urls: Set[str], out_urls_file, scroll_increment=300) -> Set[tuple[str, str]]:
        old_event_titles = {}
        new_event_titles = {}
        event_urls: Set[tuple[str, str]] = set()
        while True:
            driver.execute_script(f"window.scrollBy(0, {scroll_increment});")
            sleep(2)
            html = driver.find_elements(By.TAG_NAME, 'a')
            print("size of html: ", len(html))
            print(len(new_event_titles))
            for event in html:
                try:
                    event_url = event.get_attribute('href')
                    regex = r'https://www.facebook.com/events/\d+'
                    event_url = re.findall(regex, event_url)[0]
                    event_urls.add((event_url, category))
                    previous_urls.add(event_url)
                    json.dump((event_url, category), out_urls_file)
                    out_urls_file.write(",\n")
                except:
                    continue

            if (len(new_event_titles) ==0
                    or old_event_titles.keys() == new_event_titles.keys()
                    or len(old_event_titles.keys()) >= 200):
                return event_urls
            old_event_titles = new_event_titles.copy()

    @staticmethod
    def fetch_events(previous_urls: Set[str], previous_titles: Optional[Set[str]]) -> List[EventInfo]:
        # Path to your Chrome profile directory
        profile_path = "~/ChromeTestProfile"  # Replace with your actual path
        # Set Chrome options
        options = Options()
        options.add_argument(f"user-data-dir={profile_path}")

        # Initialize the ChromeDriver
        driver = webdriver.Chrome(options=options)
        start_date = datetime.now()
        start_date_string = start_date.strftime("%Y-%m-%d")
        start_date_string += "T05%3A00%3A00.000Z"
        end_date = start_date + relativedelta(days=30)
        end_date_string = end_date.strftime("%Y-%m-%d")
        end_date_string += "T05%3A00%3A00.000Z"
        captured_urls = previous_urls
        category_urls = set()
        # with open(FileNames.FACEBOOK_URLS, mode="r") as f:
        #     category_urls = json.loads(f.read())
        events = []
        out_file = open(FileNames.FACEBOOK_EVENTS, mode="w")
        out_urls_file = open(FileNames.FACEBOOK_URLS, mode="w")
        out_urls_file.write("[\n")
        out_file.write("[\n")
        driver.get(
            f"https://www.facebook.com/events/?"
            f"date_filter_option=CUSTOM_DATE_RANGE"
            f"&discover_tab=CUSTOM"
            f"&location_id=114912541853133"
            f"&start_date={start_date_string}"
            f"&end_date={end_date_string}")
        sleep(2)
        element = driver.find_element(By.XPATH, "//span[contains(., 'Classics')]")
        element.click()
        sleep(3)
        buttons = set(driver.find_elements(By.XPATH, "//*[@role='checkbox']"))
        cats = []
        for button in buttons:
            if button.text:
                cats.append(button.text)
        dates = driver.find_element(By.XPATH, "//span[contains(., 'Dates')]")
        dates.click()
        sleep(5)
        next_month_button = driver.find_element(By.XPATH, "//span[contains(., 'In the next month')]")
        next_month_button.click()
        sleep(2)
        location_search = driver.find_element(By.XPATH, "//input[@placeholder='Location']")
        location_search.click()
        location_search.send_keys("Wellin")
        sleep(2)
        welly = driver.find_element(By.XPATH, "//span[contains(., 'Wellington, New Zealand')]")
        welly.click()

        cat_button = driver.find_element(By.XPATH, f"//span[contains(., 'Classics')]")
        cat_button.click()
        dates.click()
        sleep(1)

        for cat in sorted(cats):
            print("cat: ", cat)
            cat_button = driver.find_element(By.XPATH, f"//span[contains(., '{cat}')]")
            driver.execute_script("arguments[0].scrollIntoView(true);", cat_button)
            cat_button.click()
            sleep(1)
            category_urls = category_urls.union(FacebookScrapper.slow_scroll_to_bottom(driver, cat, captured_urls, out_urls_file))
            cat_button.click()
        driver.get(
            f"https://www.facebook.com/events/?"
            f"date_filter_option=CUSTOM_DATE_RANGE"
            f"&discover_tab=CUSTOM"
            f"&location_id=1590021457900572"
            f"&start_date={start_date_string}"
            f"&end_date={end_date_string}")
        sleep(1)

        category_urls = category_urls.union(FacebookScrapper.slow_scroll_to_bottom_other(driver, captured_urls, out_urls_file, scroll_increment=5000))

        driver.get(
            f"https://www.facebook.com/events/?"
            f"date_filter_option=CUSTOM_DATE_RANGE"
            f"&discover_tab=CUSTOM"
            f"&location_id=114912541853133"
            f"&start_date={start_date_string}"
            f"&end_date={end_date_string}")
        sleep(1)
        category_urls = category_urls.union(FacebookScrapper.slow_scroll_to_bottom_other(driver, captured_urls, out_urls_file, scroll_increment=5000))
        out_urls_file.write("]\n")
        for part in category_urls:
            print(f"category: {part[1]} url: {part[0]}")
            try:
                event = FacebookScrapper.get_event(part[0], part[1], driver)
                if event:
                    events.append(event)
                    json.dump(event.to_dict(), out_file)
                    out_file.write(",\n")
                sleep(random.uniform(2, 4))
            except Exception as e:
                print(e)
                sleep(random.uniform(2, 4))
            print("-" * 100)

        driver.close()
        out_file.write("]\n")
        out_file.close()
        out_urls_file.close()
        return events
# events = list(map(lambda x: x.to_dict(), sorted(FacebookScrapper.fetch_events(), key=lambda k: k.name.strip())))