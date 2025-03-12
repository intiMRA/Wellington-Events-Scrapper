from dotenv import load_dotenv
import time
from time import sleep
import json
from dateutil import parser
import pandas

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup as bs
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

from DateFormatting import DateFormatting
from EventInfo import EventInfo
import re
from datetime import datetime, timedelta
import os
from pathlib import Path

dotenv_path = Path('venv/.env')
load_dotenv(dotenv_path=dotenv_path)


class FacebookScrapper:
    @staticmethod
    def parse_day_of_week(day_string: str) -> datetime:
        """Parses a day of the week string into a datetime object representing the next occurrence of that day."""
        try:
            today = datetime.now()
            target_day = parser.parse(day_string).weekday()  # 0=Monday, 6=Sunday

            days_until_target = (target_day - today.weekday()) % 7
            next_occurrence = today + timedelta(days=days_until_target)
            return next_occurrence.replace(hour=0, minute=0, second=0, microsecond=0)

        except ValueError:
            return None  # Or raise a more specific exception

    @staticmethod
    def parseDate(date: str) -> ([str], str):
        try:
            today = datetime.now()

            # Check if the string mentions "Tomorrow" or "Today"
            if "Tomorrow" in date:
                target_date = today + timedelta(days=1)
                return [DateFormatting.formatDateStamp(target_date)], DateFormatting.formatDisplayDate(target_date)
            elif "Today" in date:
                target_date = today
                return [DateFormatting.formatDateStamp(target_date)], DateFormatting.formatDisplayDate(target_date)
            elif "This" in date:
                day = date.split(" ")[1]
                date_object = FacebookScrapper.parse_day_of_week(day)
                return [DateFormatting.formatDateStamp(date_object)], DateFormatting.formatDisplayDate(date_object)
            elif "-" in date:
                parts = date.split(",")[1].split("-")
                firstPart, secondPart = parts[0], parts[1]
                firstPart = firstPart.strip()
                secondPart = secondPart.strip()
                startDate = parser.parse(firstPart)
                endDate = parser.parse(secondPart)
                range = pandas.date_range(startDate, endDate - timedelta(days=1))
                dateStamps = []
                for date in range:
                    stamp = DateFormatting.formatDateStamp(date)
                    if stamp in dateStamps:
                        continue
                    dateStamps.append(stamp)
                return dateStamps, DateFormatting.formatDisplayDate(startDate)
            elif "," in date:
                dateString = " ".join(date.split(",")[1:2])
                date = parser.parse(dateString)
                return [DateFormatting.formatDateStamp(date)], DateFormatting.formatDisplayDate(date)
            else:
                print(date)
                return None
        except Exception as e:
            print("date: ", date, " error: ", e)
            return None

    @staticmethod
    def slow_scroll_to_bottom(driver, scroll_increment=300) -> [EventInfo]:
        oldEventTitles = {}
        newEventTitles = {}
        while True:
            driver.execute_script(f"window.scrollBy(0, {scroll_increment});")
            driver.implicitly_wait(2)
            html = driver.find_elements(By.TAG_NAME, 'a')
            print("size of html: ", len(html))
            for event in html:
                try:
                    info = event.find_elements(By.TAG_NAME, "span")
                    filtered = []
                    for i in info:
                        i = i.text.strip()
                        if not i or i in filtered:
                            continue
                        filtered.append(i)

                    date = filtered[0]
                    if date == "Happening now":
                        continue
                    title = filtered[1]
                    if title in newEventTitles.keys():
                        continue
                    dates, displayDate = FacebookScrapper.parseDate(date)
                    venue = filtered[2]
                    eventUrl = event.get_attribute('href')
                    regex = r'https://www.facebook.com/events/\d+'
                    eventUrl = re.findall(regex, eventUrl)[0]
                    imageUrl = event.find_element(By.TAG_NAME, 'img').get_attribute('src')

                    newEventTitles[title] = EventInfo(name=title,
                                                      dates=dates,
                                                      displayDate=displayDate,
                                                      image=imageUrl,
                                                      url=eventUrl,
                                                      venue=venue,
                                                      source="facebook",
                                                      eventType="Other")
                except Exception as e:
                    if len(event.text) > 50:
                        print("error: ", e)
                    continue
            if oldEventTitles.keys() == newEventTitles.keys():
                driver.close()
                return newEventTitles.values()
            oldEventTitles = newEventTitles.copy()
        return list(events.values())

    @staticmethod
    def fetch_events() -> [EventInfo]:
        # Path to your Chrome profile directory
        profile_path = "/Users/ialbuquerque/ChromeTestProfile"  # Replace with your actual path
        print(profile_path)
        # Set Chrome options
        options = Options()
        options.add_argument(f"user-data-dir={profile_path}")

        # Initialize the ChromeDriver
        driver = webdriver.Chrome(options=options)
        driver.get(
            "https://www.facebook.com/events/?date_filter_option=ANY_DATE&discover_tab=CUSTOM&location_id=114912541853133")
        sleep(1)
        return list(FacebookScrapper.slow_scroll_to_bottom(driver, scroll_increment=5000))
