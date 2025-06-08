# https://www.cecwellington.ac.nz/w/courses/

from time import sleep
from selenium import webdriver
from selenium.webdriver.common.by import By
from EventInfo import EventInfo
import re
from datetime import datetime
from DateFormatting import DateFormatting
from dateutil import parser
from typing import List, Tuple, Set
import json

class WellingtonHighschoolScrapper:
    @staticmethod
    def slow_scroll_to_bottom(driver: webdriver):
        prevHeight = 0
        while True:
            height = driver.execute_script("return document.body.scrollHeight")
            driver.execute_script(f"window.scrollBy(0, {height});")
            sleep(1)
            if prevHeight == height:
                break
            prevHeight = height

    @staticmethod
    def getAllEventDates(url: str) -> List[datetime]:
        driver = webdriver.Chrome()
        driver.get(url)
        sleep(1)
        events = driver.find_elements(By.CLASS_NAME, "event")
        dates = []
        for event in events:
            texts = event.text.split("\n")
            try:
                dateTag = " ".join(texts[0].split(" ")[1:])
                if re.findall(r"\d{1,2}\s*[:0-9 ]*\s*[AMP]{2}", texts[1]):
                    hours = re.findall(r"\d{1,2}\s*[:0-9 ]*\s*[AMP]{2}", texts[1])[0]
                elif re.findall(r"\d{1,2}\s*[:0-9 ]*\s*[AMP]{2}", texts[2]):
                    hours = re.findall(r"\d{1,2}\s*[:0-9 ]*\s*[AMP]{2}", texts[2])[0]
                else:
                    print("no hours: ")
                    print(texts)
                    print("-"*30)
                    hours = "10 AM"
                dateString = dateTag + " " + hours
                date_obj = parser.parse(dateString)
                date_obj = DateFormatting.replaceYear(date_obj)
                dates.append(date_obj)
            except Exception as e:
                print(url)
                print(texts)
                raise e
        driver.close()
        return dates

    @staticmethod
    def getEvents(url: str, titles: set, category: str, driver: webdriver) -> List[EventInfo]:
        events: List[EventInfo] = []
        driver.get(url)
        WellingtonHighschoolScrapper.slow_scroll_to_bottom(driver)
        catalog = driver.find_element(By.CLASS_NAME, "catalogue")
        elements = catalog.find_elements(By.CLASS_NAME, "catalogue-item")
        for element in elements:
            try:
                title = element.find_element(By.CLASS_NAME, "name").text
                if title in titles:
                    continue
                titles.add(title)
                eventLink = element.find_element(By.TAG_NAME, "a").get_attribute("href")
                dates = []
                for i in range(10):
                    try:
                        dates = WellingtonHighschoolScrapper.getAllEventDates(eventLink)
                        break
                    except:
                        pass
                imageLink = element.find_element(By.TAG_NAME, "img").get_attribute("src")
                events.append(EventInfo(name=title,
                                        image=imageLink,
                                        venue="Wellington High School Community Education Centre",
                                        dates=dates,
                                        url=eventLink,
                                        source="Wellington High School",
                                        eventType=category))
            except Exception as e:
                if "No dates found for" in str(e):
                    print("Wellington High School error: ", e)
                    continue
                else:
                    raise e
        return events

    @staticmethod
    def getCategories() -> List[Tuple[str, str]]:
        driver = webdriver.Chrome()
        driver.get("https://www.cecwellington.ac.nz/w/courses/")
        filters = driver.find_elements(By.CLASS_NAME, "radio-filter")
        categories = []
        for filter in filters:
            aTag = filter.find_element(By.TAG_NAME, "a")
            category = (filter.text, aTag.get_attribute("href"))
            categories.append(category)
        driver.close()
        return categories

    @staticmethod
    def fetch_events(previousTitles: Set[str]) -> List[EventInfo]:
        titles = previousTitles
        categories = WellingtonHighschoolScrapper.getCategories()
        driver = webdriver.Chrome()
        events = []
        for category in categories:
            categoryName, url = category
            events += WellingtonHighschoolScrapper.getEvents(url, titles, categoryName, driver)
        driver.close()
        return events

# with open("events.json", mode="r") as f:
#     evts = json.loads(f.read())
#     previousEventTitles = evts["events"]
# wellingtonHighschoolPrevious = [EventInfo.from_dict(event) for event in previousEventTitles if event["source"] == "Wellington High School"]
# wellingtonHighschoolPrevious = [event for event in wellingtonHighschoolPrevious if event is not None]
# wellingtonHighschool_events = WellingtonHighschoolScrapper.fetch_events(set([event.name for event in wellingtonHighschoolPrevious]))

# events = list(map(lambda x: x.to_dict(), sorted(WellingtonHighschoolScrapper.fetch_events(set()), key=lambda k: k.name.strip())))
# with open('wellys.json', 'w') as outfile:
#     json.dump(events, outfile)
