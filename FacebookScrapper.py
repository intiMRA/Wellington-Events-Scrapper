import json
import random

from dotenv import load_dotenv
from time import sleep
from dateutil import parser

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

import FileUtils
import ScrapperNames
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
    def parse_date(date: str, verbose: bool = True) -> List[datetime]:
        if verbose:
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
        today_string = today.strftime("%d %b")
        today = parser.parse(f"{today_string} {hour}")
        if verbose:
            print(f"hour: {hour}")
        if "Tomorrow" in date:
            target_date = today + timedelta(days=1)
            return [target_date]
        elif "Today" in date:
            return [today]
        regex = r"\d{1,2}\s\w+\d{0,4}"
        matches = re.findall(regex, date)
        if matches:
            dates = []
            for match in matches:
                try:
                    dates.append(parser.parse(match))
                except:
                    pass
            if verbose:
                print(f"date: {matches[0]} {hour}")
            return dates
        for day_of_the_week in week_days:
            matches = re.findall(fr"{day_of_the_week}", date)
            if matches:
                day = FacebookScrapper.parse_day_of_week(matches[0])
                if verbose:
                    print(f"day: {day}")
                return [parser.parse(f"{day} {hour}")]
        if verbose:
            print(f"facebook: {date}")
        return []
    @staticmethod
    def get_event(url: str, category: str, driver: webdriver, banned_file) -> Optional[EventInfo]:
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
        try:
            button = info.find_element(By.XPATH, '//div[@role="button" and text()="See more"]')
            button.click()
        except Exception as e:
            json.dump(url, banned_file, indent=2)
            banned_file.write(",\n")
            raise e
        sleep(1)

        try:
            button = info.find_element(By.XPATH, '//div[@role="button" and text()="See more"]')
            button.click()
        except:
            pass

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
        try:
            long_desc: str = info.find_element(By.XPATH, "//span[contains(., 'See less')]").text
        except Exception as e:
            json.dump(url, banned_file, indent=2)
            banned_file.write(",\n")
            raise e

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
            while len(html) < 450:
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
                    try:
                        date_string = event.text.split("\n")[0]
                        ev_dates = FacebookScrapper.parse_date(date_string, False)
                        if ev_dates[-1] < datetime.now():
                            print(f"skipping date: {date_string}")
                            continue
                    except:
                        pass
                    event_url = event.get_attribute('href')
                    regex = r'https://www.facebook.com/events/\d+'
                    event_url = re.findall(regex, event_url)[0]
                    if event_url in previous_urls:
                        continue
                    previous_urls.add(event_url)
                    event_urls.add((event_url, "Other"))
                    json.dump((event_url, "Other"), out_urls_file, indent=2)
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
            sleep(random.uniform(2, 3))
            html = driver.find_elements(By.TAG_NAME, 'a')
            print("size of html: ", len(html))
            print(len(new_event_titles))
            for event in html:
                try:
                    try:
                        date_string = event.text.split("\n")[0]
                        ev_dates = FacebookScrapper.parse_date(date_string, False)
                        if ev_dates[-1] < datetime.now():
                            print(f"skipping date: {date_string}")
                            continue
                    except:
                        pass
                    event_url = event.get_attribute('href')
                    regex = r'https://www.facebook.com/events/\d+'
                    event_url = re.findall(regex, event_url)[0]
                    if event_url in previous_urls:
                        continue
                    event_urls.add((event_url, category))
                    previous_urls.add(event_url)
                    json.dump((event_url, category), out_urls_file, indent=2)
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
        category_urls = set()
        # category_urls = FileUtils.load_from_files(ScrapperNames.FACEBOOK)[1]
        events = []
        out_file, urls_file, banned_file = FileUtils.get_files_for_scrapper(ScrapperNames.FACEBOOK)
        previous_urls = previous_urls.union(set(FileUtils.load_banned(ScrapperNames.FACEBOOK)))
        urls_file.write("[\n")
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
        sleep(random.uniform(5, 7))
        next_month_button = driver.find_element(By.XPATH, "//span[contains(., 'In the next month')]")
        next_month_button.click()
        sleep(random.uniform(2, 3))
        location_search = driver.find_element(By.XPATH, "//input[@placeholder='Location']")
        location_search.click()
        location_search.send_keys("Wellin")
        sleep(random.uniform(2, 3))
        welly = driver.find_element(By.XPATH, "//span[contains(., 'Wellington, New Zealand')]")
        welly.click()

        cat_button = driver.find_element(By.XPATH, f"//span[contains(., 'Classics')]")
        cat_button.click()
        dates.click()
        sleep(random.uniform(1, 3))

        for cat in sorted(cats):
            print("cat: ", cat)
            cat_button = driver.find_element(By.XPATH, f"//span[contains(., '{cat}')]")
            driver.execute_script("arguments[0].scrollIntoView(true);", cat_button)
            cat_button.click()
            sleep(1)
            category_urls = category_urls.union(FacebookScrapper.slow_scroll_to_bottom(driver, cat, previous_urls, urls_file))
            cat_button.click()
        driver.get(
            f"https://www.facebook.com/events/?"
            f"date_filter_option=CUSTOM_DATE_RANGE"
            f"&discover_tab=CUSTOM"
            f"&location_id=1590021457900572"
            f"&start_date={start_date_string}"
            f"&end_date={end_date_string}")
        sleep(1)

        category_urls = category_urls.union(FacebookScrapper.slow_scroll_to_bottom_other(driver, previous_urls, urls_file, scroll_increment=5000))

        driver.get(
            f"https://www.facebook.com/events/?"
            f"date_filter_option=CUSTOM_DATE_RANGE"
            f"&discover_tab=CUSTOM"
            f"&location_id=114912541853133"
            f"&start_date={start_date_string}"
            f"&end_date={end_date_string}")
        sleep(1)
        category_urls = category_urls.union(FacebookScrapper.slow_scroll_to_bottom_other(driver, previous_urls, urls_file, scroll_increment=5000))
        urls_file.write("]\n")
        num_events = len(category_urls)
        print(f"fetching: {num_events}")
        count = 1
        for part in category_urls:
            print(f"category: {part[1]} url: {part[0]}")
            try:
                event = FacebookScrapper.get_event(part[0], part[1], driver, banned_file)
                if event:
                    events.append(event)
                    json.dump(event.to_dict(), out_file, indent=2)
                    out_file.write(",\n")
                sleep(random.uniform(2, 4))
            except Exception as e:
                print(e)
                sleep(random.uniform(2, 4))
            print(f"{count} out of {num_events}")
            count += 1
            print("-" * 100)

        driver.close()
        out_file.write("]\n")
        out_file.close()
        urls_file.close()
        banned_file.close()
        return events
# events = list(map(lambda x: x.to_dict(), sorted(FacebookScrapper.fetch_events(set(), set()), key=lambda k: k.name.strip())))