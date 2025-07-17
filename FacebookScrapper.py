from dotenv import load_dotenv
from time import sleep
from dateutil import parser

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

import ScrapperNames
from DateFormatting import DateFormatting
from EventInfo import EventInfo
import re
from datetime import datetime, timedelta
from pathlib import Path
from dateutil.relativedelta import relativedelta
from typing import List, Optional, Tuple, Set

dotenv_path = Path('venv/.env')
load_dotenv(dotenv_path=dotenv_path)


class FacebookScrapper:
    @staticmethod
    def parse_day_of_week(day_string: str) -> Optional[datetime]:
        """Parses a day of the week string into a datetime object representing the next occurrence of that day."""
        try:
            today = datetime.now()
            target_day = parser.parse(day_string).weekday()  # 0=Monday, 6=Sunday

            days_until_target = (target_day - today.weekday()) % 7
            next_occurrence = today + timedelta(days=days_until_target)
            return next_occurrence.replace(hour=0, minute=0, second=0, microsecond=0)

        except ValueError:
            return None

    @staticmethod
    def parse_date(date: str) -> Optional[List[datetime]]:
        try:
            today = datetime.now()
            hour = " 10:00"
            if re.findall(r"at\s\d+:\d+", date):
                hour = " " + date.split("at")[-1].split(" ")[1]
            if "Tomorrow" in date:
                target_date = today + timedelta(days=1)
                return [target_date]
            elif "Today" in date:
                target_date = today
                return [target_date]
            elif "This" in date:
                day = date.split(" ")[1]
                date_object = FacebookScrapper.parse_day_of_week(day)
                return [date_object]
            elif re.findall(r"and \d{1,2} more", date):
                if "-" in date:
                    parts = date.split(",")[1].split("-")
                    first_part, second_part = parts[0], parts[1]
                    first_part = first_part.strip() + hour
                    start_date = parser.parse(first_part)
                    return [start_date]
                else:
                    parts = date.split(",")[1]
                    first_part = re.findall(r"\d{1,2}\s\w{3}", parts)[0]
                    first_part = first_part.strip() + hour
                    start_date = parser.parse(first_part)
                    return [start_date]
            elif "-" in date and len(date.split("-")[-1]) > 3:
                parts = date.split(",")[1].split("-")
                first_part, second_part = parts[0], parts[1]
                first_part = first_part.strip() + hour
                second_part = second_part.strip() + hour
                start_date = parser.parse(first_part)
                end_date = parser.parse(second_part)
                dates = list(DateFormatting.create_range(start_date, end_date))
                return dates
            elif "," in date:
                date_string = " ".join(date.split(",")[-1].strip().split(" ")[:2]) + hour
                date = parser.parse(date_string)
                return [date]
            else:
                print(f"facebook: {date}")
                return None
        except Exception as e:
            print("facebook date: ", date, " error: ", e)
            return None

    @staticmethod
    def slow_scroll_to_bottom_other(driver, found_titles: Set[str], scroll_increment=300) -> (List[EventInfo], Set[str]):
        events_info: List[EventInfo] = []
        titles = set()
        while True:
            html = driver.find_elements(By.TAG_NAME, 'a')
            old_length = len(html)
            while len(html) < 700:
                driver.execute_script(f"window.scrollBy(0, {scroll_increment});")
                sleep(2)
                html = driver.find_elements(By.TAG_NAME, 'a')
                if old_length == len(html):
                    break
                else:
                    old_length = len(html)

            print(f"facebook finished finding html {len(html)}")
            for event in html:
                info = event.find_elements(By.TAG_NAME, "span")
                filtered = []
                for i in info:
                    i = i.text.strip()
                    if not i or i in filtered:
                        continue
                    filtered.append(i)
                try:
                    if len(filtered) < 3:
                        continue
                    date = filtered[0]
                    if date == "Happening now":
                        continue
                    title = filtered[1]
                    if title in found_titles or title in titles:
                        continue
                    titles.add(title)
                    dates = FacebookScrapper.parse_date(date)
                    venue = filtered[2]
                    event_url = event.get_attribute('href')
                    regex = r'https://www.facebook.com/events/\d+'
                    event_url = re.findall(regex, event_url)[0]
                    image_url = event.find_element(By.TAG_NAME, 'img').get_attribute('src')

                    events_info.append(EventInfo(name=title,
                                                dates=dates,
                                                image=image_url,
                                                url=event_url,
                                                venue=venue,
                                                source="Facebook",
                                                event_type="Other"))
                except Exception as e:
                    if "No dates found for" in str(e):
                        print("facebook error: ", e)
                        print("facebook error: ", filtered)
                        continue
                    else:
                        raise e
            return events_info, titles.union(found_titles)

    @staticmethod
    def slow_scroll_to_bottom(driver, category: str, found_titles: Set[str], scroll_increment=300) -> Tuple[List[EventInfo], Set[str]]:
        old_event_titles = {}
        new_event_titles = {}
        titles = set()
        while True:
            driver.execute_script(f"window.scrollBy(0, {scroll_increment});")
            sleep(2)
            html = driver.find_elements(By.TAG_NAME, 'a')
            print("size of html: ", len(html))
            print(len(new_event_titles))
            for event in html:
                info = event.find_elements(By.TAG_NAME, "span")
                filtered = []
                for i in info:
                    i = i.text.strip()
                    if not i or i in filtered:
                        continue
                    filtered.append(i)
                try:
                    if len(filtered) < 3:
                        continue
                    date = filtered[0]
                    if date == "Happening now":
                        continue
                    title = filtered[1]
                    if title in new_event_titles.keys() or title in found_titles or title in titles:
                        continue
                    titles.add(title)
                    dates = FacebookScrapper.parse_date(date)
                    venue = filtered[2]
                    event_url = event.get_attribute('href')
                    regex = r'https://www.facebook.com/events/\d+'
                    event_url = re.findall(regex, event_url)[0]
                    image_url = event.find_element(By.TAG_NAME, 'img').get_attribute('src')

                    new_event_titles[title] = EventInfo(name=title,
                                                      dates=dates,
                                                      image=image_url,
                                                      url=event_url,
                                                      venue=venue,
                                                      source=ScrapperNames.FACEBOOK,
                                                      event_type=category)
                except Exception as e:
                    if "No dates found for" in str(e):
                        print("facebook error: ", e)
                        print("facebook error: ", filtered)
                        continue
                    else:
                        raise e
            if (len(new_event_titles) ==0
                    or old_event_titles.keys() == new_event_titles.keys()
                    or len(old_event_titles.keys()) >= 200):
                return list(new_event_titles.values()), titles.union(found_titles)
            old_event_titles = new_event_titles.copy()

    @staticmethod
    def fetch_events() -> List[EventInfo]:
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
        events = []
        cat_button = driver.find_element(By.XPATH, f"//span[contains(., 'Classics')]")
        cat_button.click()
        dates.click()
        sleep(1)
        titles = set()
        for cat in sorted(cats):
            print("cat: ", cat)
            cat_button = driver.find_element(By.XPATH, f"//span[contains(., '{cat}')]")
            driver.execute_script("arguments[0].scrollIntoView(true);", cat_button)
            cat_button.click()
            sleep(1)
            t = FacebookScrapper.slow_scroll_to_bottom(driver, cat, titles)
            events += list(t[0])
            titles = t[1]
            cat_button.click()
        # wellington region 1590021457900572
        # wellington city 114912541853133
        driver.get(
            f"https://www.facebook.com/events/?"
            f"date_filter_option=CUSTOM_DATE_RANGE"
            f"&discover_tab=CUSTOM"
            f"&location_id=1590021457900572"
            f"&start_date={start_date_string}"
            f"&end_date={end_date_string}")
        sleep(1)

        t = FacebookScrapper.slow_scroll_to_bottom_other(driver, titles, scroll_increment=5000)
        events += t[0]
        titles = t[1]

        driver.get(
            f"https://www.facebook.com/events/?"
            f"date_filter_option=CUSTOM_DATE_RANGE"
            f"&discover_tab=CUSTOM"
            f"&location_id=114912541853133"
            f"&start_date={start_date_string}"
            f"&end_date={end_date_string}")
        sleep(1)
        t = FacebookScrapper.slow_scroll_to_bottom_other(driver, titles, scroll_increment=5000)
        welling_ton_specific = t[0]
        events += welling_ton_specific
        driver.close()
        return events
# events = list(map(lambda x: x.to_dict(), sorted(FacebookScrapper.fetch_events(), key=lambda k: k.name.strip())))