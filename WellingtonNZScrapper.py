from datetime import datetime
from selenium.webdriver.common.by import By

from DateFormatting import DateFormatting
from EventInfo import EventInfo
from selenium import webdriver
import re
from dateutil import parser
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from typing import List, Set
import json

class WellingtonNZScrapper:
    @staticmethod
    def slow_scroll_to_bottom(driver, category: str, eventNames: Set[str]) -> List[EventInfo]:
        events = {}
        height = driver.execute_script("return document.body.scrollHeight")
        scrolledAmount = 0
        while True:
            if scrolledAmount > height:
                return list(events.values())
            driver.execute_script(f"window.scrollBy(0, {400});")
            scrolledAmount += 400
            rawEvents = driver.find_elements(By.CLASS_NAME, 'grid-item')
            for event in rawEvents:
                title = event.find_element(By.TAG_NAME, 'h2').text
                dateObjects = []
                if not title:
                    continue
                if title in eventNames:
                    continue
                eventNames.add(title)
                try:
                    venue = event.find_element(By.CLASS_NAME, 'event-content__info').get_attribute('textContent')
                except:
                    venue = "not listed"
                dateString = event.find_element(By.CLASS_NAME, 'event-content__date').text
                if not dateString:
                    continue
                if re.match(r"\d+ – \d+", dateString):
                    first, rest = dateString.split(" – ")
                    if len(rest) > 2:
                        rest = rest.split(" ")
                        last = rest[0]
                        months = " ".join(rest[1:])
                        date1 = parser.parse(first + " " + months + " 10:00am")
                        date2 = parser.parse(last + " " + months + " 10:00am")
                        dateObjects = list(DateFormatting.createRange(date1, date2))
                    else:
                        splitDateString = dateString.split(" – ")
                        date = datetime.strptime(splitDateString[-1], '%d %B %Y')
                        dateObjects = [date]
                elif re.match(r"(\d{1,2} [A-Za-z]+ \d{4})\s+–\s+(\d{1,2} [A-Za-z]+ \d{4})", dateString):

                    match = re.match(r"(\d{1,2} [A-Za-z]+ \d{4})\s+–\s+(\d{1,2} [A-Za-z]+ \d{4})", dateString)
                    startDateString = match.group(1)
                    endDateString = match.group(2)

                    startDate = parser.parse(startDateString + " 10:00am")
                    endDate = parser.parse(endDateString + " 10:00am")

                    dateObjects = list(DateFormatting.createRange(startDate, endDate))

                elif re.findall(r"(\d{1,2} [A-Za-z]+)\s+–\s+(\d{1,2} [A-Za-z]+ \d{4})", dateString):
                    parts = dateString.split(" – ")
                    startDateString = re.findall(r"(\d{1,2} [A-Za-z]+)", parts[0])[0]
                    endDateString = re.findall(r"(\d{1,2} [A-Za-z]+)", parts[-1])[-1]
                    startDateString = startDateString + " 10:00am"
                    endDateString = endDateString + " 10:00am"
                    startDate = parser.parse(startDateString)
                    endDate = parser.parse(endDateString)

                    dateObjects = list(DateFormatting.createRange(startDate, endDate))
                elif dateString:
                    date = parser.parse(dateString + " 10:00am")
                    dateObjects = [date]
                else:
                    print(f"WellingtonNz failed to load: {event.text}")
                if not dateObjects:
                    print(dateString)
                    print(f"WellingtonNz failed to load: {event.text}")
                imageUrl = event.find_element(By.TAG_NAME, 'img').get_attribute('src')
                eventUrl = event.find_element(By.TAG_NAME, 'a').get_attribute('href')
                try:
                    eventInfo = EventInfo(name=title,
                                          image=imageUrl,
                                          venue=venue,
                                          dates=dateObjects,
                                          url=eventUrl,
                                          source="Wellington NZ",
                                          eventType=category)
                    events[title] = eventInfo
                except Exception as e:
                    print(f"WellingtonNz: {e}")
                    pass

    @staticmethod
    def fetch_events(previousTitles: Set[str]) -> List[EventInfo]:
        driver = webdriver.Chrome()
        driver.get('https://www.wellingtonnz.com/visit/events?mode=list')
        driver.switch_to.window(driver.current_window_handle)
        wait = WebDriverWait(driver, timeout=10, poll_frequency=1)
        _ = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "pagination__position")))
        categories = driver.find_elements(By.CLASS_NAME, 'search-button-filter')

        categories = [(cat.text.replace("&", "+%26+").replace(" ", "").split("\n")[0], cat.text.split("\n")[1]) for cat in categories]
        numberOfEvents = driver.find_element(By.CLASS_NAME, "pagination__position")
        numberOfEvents = re.findall("\d+", numberOfEvents.text)
        eventsInfo = []
        eventNames = previousTitles
        for cat in categories:
            cat = cat[0]
            page = 1
            while numberOfEvents[0] != numberOfEvents[1]:
                driver.get(f'https://www.wellingtonnz.com/visit/events?mode=list&page={page}&categories={cat}')
                _ = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "pagination__position")))
                numberOfEvents = driver.find_element(By.CLASS_NAME, "pagination__position")
                numberOfEvents = re.findall("\d+", numberOfEvents.text)
                page += 1
            numberOfEvents = [0, 1]
            eventsInfo += list(WellingtonNZScrapper.slow_scroll_to_bottom(driver, cat, eventNames))
        driver.close()
        return eventsInfo
# events = list(map(lambda x: x.to_dict(), sorted(WellingtonNZScrapper.fetch_events(), key=lambda k: k.name.strip())))
# with open('wellys.json', 'w') as outfile:
#     json.dump(events, outfile)