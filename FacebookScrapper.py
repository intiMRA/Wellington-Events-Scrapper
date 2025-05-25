from dotenv import load_dotenv
from time import sleep
import json
from dateutil import parser

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

from DateFormatting import DateFormatting
from EventInfo import EventInfo
import re
from datetime import datetime, timedelta
from pathlib import Path
from dateutil.relativedelta import relativedelta

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
            return None

    @staticmethod
    def parseDate(date: str) -> [datetime]:
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
                    firstPart, secondPart = parts[0], parts[1]
                    firstPart = firstPart.strip() + hour
                    startDate = parser.parse(firstPart)
                    return [startDate]
                else:
                    parts = date.split(",")[1]
                    firstPart = re.findall(r"\d{1,2}\s\w{3}", parts)[0]
                    firstPart = firstPart.strip() + hour
                    startDate = parser.parse(firstPart)
                    return [startDate]
            elif "-" in date and len(date.split("-")[-1]) > 3:
                parts = date.split(",")[1].split("-")
                firstPart, secondPart = parts[0], parts[1]
                firstPart = firstPart.strip() + hour
                secondPart = secondPart.strip() + hour
                startDate = parser.parse(firstPart)
                endDate = parser.parse(secondPart)
                dates = list(DateFormatting.createRange(startDate, endDate))
                return dates
            elif "," in date:
                dateString = " ".join(date.split(",")[-1].strip().split(" ")[:2]) + hour
                date = parser.parse(dateString)
                return [date]
            else:
                print(f"facebook: {date}")
                return None
        except Exception as e:
            print("facebook date: ", date, " error: ", e)
            return None

    @staticmethod
    def slow_scroll_to_bottom(driver, category: str, foundTitles: set, scroll_increment=300) -> ([EventInfo], set):
        oldEventTitles = {}
        newEventTitles = {}
        titles = set()
        while True:
            driver.execute_script(f"window.scrollBy(0, {scroll_increment});")
            driver.implicitly_wait(2)
            html = driver.find_elements(By.TAG_NAME, 'a')
            print("size of html: ", len(html))
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
                    if title in newEventTitles.keys() or title in foundTitles:
                        continue
                    titles.add(title)
                    dates = FacebookScrapper.parseDate(date)
                    venue = filtered[2]
                    eventUrl = event.get_attribute('href')
                    regex = r'https://www.facebook.com/events/\d+'
                    eventUrl = re.findall(regex, eventUrl)[0]
                    imageUrl = event.find_element(By.TAG_NAME, 'img').get_attribute('src')

                    newEventTitles[title] = EventInfo(name=title,
                                                      dates=dates,
                                                      image=imageUrl,
                                                      url=eventUrl,
                                                      venue=venue,
                                                      source="facebook",
                                                      eventType=category)
                except Exception as e:
                    if "No dates found for" in str(e):
                        print("facebook error: ", e)
                        print("facebook error: ", filtered)
                        continue
                    else:
                        raise e
            if oldEventTitles.keys() == newEventTitles.keys() or len(oldEventTitles.keys()) >= 250:
                return newEventTitles.values(), titles.union(foundTitles)
            oldEventTitles = newEventTitles.copy()
        return list(events.values()), titles.union(foundTitles)

    @staticmethod
    def fetch_events() -> [EventInfo]:
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
        nextMonthButton = driver.find_element(By.XPATH, "//span[contains(., 'In the next month')]")
        nextMonthButton.click()
        sleep(2)
        locationSearch = driver.find_element(By.XPATH, "//input[@placeholder='Location']")
        locationSearch.click()
        locationSearch.send_keys("Wellin")
        sleep(2)
        welly = driver.find_element(By.XPATH, "//span[contains(., 'Wellington, New Zealand')]")
        welly.click()
        events = []
        catButton = driver.find_element(By.XPATH, f"//span[contains(., 'Classics')]")
        catButton.click()
        dates.click()
        sleep(1)
        titles = set()
        for cat in sorted(cats):
            print("cat: ", cat)
            catButton = driver.find_element(By.XPATH, f"//span[contains(., '{cat}')]")
            driver.execute_script("arguments[0].scrollIntoView(true);", catButton)
            catButton.click()
            sleep(1)
            t = FacebookScrapper.slow_scroll_to_bottom(driver, cat, titles, scroll_increment=5000)
            events += list(t[0])
            titles = t[1]
            catButton.click()
        driver.get(
            f"https://www.facebook.com/events/?"
            f"date_filter_option=CUSTOM_DATE_RANGE"
            f"&discover_tab=CUSTOM"
            f"&location_id=114912541853133"
            f"&start_date={start_date_string}"
            f"&end_date={end_date_string}")
        sleep(1)
        events += list(FacebookScrapper.slow_scroll_to_bottom(driver, "Other", titles, scroll_increment=5000)[0])
        driver.close()
        return events
# events = list(map(lambda x: x.to_dict(), sorted(FacebookScrapper.fetch_events(), key=lambda k: k.name.strip())))
# with open('wellys.json', 'w') as outfile:
#     json.dump(events, outfile)